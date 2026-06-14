from backend.engines import explainer
from backend.engines.verifier import verify


def test_route_offside():
    assert explainer.route("Why was the goal disallowed for offside in the 27th minute?") == "offside_27"


def test_route_handball():
    assert explainer.route("Why didn't the referee award a penalty for the handball appeal?") == "handball_38"


def test_route_halftime_shift():
    assert explainer.route("Why did the team switch from a 4-3-3 to a 4-4-2 formation at halftime?") == "halftime_shift"


def test_route_substitution():
    assert explainer.route("Why did they make a substitution and bring on a fresh winger in the 58th minute?") == "sub_58"


def test_route_goal_home_1():
    assert explainer.route("How did the equaliser happen to make it 1-1?") == "goal_home_1"


def test_route_fatigue():
    assert explainer.route("Why did France's pressing collapse due to fatigue late on?") == "fatigue_71"


def test_route_goal_home_2():
    assert explainer.route("How was the winning goal scored from the corner?") == "goal_home_2"


def test_route_general_question_returns_none():
    assert explainer.route("What's the weather forecast for the stadium tonight?") is None


def test_route_tie_breaks_to_lowest_minute():
    assert explainer.route("Tell me about the offside call and the corner routine") == "offside_27"


def test_ground_returns_moment_and_retrieved_for_routed_question():
    result = explainer.ground("Why was the goal disallowed for offside in the 27th minute?", "offside_27")
    assert result["moment"]["title"].startswith("Argentina goal disallowed")
    assert len(result["retrieved"]) == 3


def test_ground_returns_none_moment_for_general_question():
    result = explainer.ground("What's the weather forecast for the stadium tonight?", None)
    assert result["moment"] is None
    assert len(result["retrieved"]) == 3


def test_reason_returns_empty_string_in_demo_mode():
    assert explainer.reason("Why was the goal disallowed?") == ""


def test_compose_demo_for_each_persona_includes_decision_and_evidence():
    moment = explainer.MATCH_DATA["moments"]["offside_27"]
    for persona, (intro, outro) in explainer.PERSONA_TEMPLATES.items():
        answer = explainer.compose_demo(persona, moment, [])
        assert answer.startswith(intro)
        assert answer.endswith(outro)
        assert moment["decision"] in answer
        assert moment["evidence"][0] in answer


def test_compose_demo_general_question_uses_top_retrieved_chunk():
    retrieved = explainer.get_retriever().search("VAR clear and obvious error review", k=3)
    answer = explainer.compose_demo("analyst", None, retrieved)
    first_sentence = retrieved[0]["text"].split(".")[0].replace("\n", " ")
    assert first_sentence in answer


def test_explain_for_measured_moment():
    moment_id = "offside_27"
    grounded = explainer.ground("Why was the goal disallowed for offside in the 27th minute?", moment_id)
    answer = explainer.compose_demo("analyst", grounded["moment"], grounded["retrieved"])
    verification = verify(answer, grounded["moment"]["evidence"])
    result = explainer.explain(moment_id, grounded["moment"], grounded["retrieved"], verification)
    assert result["confidence"] == 0.997
    assert result["confidence_components"]["decision_class"] == "measured"
    assert result["counterfactual"] is not None
    assert result["debate"] is not None
    assert result["lineage"] == "question -> route[offside_27] -> retrieve[3 chunks] -> demo composer -> verifier[lexical]"


def test_explain_for_general_question():
    grounded = explainer.ground("What's the weather forecast for the stadium tonight?", None)
    answer = explainer.compose_demo("analyst", grounded["moment"], grounded["retrieved"])
    evidence = [r["text"] for r in grounded["retrieved"]]
    verification = verify(answer, evidence)
    result = explainer.explain(None, grounded["moment"], grounded["retrieved"], verification)
    assert result["confidence"] == 0.5
    assert result["confidence_components"]["decision_class"] == "general"
    assert result["counterfactual"] is None
    assert result["debate"] is None
    assert result["lineage"] == "question -> route[none] -> retrieve[3 chunks] -> demo composer -> verifier[lexical]"


def test_explain_schema_has_all_required_keys():
    grounded = explainer.ground("Why did France's pressing collapse due to fatigue late on?", "fatigue_71")
    answer = explainer.compose_demo("coach", grounded["moment"], grounded["retrieved"])
    verification = verify(answer, grounded["moment"]["evidence"])
    result = explainer.explain("fatigue_71", grounded["moment"], grounded["retrieved"], verification)
    for key in ["confidence", "confidence_basis", "confidence_components", "sources", "evidence", "counterfactual", "debate", "uncertainty", "lineage"]:
        assert key in result
    for key in ["evidence_coverage", "retrieval_strength_top", "decision_class", "note"]:
        assert key in result["confidence_components"]
