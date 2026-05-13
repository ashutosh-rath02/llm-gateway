from fastapi.testclient import TestClient

from app.main import app


def test_execute_returns_trace_id_header() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"].startswith("trace_")
    assert body["status"] == "success"
    assert body["trace_id"].startswith("trace_")
    assert body["model"] == "mock-fast-small"


def test_execute_returns_structured_output_for_schema_requests() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/llm/execute",
        json={
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
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["validation"]["schema_valid"] is True
    assert body["output"]["currency"] == "USD"

