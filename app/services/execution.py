import json
from dataclasses import dataclass
from time import perf_counter

from app.core.config import get_settings
from app.core.errors import GatewayError
from app.core.pricing import calculate_cost_usd
from app.providers.base import ProviderError, ProviderRequest, ProviderResponse
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


@dataclass(slots=True)
class AttemptExecutionResult:
    persisted_call: PersistedModelCall
    provider_response: ProviderResponse | None = None
    validation_summary: ValidationSummary | None = None
    error: ProviderError | None = None


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
        repair_attempts = 0

        total_input_tokens = 0
        total_output_tokens = 0
        total_cached_input_tokens = 0
        total_cost_usd = 0.0
        total_latency_ms = 0
        attempt_number = 0
        final_fallback_level = 0
        settings = get_settings()

        for model_index, model_name in enumerate(attempt_models):
            if model_index > 0 and not self.routing_service.can_attempt_model(
                model_name,
                payload,
                estimated_input_tokens=decision.estimated_input_tokens,
                estimated_output_tokens=decision.estimated_output_tokens,
                cost_spent_usd=round(total_cost_usd, 6),
                elapsed_latency_ms=total_latency_ms,
            ):
                break

            primary_kind = "primary" if model_index == 0 else "fallback"
            primary_result = self._execute_attempt(
                payload=payload,
                provider_name=decision.provider_name,
                model_name=model_name,
                request=self._build_provider_request(payload, model_name),
                attempt=attempt_number + 1,
                attempt_kind=primary_kind,
            )
            attempt_number += 1
            persisted_calls.append(primary_result.persisted_call)
            total_latency_ms += primary_result.persisted_call.latency_ms

            if primary_result.error is not None:
                last_provider_error = primary_result.error
                final_fallback_level = model_index
                continue

            total_input_tokens += primary_result.persisted_call.input_tokens
            total_output_tokens += primary_result.persisted_call.output_tokens
            total_cached_input_tokens += primary_result.persisted_call.cached_input_tokens
            total_cost_usd += primary_result.persisted_call.cost_usd

            last_validation_summary = primary_result.validation_summary
            last_output = (
                primary_result.provider_response.output
                if primary_result.provider_response
                else None
            )
            successful_provider_name = (
                primary_result.provider_response.provider
                if primary_result.provider_response
                else successful_provider_name
            )

            if self._is_success(primary_result.validation_summary):
                response = self._build_success_response(
                    trace_id=resolved_trace_id,
                    provider_response=primary_result.provider_response,
                    validation_summary=primary_result.validation_summary,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cached_input_tokens=total_cached_input_tokens,
                    cost_usd=total_cost_usd,
                    fallback_level=model_index,
                )
                self.trace_repository.record_success(
                    trace_id=resolved_trace_id,
                    payload=payload,
                    provider_name=primary_result.provider_response.provider,
                    response=response,
                    latency_ms=total_latency_ms,
                    model_calls=persisted_calls,
                    gateway_metadata=self.routing_service.build_gateway_metadata(
                        payload,
                        decision,
                        attempts=attempt_number,
                        fallback_level=model_index,
                        final_status="success",
                        repair_attempts=repair_attempts,
                        repair_prompt_version=settings.repair_prompt_version,
                    ),
                )
                return response

            repairs_for_model = 0
            while self._should_attempt_repair(
                payload,
                settings=settings,
                validation_summary=last_validation_summary,
                model_name=model_name,
                decision=decision,
                total_cost_usd=total_cost_usd,
                total_latency_ms=total_latency_ms,
                repairs_for_model=repairs_for_model,
            ):
                repair_result = self._execute_attempt(
                    payload=payload,
                    provider_name=decision.provider_name,
                    model_name=model_name,
                    request=self._build_repair_request(
                        payload,
                        model_name=model_name,
                        invalid_output=last_output,
                        validation_summary=last_validation_summary,
                    ),
                    attempt=attempt_number + 1,
                    attempt_kind="repair",
                )
                attempt_number += 1
                repair_attempts += 1
                repairs_for_model += 1
                persisted_calls.append(repair_result.persisted_call)
                total_latency_ms += repair_result.persisted_call.latency_ms

                if repair_result.error is not None:
                    last_provider_error = repair_result.error
                    break

                total_input_tokens += repair_result.persisted_call.input_tokens
                total_output_tokens += repair_result.persisted_call.output_tokens
                total_cached_input_tokens += repair_result.persisted_call.cached_input_tokens
                total_cost_usd += repair_result.persisted_call.cost_usd

                last_validation_summary = repair_result.validation_summary
                last_output = (
                    repair_result.provider_response.output
                    if repair_result.provider_response
                    else last_output
                )
                successful_provider_name = (
                    repair_result.provider_response.provider
                    if repair_result.provider_response
                    else successful_provider_name
                )

                if self._is_success(repair_result.validation_summary):
                    response = self._build_success_response(
                        trace_id=resolved_trace_id,
                        provider_response=repair_result.provider_response,
                        validation_summary=repair_result.validation_summary,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        cached_input_tokens=total_cached_input_tokens,
                        cost_usd=total_cost_usd,
                        fallback_level=model_index,
                    )
                    self.trace_repository.record_success(
                        trace_id=resolved_trace_id,
                        payload=payload,
                        provider_name=repair_result.provider_response.provider,
                        response=response,
                        latency_ms=total_latency_ms,
                        model_calls=persisted_calls,
                        gateway_metadata=self.routing_service.build_gateway_metadata(
                            payload,
                            decision,
                            attempts=attempt_number,
                            fallback_level=model_index,
                            final_status="success",
                            repair_attempts=repair_attempts,
                            repair_prompt_version=settings.repair_prompt_version,
                        ),
                    )
                    return response

            final_fallback_level = model_index

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
                    used=final_fallback_level > 0,
                    level=final_fallback_level,
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
                    fallback_level=final_fallback_level,
                    final_status="validation_failed",
                    repair_attempts=repair_attempts,
                    repair_prompt_version=settings.repair_prompt_version,
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
            fallback_level=final_fallback_level,
            gateway_metadata=self.routing_service.build_gateway_metadata(
                payload,
                decision,
                attempts=max(len(persisted_calls), 1),
                fallback_level=final_fallback_level,
                final_status="provider_error",
                final_error_type=final_error.error_type,
                repair_attempts=repair_attempts,
                repair_prompt_version=settings.repair_prompt_version,
            ),
        )
        raise final_error

    def _build_success_response(
        self,
        *,
        trace_id: str,
        provider_response: ProviderResponse,
        validation_summary: ValidationSummary | None,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int,
        cost_usd: float,
        fallback_level: int,
    ) -> GatewayExecuteResponse:
        return GatewayExecuteResponse(
            status="success",
            trace_id=trace_id,
            model=provider_response.model,
            output=provider_response.output,
            validation=validation_summary,
            usage=UsageSummary(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_input_tokens=cached_input_tokens,
                cost_usd=round(cost_usd, 6),
            ),
            fallback=FallbackSummary(
                used=fallback_level > 0,
                level=fallback_level,
            ),
        )

    def _build_provider_request(
        self,
        payload: GatewayExecuteRequest,
        model_name: str,
    ) -> ProviderRequest:
        return ProviderRequest(
            feature=payload.feature,
            task_type=payload.task_type,
            input_text=payload.input,
            context=[item.model_dump() for item in payload.context],
            schema=payload.schema_,
            requested_model=model_name,
        )

    def _build_repair_request(
        self,
        payload: GatewayExecuteRequest,
        *,
        model_name: str,
        invalid_output: object | None,
        validation_summary: ValidationSummary | None,
    ) -> ProviderRequest:
        repair_prompt = self._build_repair_prompt(
            payload=payload,
            invalid_output=invalid_output,
            validation_summary=validation_summary,
        )
        return ProviderRequest(
            feature=payload.feature,
            task_type=payload.task_type,
            input_text=repair_prompt,
            context=[item.model_dump() for item in payload.context],
            schema=payload.schema_,
            requested_model=model_name,
        )

    def _build_repair_prompt(
        self,
        *,
        payload: GatewayExecuteRequest,
        invalid_output: object | None,
        validation_summary: ValidationSummary | None,
    ) -> str:
        rendered_errors = "\n".join(
            f"- {error.path}: {error.message}"
            for error in (validation_summary.errors or [])
        )
        return (
            "Repair the previous structured response so it strictly matches the required "
            "JSON schema.\n"
            "Return only valid JSON with no markdown, commentary, or extra keys.\n\n"
            f"Original user input:\n{payload.input}\n\n"
            f"Required schema:\n{self._render_for_prompt(payload.schema_)}\n\n"
            f"Previous invalid output:\n{self._render_for_prompt(invalid_output)}\n\n"
            f"Validation errors:\n{rendered_errors or '- No validation details were provided.'}"
        )

    def _execute_attempt(
        self,
        *,
        payload: GatewayExecuteRequest,
        provider_name: str,
        model_name: str,
        request: ProviderRequest,
        attempt: int,
        attempt_kind: str,
    ) -> AttemptExecutionResult:
        provider = self.provider_factory.get_provider(provider_name)
        started_at = perf_counter()
        try:
            provider_response = provider.generate(request)
        except ProviderError as exc:
            latency_ms = int((perf_counter() - started_at) * 1000)
            return AttemptExecutionResult(
                persisted_call=PersistedModelCall(
                    attempt=attempt,
                    attempt_kind=attempt_kind,
                    provider=provider_name,
                    model=model_name,
                    status="provider_error",
                    error_type=exc.error_type,
                    input_tokens=0,
                    output_tokens=0,
                    cached_input_tokens=0,
                    latency_ms=latency_ms,
                    cost_usd=0.0,
                ),
                error=exc,
            )

        latency_ms = int((perf_counter() - started_at) * 1000)
        attempt_cost_usd = calculate_cost_usd(
            provider_response.model,
            provider_response.input_tokens,
            provider_response.output_tokens,
            provider_response.cached_input_tokens,
        )
        validation_summary = self._validate_output(payload, provider_response.output)
        has_validation_errors = bool(validation_summary and validation_summary.errors)
        attempt_status = "success" if not has_validation_errors else "validation_failed"

        return AttemptExecutionResult(
            persisted_call=PersistedModelCall(
                attempt=attempt,
                attempt_kind=attempt_kind,
                provider=provider_response.provider,
                model=provider_response.model,
                status=attempt_status,
                error_type=None,
                input_tokens=provider_response.input_tokens,
                output_tokens=provider_response.output_tokens,
                cached_input_tokens=provider_response.cached_input_tokens,
                latency_ms=latency_ms,
                cost_usd=attempt_cost_usd,
            ),
            provider_response=provider_response,
            validation_summary=validation_summary,
        )

    def _should_attempt_repair(
        self,
        payload: GatewayExecuteRequest,
        *,
        settings,
        validation_summary: ValidationSummary | None,
        model_name: str,
        decision,
        total_cost_usd: float,
        total_latency_ms: int,
        repairs_for_model: int,
    ) -> bool:
        if payload.schema_ is None:
            return False
        if validation_summary is None or not validation_summary.errors:
            return False
        if not settings.repair_retry_enabled:
            return False
        if repairs_for_model >= settings.max_repair_attempts_per_model:
            return False
        return self.routing_service.can_attempt_model(
            model_name,
            payload,
            estimated_input_tokens=decision.estimated_input_tokens,
            estimated_output_tokens=decision.estimated_output_tokens,
            cost_spent_usd=round(total_cost_usd, 6),
            elapsed_latency_ms=total_latency_ms,
        )

    def _is_success(self, validation_summary: ValidationSummary | None) -> bool:
        return not validation_summary or not validation_summary.errors

    def _render_for_prompt(self, value: object | None) -> str:
        try:
            return json.dumps(value, indent=2, sort_keys=True)
        except TypeError:
            return str(value)

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
