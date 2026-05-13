import json

import httpx

from app.providers.base import LLMProvider, ProviderError, ProviderRequest, ProviderResponse
from app.providers.schema_normalizer import normalize_openai_schema


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout_ms: int,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_seconds = timeout_ms / 1000

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not configured for the openai_compatible provider.",
                error_type="provider_auth_missing",
            )

        payload = {
            "model": request.requested_model or self.default_model,
            "input": self._build_input(request),
        }
        if request.schema:
            normalized_schema = normalize_openai_schema(request.schema)
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": f"{request.feature}_response".replace("-", "_")[:64],
                    "schema": normalized_schema,
                    "strict": True,
                }
            }

        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "The provider request timed out.",
                error_type="provider_timeout",
                status_code=504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            error_payload = self._safe_json(exc.response)
            error_message = (
                error_payload.get("error", {}).get("message")
                or exc.response.text
                or "The provider returned an error."
            )
            status_code = 429 if exc.response.status_code == 429 else 502
            error_type = (
                "provider_rate_limit"
                if exc.response.status_code == 429
                else "provider_error"
            )
            raise ProviderError(
                error_message,
                error_type=error_type,
                status_code=status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "The provider request failed before a response was returned.",
                error_type="provider_transport_error",
            ) from exc

        data = response.json()
        output_text, refusal = self._extract_output(data)
        parsed_output = self._parse_output(output_text, request.schema)
        usage = data.get("usage", {})

        return ProviderResponse(
            provider="openai_compatible",
            model=data.get("model", payload["model"]),
            output=parsed_output,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cached_input_tokens=usage.get("input_tokens_details", {}).get("cached_tokens", 0),
            refusal=refusal,
        )

    def _build_input(self, request: ProviderRequest) -> str:
        sections = [f"Task type: {request.task_type}"]

        if request.context:
            rendered_context = "\n\n".join(
                f"[{item.get('type', 'context')}]\n{item.get('content', '')}"
                for item in request.context
            )
            sections.append(f"Context:\n{rendered_context}")

        sections.append(f"User input:\n{request.input_text}")
        return "\n\n".join(sections)

    def _extract_output(self, payload: dict) -> tuple[str, str | None]:
        text_parts: list[str] = []
        refusal: str | None = None

        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue

            for content in item.get("content", []):
                content_type = content.get("type")
                if content_type == "output_text":
                    text_parts.append(content.get("text", ""))
                if content_type == "refusal":
                    refusal = content.get("refusal")

        if not text_parts and isinstance(payload.get("output_text"), str):
            text_parts.append(payload["output_text"])

        return "".join(text_parts).strip(), refusal

    def _parse_output(self, output_text: str, schema: dict | None) -> object:
        if not schema:
            return output_text

        if not output_text:
            return None

        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            return output_text

    def _safe_json(self, response: httpx.Response) -> dict:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}
