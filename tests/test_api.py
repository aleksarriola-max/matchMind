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


def test_ask_routed_question_returns_full_schema():
    response = client.post(
        "/api/ask",
        json={"question": "Why was the goal disallowed for offside in the 27th minute?", "persona": "analyst", "language": "English"},
    )
    assert response.status_code == 200
    data = response.json()
    for key in ["answer", "persona", "language", "moment_id", "verification", "explainability", "llm"]:
        assert key in data
    assert data["moment_id"] == "offside_27"
    assert data["persona"] == "analyst"
    assert data["language"] == "English"
    assert data["llm"] == {"provider": "demo", "model": None}
    for key in ["verified", "coverage", "checked_sentences", "unsupported", "method"]:
        assert key in data["verification"]


def test_ask_general_question_has_null_moment_id():
    response = client.post(
        "/api/ask",
        json={"question": "What's the weather forecast for the stadium tonight?", "persona": "beginner", "language": "English"},
    )
    assert response.status_code == 200
    assert response.json()["moment_id"] is None


def test_ask_defaults_persona_and_language():
    response = client.post("/api/ask", json={"question": "Why was the goal disallowed for offside in the 27th minute?"})
    assert response.status_code == 200
    data = response.json()
    assert data["persona"] == "analyst"
    assert data["language"] == "English"


def test_ask_invalid_persona_returns_422():
    response = client.post(
        "/api/ask",
        json={"question": "Why was the goal disallowed?", "persona": "referee", "language": "English"},
    )
    assert response.status_code == 422
