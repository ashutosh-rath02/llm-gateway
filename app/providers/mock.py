from typing import Any

from app.providers.base import LLMProvider, ProviderRequest, ProviderResponse


class MockProvider(LLMProvider):
    def __init__(self, default_model: str) -> None:
        self.default_model = default_model

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        output = self._build_output(request)
        input_tokens = max(1, len(request.input_text.split()))
        output_tokens = max(1, len(str(output).split()))

        return ProviderResponse(
            provider="mock",
            model=request.requested_model or self.default_model,
            output=output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _build_output(self, request: ProviderRequest) -> Any:
        if not request.schema:
            return (
                f"Mock response for feature '{request.feature}' and task "
                f"'{request.task_type}'."
            )

        properties = request.schema.get("properties", {})
        required_fields = request.schema.get("required", [])
        output: dict[str, Any] = {}

        for field_name in required_fields:
            field_schema = properties.get(field_name, {})
            output[field_name] = self._value_for_schema(field_name, field_schema)

        for field_name, field_schema in properties.items():
            output.setdefault(field_name, self._value_for_schema(field_name, field_schema))

        return output

    def _value_for_schema(self, field_name: str, field_schema: dict[str, Any]) -> Any:
        schema_type = field_schema.get("type", "string")

        if schema_type == "string":
            if "enum" in field_schema and field_schema["enum"]:
                return field_schema["enum"][0]
            return f"mock_{field_name}"
        if schema_type == "number":
            return 0.0
        if schema_type == "integer":
            return 0
        if schema_type == "boolean":
            return True
        if schema_type == "array":
            return []
        if schema_type == "object":
            return {}
        return None
