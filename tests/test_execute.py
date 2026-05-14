import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine, get_session_factory, reset_db_caches
from app.main import create_application
from app.models.trace import ModelCallRecord, TraceRecord
from app.services.rate_limits import reset_execute_rate_limiter


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
            "prompt_template_name": "support_triage_v1",
            "prompt_template_version": "2026-05-13",
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
    assert trace_record.prompt_template_name == "support_triage_v1"
    assert trace_record.prompt_template_version == "2026-05-13"
    assert trace_record.tenant_id == "tenant_123"
    assert trace_record.user_id_hash is not None
    assert len(model_calls) == 1
    assert model_calls[0].attempt_kind == "primary"
    assert model_calls[0].status == "success"


@pytest.fixture
def rate_limited_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> TestClient:
    database_file = tmp_path / "rate-limited-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("DEFAULT_PROVIDER", "mock")
    monkeypatch.setenv("TRACE_PERSISTENCE_ENABLED", "true")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("AUTH_API_KEYS", "{}")
    monkeypatch.setenv("EXECUTE_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("EXECUTE_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("EXECUTE_RATE_LIMIT_WINDOW_SECONDS", "60")

    get_settings.cache_clear()
    reset_db_caches()
    reset_execute_rate_limiter()

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    app = create_application()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        Base.metadata.drop_all(bind=engine)
        reset_execute_rate_limiter()
        reset_db_caches()
        get_settings.cache_clear()


def test_execute_rejects_requests_over_configured_budget_caps(client: TestClient) -> None:
    response = client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "latency_budget_ms": 50001,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "request_latency_budget_too_high"


def test_execute_rate_limit_returns_429(rate_limited_client: TestClient) -> None:
    payload = {
        "feature": "support_triage",
        "task_type": "faq",
        "input": "How do I reset my device Wi-Fi?",
    }

    first = rate_limited_client.post("/v1/llm/execute", json=payload)
    second = rate_limited_client.post("/v1/llm/execute", json=payload)
    third = rate_limited_client.post("/v1/llm/execute", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"]["error_type"] == "rate_limit_exceeded"
