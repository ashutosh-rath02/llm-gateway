from fastapi.testclient import TestClient


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_endpoint(client: TestClient) -> None:
    response = client.get("/v1/meta")

    assert response.status_code == 200
    assert response.json()["default_provider"] == "mock"
