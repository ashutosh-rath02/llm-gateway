import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine, reset_db_caches
from app.main import create_application
from app.services.rate_limits import reset_execute_rate_limiter


def test_get_trace_returns_persisted_trace_details(client: TestClient) -> None:
    execute_response = client.post(
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

    trace_id = execute_response.json()["trace_id"]
    response = client.get(f"/v1/traces/{trace_id}")
    body = response.json()

    assert response.status_code == 200
    assert body["trace_id"] == trace_id
    assert body["feature"] == "support_triage"
    assert body["provider"] == "mock"
    assert body["prompt_template_name"] == "support_triage_v1"
    assert body["prompt_template_version"] == "2026-05-13"
    assert body["tenant_id"] == "tenant_123"
    assert body["user_id_hash"] is not None
    assert len(body["model_calls"]) == 1
    assert body["model_calls"][0]["provider"] == "mock"
    assert body["model_calls"][0]["attempt_kind"] == "primary"


def test_get_trace_returns_404_for_missing_trace(client: TestClient) -> None:
    response = client.get("/v1/traces/trace_missing")

    assert response.status_code == 404
    assert response.json()["detail"]["message"] == "Trace not found."


@pytest.fixture
def storage_policy_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> TestClient:
    database_file = tmp_path / "storage-policy-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("DEFAULT_PROVIDER", "mock")
    monkeypatch.setenv("TRACE_PERSISTENCE_ENABLED", "true")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("AUTH_API_KEYS", "{}")
    monkeypatch.setenv("EXECUTE_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("STORE_PROMPTS", "true")
    monkeypatch.setenv("STORE_OUTPUTS", "true")
    monkeypatch.setenv("PROMPT_STORAGE_FEATURE_DENYLIST", '["sensitive_feature"]')
    monkeypatch.setenv("OUTPUT_STORAGE_FEATURE_DENYLIST", '["sensitive_feature"]')

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


def test_trace_redacts_sensitive_metadata_keys(client: TestClient) -> None:
    execute_response = client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "metadata": {
                "tenant_id": "tenant_123",
                "token": "secret-token-value",
                "nested": {"authorization": "Bearer abc"},
                "user_id": "user_456",
            },
        },
    )

    trace_id = execute_response.json()["trace_id"]
    response = client.get(f"/v1/traces/{trace_id}")
    body = response.json()

    assert response.status_code == 200
    assert body["request_metadata"]["token"] == "[redacted]"
    assert body["request_metadata"]["nested"]["authorization"] == "[redacted]"
    assert "user_id" not in body["request_metadata"]


def test_trace_storage_feature_denylist_skips_prompt_and_output_previews(
    storage_policy_client: TestClient,
) -> None:
    execute_response = storage_policy_client.post(
        "/v1/llm/execute",
        json={
            "feature": "sensitive_feature",
            "task_type": "faq",
            "input": "This should not be persisted as a preview.",
        },
    )

    trace_id = execute_response.json()["trace_id"]
    response = storage_policy_client.get(f"/v1/traces/{trace_id}")
    body = response.json()

    assert response.status_code == 200
    assert body["input_preview"] is None
    assert body["output_preview"] is None
