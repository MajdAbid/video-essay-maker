from fastapi.testclient import TestClient

from backend.app.main import app


def test_healthcheck() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
