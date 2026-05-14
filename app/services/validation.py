from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from app.core.config import get_settings
from app.core.errors import GatewayError
from app.schemas.llm import GatewayExecuteRequest


@dataclass(slots=True)
class ValidationErrorItem:
    path: str
    message: str


def validate_structured_output(
    output: Any,
    schema: dict[str, Any],
) -> list[ValidationErrorItem]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(output), key=lambda err: list(err.path))
    return [
        ValidationErrorItem(
            path=_format_error_path(error),
            message=error.message,
        )
        for error in errors
    ]


def enforce_execute_guardrails(payload: GatewayExecuteRequest) -> None:
    settings = get_settings()

    if payload.latency_budget_ms > settings.max_request_latency_budget_ms:
        raise GatewayError(
            (
                f"Requested latency_budget_ms={payload.latency_budget_ms} exceeds the "
                f"configured maximum of {settings.max_request_latency_budget_ms}."
            ),
            error_type="request_latency_budget_too_high",
            status_code=400,
        )

    if payload.cost_budget_usd > settings.max_request_cost_budget_usd:
        raise GatewayError(
            (
                f"Requested cost_budget_usd={payload.cost_budget_usd} exceeds the "
                f"configured maximum of {settings.max_request_cost_budget_usd}."
            ),
            error_type="request_cost_budget_too_high",
            status_code=400,
        )


def _format_error_path(error) -> str:
    if not error.path:
        return "$"

    return "$." + ".".join(str(part) for part in error.path)
