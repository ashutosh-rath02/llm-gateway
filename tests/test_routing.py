from fastapi.testclient import TestClient


def test_cost_optimized_routes_to_cheapest_eligible_model(client: TestClient, monkeypatch) -> None:
    captured_models: list[str] = []

    def fake_generate(self, request):
        from app.providers.base import ProviderResponse

        captured_models.append(request.requested_model)
        return ProviderResponse(
            provider="openai_compatible",
            model=request.requested_model or "unknown",
            output="Cheap route response",
            input_tokens=10,
            output_tokens=5,
            cached_input_tokens=0,
        )

    monkeypatch.setattr(
        "app.providers.openai_compatible.OpenAICompatibleProvider.generate",
        fake_generate,
    )

    response = client.post(
        "/v1/llm/execute",
        json={
            "provider": "openai_compatible",
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "routing_policy": "cost_optimized",
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "gpt-5-nano"
    assert captured_models == ["gpt-5-nano"]


def test_quality_optimized_routes_to_strongest_model(client: TestClient, monkeypatch) -> None:
    def fake_generate(self, request):
        from app.providers.base import ProviderResponse

        return ProviderResponse(
            provider="openai_compatible",
            model=request.requested_model or "unknown",
            output="High quality response",
            input_tokens=10,
            output_tokens=5,
            cached_input_tokens=0,
        )

    monkeypatch.setattr(
        "app.providers.openai_compatible.OpenAICompatibleProvider.generate",
        fake_generate,
    )

    response = client.post(
        "/v1/llm/execute",
        json={
            "provider": "openai_compatible",
            "feature": "policy_answer",
            "task_type": "analysis",
            "input": "Provide a risk-sensitive answer.",
            "routing_policy": "quality_optimized",
            "risk_level": "high",
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "gpt-5.5"


def test_validation_failure_falls_back_to_stronger_model(client: TestClient, monkeypatch) -> None:
    def fake_generate(self, request):
        from app.providers.base import ProviderResponse

        if request.requested_model == "gpt-5-nano":
            output = {"intent": "wifi_reset"}
        else:
            output = {
                "intent": "wifi_reset",
                "urgency": "high",
                "required_action": "Escalate to technical support.",
            }

        return ProviderResponse(
            provider="openai_compatible",
            model=request.requested_model or "unknown",
            output=output,
            input_tokens=12,
            output_tokens=8,
            cached_input_tokens=0,
        )

    monkeypatch.setattr(
        "app.providers.openai_compatible.OpenAICompatibleProvider.generate",
        fake_generate,
    )

    response = client.post(
        "/v1/llm/execute",
        json={
            "provider": "openai_compatible",
            "feature": "support_triage",
            "task_type": "structured_extraction",
            "input": "Router disconnects every ten minutes.",
            "routing_policy": "cost_optimized",
            "schema": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "urgency": {"type": "string"},
                    "required_action": {"type": "string"},
                },
                "required": ["intent", "urgency", "required_action"],
            },
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["fallback"]["used"] is True
    assert body["fallback"]["level"] == 1
    assert body["model"] == "gpt-5-mini"


def test_provider_error_falls_back_to_stronger_model(client: TestClient, monkeypatch) -> None:
    def fake_generate(self, request):
        from app.providers.base import ProviderError, ProviderResponse

        if request.requested_model == "gpt-5-nano":
            raise ProviderError(
                "Temporary upstream issue.",
                error_type="provider_error",
                status_code=502,
            )

        return ProviderResponse(
            provider="openai_compatible",
            model=request.requested_model or "unknown",
            output="Fallback success",
            input_tokens=15,
            output_tokens=7,
            cached_input_tokens=0,
        )

    monkeypatch.setattr(
        "app.providers.openai_compatible.OpenAICompatibleProvider.generate",
        fake_generate,
    )

    response = client.post(
        "/v1/llm/execute",
        json={
            "provider": "openai_compatible",
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "routing_policy": "cost_optimized",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["fallback"]["used"] is True
    assert body["model"] == "gpt-5-mini"
