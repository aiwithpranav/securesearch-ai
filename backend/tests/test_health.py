import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_returns_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready_endpoint_and_request_id():
    response = client.get("/api/v1/ready")

    assert response.status_code in [200, 503]

    assert "X-Request-ID" in response.headers

    test_id = str(uuid.uuid4())
    resp2 = client.get("/api/v1/health", headers={"X-Request-ID": test_id})
    assert resp2.headers["X-Request-ID"] == test_id
