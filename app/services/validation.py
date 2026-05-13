from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator


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


def _format_error_path(error) -> str:
    if not error.path:
        return "$"

    return "$." + ".".join(str(part) for part in error.path)

