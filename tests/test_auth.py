import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_engine, reset_db_caches
from app.main import create_application


@pytest.fixture
def authenticated_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> TestClient:
    database_file = tmp_path / "auth-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("DEFAULT_PROVIDER", "mock")
    monkeypatch.setenv("TRACE_PERSISTENCE_ENABLED", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv(
        "AUTH_API_KEYS",
        (
            '{"tenant-key":{"name":"tenant-app","role":"tenant","tenant_id":"tenant_123"},'
            '"admin-key":{"name":"admin-app","role":"admin"},'
            '"feature-key":{"name":"feature-app","role":"tenant",'
            '"tenant_id":"tenant_123","allowed_features":["support_triage"]}}'
        ),
    )

    get_settings.cache_clear()
    reset_db_caches()

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    app = create_application()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        Base.metadata.drop_all(bind=engine)
        reset_db_caches()
        get_settings.cache_clear()


def test_execute_requires_auth_when_enabled(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        "/v1/llm/execute",
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error_type"] == "auth_required"


def test_tenant_key_scopes_execute_and_trace_access(
    authenticated_client: TestClient,
) -> None:
    execute_response = authenticated_client.post(
        "/v1/llm/execute",
        headers={"X-API-Key": "tenant-key"},
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )

    assert execute_response.status_code == 200
    body = execute_response.json()
    trace_id = body["trace_id"]

    trace_response = authenticated_client.get(
        f"/v1/traces/{trace_id}",
        headers={"X-API-Key": "tenant-key"},
    )

    assert trace_response.status_code == 200
    assert trace_response.json()["tenant_id"] == "tenant_123"


def test_tenant_key_cannot_cross_tenant_boundary(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/v1/llm/execute",
        headers={"X-API-Key": "tenant-key"},
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
            "metadata": {"tenant_id": "tenant_999"},
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_type"] == "auth_tenant_mismatch"


def test_tenant_metrics_and_export_are_scoped(
    authenticated_client: TestClient,
) -> None:
    authenticated_client.post(
        "/v1/llm/execute",
        headers={"X-API-Key": "tenant-key"},
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )
    authenticated_client.post(
        "/v1/llm/execute",
        headers={"X-API-Key": "admin-key"},
        json={
            "feature": "invoice_extraction",
            "task_type": "faq",
            "input": "Extract the invoice total.",
            "metadata": {"tenant_id": "tenant_999"},
        },
    )

    metrics_response = authenticated_client.get(
        "/v1/metrics/cost",
        headers={"X-API-Key": "tenant-key"},
    )
    export_response = authenticated_client.post(
        "/v1/evals/export",
        headers={"X-API-Key": "tenant-key"},
        json={},
    )

    assert metrics_response.status_code == 200
    assert metrics_response.json()["request_count"] == 1
    assert {item["key"] for item in metrics_response.json()["by_tenant"]} == {"tenant_123"}

    assert export_response.status_code == 200
    assert export_response.json()["item_count"] == 1
    assert export_response.json()["items"][0]["tenant_id"] == "tenant_123"


def test_feature_allowlist_is_enforced(authenticated_client: TestClient) -> None:
    forbidden_response = authenticated_client.post(
        "/v1/llm/execute",
        headers={"Authorization": "Bearer feature-key"},
        json={
            "feature": "invoice_extraction",
            "task_type": "faq",
            "input": "Extract the invoice total.",
        },
    )
    allowed_response = authenticated_client.post(
        "/v1/llm/execute",
        headers={"Authorization": "Bearer feature-key"},
        json={
            "feature": "support_triage",
            "task_type": "faq",
            "input": "How do I reset my device Wi-Fi?",
        },
    )

    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"]["error_type"] == "auth_feature_forbidden"
    assert allowed_response.status_code == 200
