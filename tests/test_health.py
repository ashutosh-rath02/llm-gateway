from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck() -> None:
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/v1/meta")

    assert response.status_code == 200
    assert response.json()["default_provider"] == "mock"
