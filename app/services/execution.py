from app.providers.base import ProviderRequest
from app.providers.factory import ProviderFactory
from app.schemas.llm import (
    FallbackSummary,
    GatewayExecuteRequest,
    GatewayExecuteResponse,
    UsageSummary,
    ValidationSummary,
)
from app.services.validation import ValidationErrorItem, validate_structured_output


class ExecutionService:
    def __init__(self) -> None:
        self.provider_factory = ProviderFactory()

    def execute(
        self,
        payload: GatewayExecuteRequest,
        trace_id: str | None,
    ) -> GatewayExecuteResponse:
        provider = self.provider_factory.get_provider()
        provider_request = ProviderRequest(
            feature=payload.feature,
            task_type=payload.task_type,
            input_text=payload.input,
            context=[item.model_dump() for item in payload.context],
            schema=payload.schema_,
            requested_model=payload.requested_model,
        )

        provider_response = provider.generate(provider_request)
        validation_summary = self._validate_output(payload, provider_response.output)
        has_validation_errors = bool(validation_summary and validation_summary.errors)
        status = "success" if not has_validation_errors else "validation_failed"

        input_cost = provider_response.input_tokens * 0.00015 / 1000
        output_cost = provider_response.output_tokens * 0.0006 / 1000

        return GatewayExecuteResponse(
            status=status,
            trace_id=trace_id or "trace_missing",
            model=provider_response.model,
            output=provider_response.output,
            validation=validation_summary,
            usage=UsageSummary(
                input_tokens=provider_response.input_tokens,
                output_tokens=provider_response.output_tokens,
                cached_input_tokens=provider_response.cached_input_tokens,
                cost_usd=round(input_cost + output_cost, 6),
            ),
            fallback=FallbackSummary(used=False, level=0),
        )

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
