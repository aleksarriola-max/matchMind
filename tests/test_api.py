import pytest
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


def test_root_contains_ask_form():
    response = client.get("/")
    html = response.text
    assert 'id="ask-form"' in html
    assert 'id="question"' in html
    assert 'id="persona"' in html
    assert 'id="language"' in html
    for persona in ["beginner", "analyst", "kid", "journalist", "coach"]:
        assert f'value="{persona}"' in html


MOMENT_QUESTIONS = {
    "offside_27": "Why was the goal disallowed for offside in the 27th minute?",
    "handball_38": "Why didn't the referee award a penalty for the handball appeal?",
    "halftime_shift": "Why did the team switch from a 4-3-3 to a 4-4-2 formation at halftime?",
    "sub_58": "Why did they make a substitution and bring on a fresh winger in the 58th minute?",
    "goal_home_1": "How did the equaliser happen to make it 1-1?",
    "fatigue_71": "Why did Borealia's pressing collapse due to fatigue late on?",
    "goal_home_2": "How was the winning goal scored from the corner?",
}

PERSONAS = ["beginner", "analyst", "kid", "journalist", "coach"]


def test_ask_every_moment_and_persona_is_verified():
    for moment_id, question in MOMENT_QUESTIONS.items():
        for persona in PERSONAS:
            response = client.post("/api/ask", json={"question": question, "persona": persona, "language": "English"})
            assert response.status_code == 200, (moment_id, persona, response.text)
            data = response.json()
            assert data["moment_id"] == moment_id, (moment_id, persona, data["moment_id"])
            assert data["verification"]["verified"] is True, (moment_id, persona, data["verification"])
            assert data["verification"]["method"] == "lexical"


def test_ask_general_question_is_verified():
    response = client.post(
        "/api/ask",
        json={"question": "What's the weather forecast for the stadium tonight?", "persona": "analyst", "language": "English"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["moment_id"] is None
    assert data["verification"]["verified"] is True
    assert data["verification"]["method"] == "lexical"


def test_analytics_endpoint_has_all_six_models():
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    for key in [
        "offside_probability",
        "offside_sensitivity",
        "counterfactual_timing",
        "handball_reaction",
        "fatigue_index",
        "momentum_curve",
    ]:
        assert key in data, key
        for subkey in ["formula", "inputs", "result"]:
            assert subkey in data[key], (key, subkey)
    assert data["offside_probability"]["result"]["probability"] == pytest.approx(0.997, abs=0.001)
    assert data["counterfactual_timing"]["result"]["delay_needed_ms"] == pytest.approx(15.7, abs=0.05)
    assert data["handball_reaction"]["result"]["time_available_ms"] == 53.0
    assert "home" in data["fatigue_index"]["result"]
    assert "away" in data["fatigue_index"]["result"]
    assert len(data["momentum_curve"]["result"]) == 19
