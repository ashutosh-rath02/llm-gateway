from fastapi.testclient import TestClient


def test_cost_metrics_returns_rollups(client: TestClient) -> None:
    payloads = [
        {
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "metadata": {
                "tenant_id": "tenant_123",
                "user_id": "user_1",
            },
        },
        {
            "feature": "invoice_extraction",
            "task_type": "structured_extraction",
            "input": "Invoice INV-001 total is 1250 USD.",
            "schema": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "total": {"type": "number"},
                    "currency": {"type": "string", "enum": ["USD", "EUR"]},
                },
                "required": ["invoice_number", "total", "currency"],
            },
            "metadata": {
                "tenant_id": "tenant_456",
                "user_id": "user_2",
            },
        },
    ]

    for payload in payloads:
        response = client.post("/v1/llm/execute", json=payload)
        assert response.status_code == 200

    response = client.get("/v1/metrics/cost")
    body = response.json()

    assert response.status_code == 200
    assert body["request_count"] == 2
    assert body["success_count"] == 2
    assert body["failed_count"] == 0
    assert body["total_cost_usd"] > 0
    assert {item["key"] for item in body["by_feature"]} == {
        "support_triage",
        "invoice_extraction",
    }
    assert {item["key"] for item in body["by_tenant"]} == {
        "tenant_123",
        "tenant_456",
    }


def test_cost_metrics_supports_feature_filter(client: TestClient) -> None:
    client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )
    client.post(
        "/v1/llm/execute",
        json={
            "feature": "invoice_extraction",
            "task_type": "faq",
            "input": "Extract the invoice total.",
        },
    )

    response = client.get("/v1/metrics/cost?feature=support_triage")
    body = response.json()

    assert response.status_code == 200
    assert body["request_count"] == 1
    assert body["by_feature"][0]["key"] == "support_triage"
