from fastapi.testclient import TestClient


def test_get_trace_returns_persisted_trace_details(client: TestClient) -> None:
    execute_response = client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "metadata": {
                "tenant_id": "tenant_123",
                "user_id": "user_456",
            },
        },
    )

    trace_id = execute_response.json()["trace_id"]
    response = client.get(f"/v1/traces/{trace_id}")
    body = response.json()

    assert response.status_code == 200
    assert body["trace_id"] == trace_id
    assert body["feature"] == "support_triage"
    assert body["provider"] == "mock"
    assert body["tenant_id"] == "tenant_123"
    assert body["user_id_hash"] is not None
    assert len(body["model_calls"]) == 1
    assert body["model_calls"][0]["provider"] == "mock"


def test_get_trace_returns_404_for_missing_trace(client: TestClient) -> None:
    response = client.get("/v1/traces/trace_missing")

    assert response.status_code == 404
    assert response.json()["detail"]["message"] == "Trace not found."
