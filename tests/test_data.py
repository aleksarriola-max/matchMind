import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "sample_match.json"

MOMENT_IDS = [
    "offside_27",
    "handball_38",
    "halftime_shift",
    "sub_58",
    "goal_home_1",
    "fatigue_71",
    "goal_home_2",
]


def load_match():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_top_level_keys():
    data = load_match()
    for key in ["match_id", "competition", "home", "away", "score", "events", "momentum", "moments"]:
        assert key in data


def test_score_is_2_1():
    data = load_match()
    assert data["score"] == {"home": 2, "away": 1}


def test_all_seven_moments_present():
    data = load_match()
    for moment_id in MOMENT_IDS:
        assert moment_id in data["moments"], f"missing moment {moment_id}"


def test_moment_dossier_required_fields():
    data = load_match()
    for moment_id in MOMENT_IDS:
        moment = data["moments"][moment_id]
        for field in ["title", "law", "decision", "confidence", "summary", "evidence", "counterfactual", "referee_view", "debate"]:
            assert field in moment, f"{moment_id} missing field {field}"
        assert isinstance(moment["evidence"], list) and len(moment["evidence"]) >= 1


def test_offside_27_has_pitch_geometry():
    data = load_match()
    pitch = data["moments"]["offside_27"]["pitch"]
    for field in ["offside_line_x", "ball", "passer", "attacker", "second_last_defender", "keeper", "others", "assistant_referee"]:
        assert field in pitch
    assert pitch["attacker"]["offside"] is True


def test_momentum_covers_full_match():
    data = load_match()
    minutes = [p["minute"] for p in data["momentum"]]
    assert minutes[0] == 0
    assert minutes[-1] == 90
    assert minutes == sorted(minutes)


def test_decision_classes_match_confidence_levels():
    data = load_match()
    # measured (offside) should be the most confident, general/tactical the least
    assert data["moments"]["offside_27"]["confidence"] > data["moments"]["handball_38"]["confidence"]
    assert data["moments"]["handball_38"]["confidence"] > data["moments"]["sub_58"]["confidence"]


KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "knowledge" / "laws_and_tactics.md"


def test_knowledge_pack_has_nine_sections():
    text = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    sections = [line for line in text.splitlines() if line.startswith("## ")]
    assert len(sections) == 9


def test_knowledge_pack_covers_key_numbers():
    text = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    for number in ["11 cm", "99.7%", "250 ms", "53 ms", "4-3-3", "4-4-2", "63rd", "84th", "71st"]:
        assert number in text, f"missing {number!r} in knowledge pack"


def test_offside_27_has_counterfactual_inputs():
    data = load_match()
    moment = data["moments"]["offside_27"]
    assert moment["attacker_speed_ms"] == 7


def test_handball_38_has_reaction_inputs():
    data = load_match()
    moment = data["moments"]["handball_38"]
    assert moment["deflection_distance_m"] == 1.06
    assert moment["ball_speed_ms"] == 20
