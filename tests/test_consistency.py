from backend.engines import consistency


def test_offside_topic_has_today_and_one_incident():
    result = consistency.compare("offside")
    assert result["today"] == {
        "moment_id": "offside_27",
        "decision": "Goal disallowed for offside",
        "confidence": 0.997,
    }
    assert len(result["historical_incidents"]) == 1
    assert result["historical_incidents"][0]["id"] == "argentina_saudi_offside_2022"
    assert result["historical_incidents"][0]["comparison_to_today"] is not None


def test_handball_topic_has_today_and_two_incidents():
    result = consistency.compare("handball")
    assert result["today"]["moment_id"] == "handball_38"
    incident_ids = {i["id"] for i in result["historical_incidents"]}
    assert incident_ids == {"hand_of_god_1986", "suarez_handball_2010"}
    for incident in result["historical_incidents"]:
        assert incident["comparison_to_today"] is not None


def test_goal_line_topic_has_no_today_comparison():
    result = consistency.compare("goal-line")
    assert result["today"] is None
    incident_ids = {i["id"] for i in result["historical_incidents"]}
    assert incident_ids == {"lampard_2010", "japan_spain_goal_line_2022"}
    for incident in result["historical_incidents"]:
        assert incident["comparison_to_today"] is None


def test_penalty_topic_has_no_today_comparison():
    result = consistency.compare("penalty")
    assert result["today"] is None
    assert len(result["historical_incidents"]) == 1
    assert result["historical_incidents"][0]["id"] == "var_penalty_2018"
    assert result["historical_incidents"][0]["comparison_to_today"] is None


def test_list_topics():
    assert consistency.list_topics() == ["offside", "handball", "goal-line", "penalty"]
