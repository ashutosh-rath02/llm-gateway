from fastapi.testclient import TestClient


def test_dashboard_route_returns_html(client: TestClient) -> None:
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "LLM Gateway Dashboard" in response.text
    assert "/v1/metrics/cost" in response.text
