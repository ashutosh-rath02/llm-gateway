import httpx

from app.providers.base import ProviderRequest
from app.providers.openai_compatible import OpenAICompatibleProvider


def test_openai_provider_parses_text_output(monkeypatch) -> None:
    def fake_post(*args, **kwargs) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.4-mini",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Reset Wi-Fi from Settings > Network.",
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 20,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 8,
                },
            },
            request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
        )

    monkeypatch.setattr("app.providers.openai_compatible.httpx.post", fake_post)
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-5.4-mini",
        timeout_ms=15000,
    )

    result = provider.generate(
        ProviderRequest(
            feature="support_triage",
            task_type="faq",
            input_text="How do I reset my device Wi-Fi?",
            context=[],
            schema=None,
            requested_model=None,
        )
    )

    assert result.provider == "openai_compatible"
    assert result.model == "gpt-5.4-mini"
    assert result.output == "Reset Wi-Fi from Settings > Network."
    assert result.input_tokens == 20
    assert result.output_tokens == 8


def test_openai_provider_parses_structured_output(monkeypatch) -> None:
    def fake_post(*args, **kwargs) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.4-mini",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"intent":"wifi_reset","urgency":"low"}',
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 42,
                    "input_tokens_details": {"cached_tokens": 5},
                    "output_tokens": 12,
                },
            },
            request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
        )

    monkeypatch.setattr("app.providers.openai_compatible.httpx.post", fake_post)
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-5.4-mini",
        timeout_ms=15000,
    )

    result = provider.generate(
        ProviderRequest(
            feature="support_triage",
            task_type="structured_extraction",
            input_text="Router keeps disconnecting.",
            context=[],
            schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "urgency": {"type": "string"},
                },
                "required": ["intent", "urgency"],
            },
            requested_model=None,
        )
    )

    assert result.output == {"intent": "wifi_reset", "urgency": "low"}
    assert result.cached_input_tokens == 5


def test_openai_provider_normalizes_object_schema_for_strict_mode(monkeypatch) -> None:
    captured_payload: dict = {}

    def fake_post(*args, **kwargs) -> httpx.Response:
        captured_payload.update(kwargs["json"])
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.4-mini",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"intent":"wifi_reset","details":{"urgency":"low"}}',
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 42,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 12,
                },
            },
            request=httpx.Request("POST", "https://api.openai.com/v1/responses"),
        )

    monkeypatch.setattr("app.providers.openai_compatible.httpx.post", fake_post)
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        default_model="gpt-5.4-mini",
        timeout_ms=15000,
    )

    provider.generate(
        ProviderRequest(
            feature="support_triage",
            task_type="structured_extraction",
            input_text="Router keeps disconnecting.",
            context=[],
            schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "details": {
                        "type": "object",
                        "properties": {
                            "urgency": {"type": "string"},
                        },
                        "required": ["urgency"],
                    },
                },
                "required": ["intent", "details"],
            },
            requested_model=None,
        )
    )

    schema = captured_payload["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["details"]["additionalProperties"] is False
