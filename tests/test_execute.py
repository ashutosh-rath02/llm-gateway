from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.models.trace import ModelCallRecord, TraceRecord


def test_execute_returns_trace_id_header(client: TestClient) -> None:
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


def test_execute_returns_structured_output_for_schema_requests(client: TestClient) -> None:
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


def test_execute_persists_trace_and_model_call_records(client: TestClient) -> None:
    response = client.post(
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

    trace_id = response.json()["trace_id"]

    session = get_session_factory()()
    try:
        trace_record = session.get(TraceRecord, trace_id)
        model_calls = (
            session.query(ModelCallRecord)
            .filter(ModelCallRecord.trace_id == trace_id)
            .all()
        )
    finally:
        session.close()

    assert trace_record is not None
    assert trace_record.feature == "support_triage"
    assert trace_record.provider == "mock"
    assert trace_record.tenant_id == "tenant_123"
    assert trace_record.user_id_hash is not None
    assert len(model_calls) == 1
    assert model_calls[0].status == "success"
