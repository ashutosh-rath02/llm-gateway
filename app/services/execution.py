from time import perf_counter

from app.core.errors import GatewayError
from app.core.pricing import calculate_cost_usd
from app.providers.base import ProviderError, ProviderRequest
from app.providers.factory import ProviderFactory
from app.repositories.traces import PersistedModelCall, TraceRepository
from app.schemas.llm import (
    FallbackSummary,
    GatewayExecuteRequest,
    GatewayExecuteResponse,
    UsageSummary,
    ValidationErrorItem,
    ValidationSummary,
)
from app.services.routing import RoutingService
from app.services.validation import validate_structured_output


class ExecutionService:
    def __init__(self, trace_repository: TraceRepository | None = None) -> None:
        self.provider_factory = ProviderFactory()
        self.trace_repository = trace_repository or TraceRepository()
        self.routing_service = RoutingService()

    def execute(
        self,
        payload: GatewayExecuteRequest,
        trace_id: str | None,
    ) -> GatewayExecuteResponse:
        resolved_trace_id = trace_id or "trace_missing"
        default_provider = self.provider_factory.get_default_provider_name()
        decision = self.routing_service.plan(payload, default_provider)

        attempt_models = [decision.initial_model, *decision.fallback_models]
        persisted_calls: list[PersistedModelCall] = []
        successful_provider_name: str | None = None
        last_provider_error: ProviderError | None = None
        last_validation_summary: ValidationSummary | None = None
        last_output: object | None = None

        total_input_tokens = 0
        total_output_tokens = 0
        total_cached_input_tokens = 0
        total_cost_usd = 0.0
        total_latency_ms = 0

        for attempt_number, model_name in enumerate(attempt_models, start=1):
            if attempt_number > 1 and not self.routing_service.can_attempt_model(
                model_name,
                payload,
                estimated_input_tokens=decision.estimated_input_tokens,
                estimated_output_tokens=decision.estimated_output_tokens,
                cost_spent_usd=round(total_cost_usd, 6),
                elapsed_latency_ms=total_latency_ms,
            ):
                break

            provider = self.provider_factory.get_provider(decision.provider_name)
            provider_request = ProviderRequest(
                feature=payload.feature,
                task_type=payload.task_type,
                input_text=payload.input,
                context=[item.model_dump() for item in payload.context],
                schema=payload.schema_,
                requested_model=model_name,
            )

            started_at = perf_counter()
            try:
                provider_response = provider.generate(provider_request)
            except ProviderError as exc:
                latency_ms = int((perf_counter() - started_at) * 1000)
                total_latency_ms += latency_ms
                persisted_calls.append(
                    PersistedModelCall(
                        attempt=attempt_number,
                        provider=decision.provider_name,
                        model=model_name,
                        status="provider_error",
                        error_type=exc.error_type,
                        input_tokens=0,
                        output_tokens=0,
                        cached_input_tokens=0,
                        latency_ms=latency_ms,
                        cost_usd=0.0,
                    )
                )
                last_provider_error = exc
                continue

            latency_ms = int((perf_counter() - started_at) * 1000)
            attempt_cost_usd = calculate_cost_usd(
                provider_response.model,
                provider_response.input_tokens,
                provider_response.output_tokens,
                provider_response.cached_input_tokens,
            )
            total_latency_ms += latency_ms
            total_input_tokens += provider_response.input_tokens
            total_output_tokens += provider_response.output_tokens
            total_cached_input_tokens += provider_response.cached_input_tokens
            total_cost_usd += attempt_cost_usd

            validation_summary = self._validate_output(payload, provider_response.output)
            has_validation_errors = bool(validation_summary and validation_summary.errors)
            attempt_status = "success" if not has_validation_errors else "validation_failed"
            persisted_calls.append(
                PersistedModelCall(
                    attempt=attempt_number,
                    provider=provider_response.provider,
                    model=provider_response.model,
                    status=attempt_status,
                    error_type=None,
                    input_tokens=provider_response.input_tokens,
                    output_tokens=provider_response.output_tokens,
                    cached_input_tokens=provider_response.cached_input_tokens,
                    latency_ms=latency_ms,
                    cost_usd=attempt_cost_usd,
                )
            )

            last_validation_summary = validation_summary
            last_output = provider_response.output
            successful_provider_name = provider_response.provider

            if not has_validation_errors:
                response = GatewayExecuteResponse(
                    status="success",
                    trace_id=resolved_trace_id,
                    model=provider_response.model,
                    output=provider_response.output,
                    validation=validation_summary,
                    usage=UsageSummary(
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        cached_input_tokens=total_cached_input_tokens,
                        cost_usd=round(total_cost_usd, 6),
                    ),
                    fallback=FallbackSummary(
                        used=attempt_number > 1,
                        level=attempt_number - 1,
                    ),
                )
                self.trace_repository.record_success(
                    trace_id=resolved_trace_id,
                    payload=payload,
                    provider_name=provider_response.provider,
                    response=response,
                    latency_ms=total_latency_ms,
                    model_calls=persisted_calls,
                    gateway_metadata=self.routing_service.build_gateway_metadata(
                        payload,
                        decision,
                        attempts=attempt_number,
                        final_status="success",
                    ),
                )
                return response

        if last_validation_summary is not None:
            final_attempts = len(persisted_calls)
            response = GatewayExecuteResponse(
                status="validation_failed",
                trace_id=resolved_trace_id,
                model=persisted_calls[-1].model,
                output=last_output,
                validation=last_validation_summary,
                usage=UsageSummary(
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cached_input_tokens=total_cached_input_tokens,
                    cost_usd=round(total_cost_usd, 6),
                ),
                fallback=FallbackSummary(
                    used=final_attempts > 1,
                    level=max(final_attempts - 1, 0),
                ),
            )
            self.trace_repository.record_success(
                trace_id=resolved_trace_id,
                payload=payload,
                provider_name=successful_provider_name or decision.provider_name,
                response=response,
                latency_ms=total_latency_ms,
                model_calls=persisted_calls,
                gateway_metadata=self.routing_service.build_gateway_metadata(
                    payload,
                    decision,
                    attempts=final_attempts,
                    final_status="validation_failed",
                ),
            )
            return response

        final_error = last_provider_error or GatewayError(
            "No attempt could be executed within the configured budgets.",
            error_type="routing_budget_exhausted",
            status_code=400,
        )
        self.trace_repository.record_failure(
            trace_id=resolved_trace_id,
            payload=payload,
            provider_name=decision.provider_name,
            model_name=persisted_calls[-1].model if persisted_calls else decision.initial_model,
            error_type=final_error.error_type,
            latency_ms=total_latency_ms,
            model_calls=persisted_calls,
            total_cost_usd=round(total_cost_usd, 6),
            fallback_level=max(len(persisted_calls) - 1, 0),
            gateway_metadata=self.routing_service.build_gateway_metadata(
                payload,
                decision,
                attempts=max(len(persisted_calls), 1),
                final_status="provider_error",
                final_error_type=final_error.error_type,
            ),
        )
        raise final_error

    def _validate_output(
        self,
        payload: GatewayExecuteRequest,
        output: object,
    ) -> ValidationSummary | None:
        if payload.schema_ is None:
            return None

        errors = validate_structured_output(output, payload.schema_)
        return ValidationSummary(
            schema_valid=not errors,
            business_rules_valid=None,
            errors=[
                ValidationErrorItem(path=error.path, message=error.message)
                for error in errors
            ]
            or None,
        )
