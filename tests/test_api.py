import pytest
from fastapi.testclient import TestClient

from backend.engines import explainer
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
    assert response.json()["title"].startswith("Argentina goal disallowed")


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
    "fatigue_71": "Why did France's pressing collapse due to fatigue late on?",
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
    assert "fatigue_comparison" in data
    assert data["fatigue_comparison"]["result"]["more_fatigued_team"] == "away"
    assert "summary" in data["momentum_curve"]
    assert data["momentum_curve"]["summary"]["dominant_team"] == "home"


def test_match_momentum_is_computed_curve():
    response = client.get("/api/match")
    assert response.status_code == 200
    data = response.json()
    momentum = data["momentum"]
    assert len(momentum) == 19
    for point in momentum:
        assert "minute" in point and "value" in point
    minutes = [p["minute"] for p in momentum]
    assert minutes == list(range(0, 91, 5))
    by_minute = {p["minute"]: p["value"] for p in momentum}
    assert by_minute[20] == pytest.approx(-29.0, abs=0.5)


def test_moment_offside_27_has_analytics():
    response = client.get("/api/moment/offside_27")
    assert response.status_code == 200
    data = response.json()
    analytics_data = data["analytics"]
    for key in ["offside_probability", "offside_sensitivity", "counterfactual_timing"]:
        assert key in analytics_data, key
    assert analytics_data["offside_probability"]["result"]["probability"] == pytest.approx(0.997, abs=0.001)


def test_moment_handball_38_has_analytics():
    response = client.get("/api/moment/handball_38")
    assert response.status_code == 200
    data = response.json()
    assert "handball_reaction" in data["analytics"]
    assert data["analytics"]["handball_reaction"]["result"]["time_available_ms"] == 53.0


def test_moment_fatigue_71_has_analytics():
    response = client.get("/api/moment/fatigue_71")
    assert response.status_code == 200
    data = response.json()
    fatigue = data["analytics"]["fatigue_index"]
    assert "home" in fatigue and "away" in fatigue
    assert fatigue["away"]["fatigue_index"][4] == pytest.approx(40.7, abs=0.1)
    assert "fatigue_comparison" in data["analytics"]
    assert data["analytics"]["fatigue_comparison"]["more_fatigued_team"] == "away"


def test_moment_halftime_shift_has_null_analytics():
    response = client.get("/api/moment/halftime_shift")
    assert response.status_code == 200
    assert response.json()["analytics"] is None


def test_moment_sub_58_has_null_analytics():
    response = client.get("/api/moment/sub_58")
    assert response.status_code == 200
    assert response.json()["analytics"] is None


def test_outrage_offside_27_returns_debate():
    take = "That offside call was robbery, the goal should have stood!"
    response = client.post("/api/outrage", json={"take": take})
    assert response.status_code == 200
    data = response.json()
    assert data["moment_id"] == "offside_27"
    assert data["steelman"] == (
        "Even a 99.7% confident measurement carries a small chance of error, and a "
        "margin smaller than the width of a boot stud arguably should not decide a "
        "goal at the highest level of the sport."
    )
    assert data["counter"] == (
        "Under Law 11, semi-automated offside technology measured the attacker 11 cm "
        "beyond the second-last defender, and combining the camera and limb-line "
        "uncertainties gives roughly 99.7% confidence that the attacker was "
        "genuinely in an offside position."
    )
    assert "99.7%" in data["verdict"]
    assert data["verification"]["verified"] is True


def test_outrage_handball_38_returns_debate():
    take = "No way that handball deserved a penalty, total joke of a decision!"
    response = client.post("/api/outrage", json={"take": take})
    assert response.status_code == 200
    data = response.json()
    assert data["moment_id"] == "handball_38"
    assert data["steelman"] is not None
    assert data["counter"] is not None
    assert "74.0%" in data["verdict"]
    assert data["verification"]["verified"] is True


def test_outrage_no_debate_moment_omits_steelman_and_counter():
    take = "Switching to a 4-4-2 at halftime was a disaster tactically."
    response = client.post("/api/outrage", json={"take": take})
    assert response.status_code == 200
    data = response.json()
    assert data["moment_id"] == "halftime_shift"
    assert data["steelman"] is None
    assert data["counter"] is None
    assert data["verdict"] is None
    assert data["verification"] is None
    assert data["summary"] == explainer.MATCH_DATA["moments"]["halftime_shift"]["summary"]


def test_consistency_topics():
    response = client.get("/api/consistency")
    assert response.status_code == 200
    assert response.json() == {"topics": ["offside", "handball", "goal-line", "penalty"]}


def test_consistency_offside_topic():
    response = client.get("/api/consistency/offside")
    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "offside"
    assert data["today"]["moment_id"] == "offside_27"
    assert len(data["historical_incidents"]) == 1


def test_consistency_invalid_topic_returns_404():
    response = client.get("/api/consistency/nonexistent")
    assert response.status_code == 404


def test_outrage_offtopic_take_has_no_moment():
    take = "What is the weather like today?"
    response = client.post("/api/outrage", json={"take": take})
    assert response.status_code == 200
    data = response.json()
    assert data["moment_id"] is None
    assert data["steelman"] is None
    assert data["counter"] is None
    assert data["verdict"] is None
    assert data["verification"] is None
    assert data["summary"]
