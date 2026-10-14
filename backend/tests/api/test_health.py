from fastapi.testclient import TestClient

from app.main import app


def test_health_check():
    with TestClient(app) as client:                      # runs startup: migrations + queue start
        r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "railvigil-api"}
