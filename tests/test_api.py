from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_serves_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"provider": "demo", "model": None, "chunk_count": 9}


def test_match():
    response = client.get("/api/match")
    assert response.status_code == 200
    data = response.json()
    for key in ["match_id", "competition", "home", "away", "score", "events", "momentum"]:
        assert key in data
    assert data["score"] == {"home": 2, "away": 1}


def test_moment_found():
    response = client.get("/api/moment/offside_27")
    assert response.status_code == 200
    assert response.json()["title"].startswith("Atlántica goal disallowed")


def test_moment_not_found():
    response = client.get("/api/moment/nonexistent")
    assert response.status_code == 404
