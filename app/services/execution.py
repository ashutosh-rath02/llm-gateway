from time import perf_counter

from app.core.pricing import calculate_cost_usd
from app.providers.base import ProviderError, ProviderRequest
from app.providers.factory import ProviderFactory
from app.repositories.traces import TraceRepository
from app.schemas.llm import (
    FallbackSummary,
    GatewayExecuteRequest,
    GatewayExecuteResponse,
    UsageSummary,
    ValidationSummary,
)
from app.services.validation import ValidationErrorItem, validate_structured_output


class ExecutionService:
    def __init__(self, trace_repository: TraceRepository | None = None) -> None:
        self.provider_factory = ProviderFactory()
        self.trace_repository = trace_repository or TraceRepository()

    def execute(
        self,
        payload: GatewayExecuteRequest,
        trace_id: str | None,
    ) -> GatewayExecuteResponse:
        resolved_trace_id = trace_id or "trace_missing"
        provider = self.provider_factory.get_provider(payload.provider)
        provider_request = ProviderRequest(
            feature=payload.feature,
            task_type=payload.task_type,
            input_text=payload.input,
            context=[item.model_dump() for item in payload.context],
            schema=payload.schema_,
            requested_model=payload.requested_model,
        )

        started_at = perf_counter()
        try:
            provider_response = provider.generate(provider_request)
        except ProviderError as exc:
            latency_ms = int((perf_counter() - started_at) * 1000)
            self.trace_repository.record_failure(
                trace_id=resolved_trace_id,
                payload=payload,
                provider_name=payload.provider or "default",
                model_name=payload.requested_model,
                error_type=exc.error_type,
                latency_ms=latency_ms,
            )
            raise

        latency_ms = int((perf_counter() - started_at) * 1000)
        validation_summary = self._validate_output(payload, provider_response.output)
        has_validation_errors = bool(validation_summary and validation_summary.errors)
        status = "success" if not has_validation_errors else "validation_failed"
        cost_usd = calculate_cost_usd(
            provider_response.model,
            provider_response.input_tokens,
            provider_response.output_tokens,
            provider_response.cached_input_tokens,
        )

        response = GatewayExecuteResponse(
            status=status,
            trace_id=resolved_trace_id,
            model=provider_response.model,
            output=provider_response.output,
            validation=validation_summary,
            usage=UsageSummary(
                input_tokens=provider_response.input_tokens,
                output_tokens=provider_response.output_tokens,
                cached_input_tokens=provider_response.cached_input_tokens,
                cost_usd=cost_usd,
            ),
            fallback=FallbackSummary(used=False, level=0),
        )
        self.trace_repository.record_success(
            trace_id=resolved_trace_id,
            payload=payload,
            provider_name=provider_response.provider,
            response=response,
            latency_ms=latency_ms,
        )
        return response

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
            errors=[ValidationErrorItem(path=err.path, message=err.message) for err in errors]
            or None,
        )
