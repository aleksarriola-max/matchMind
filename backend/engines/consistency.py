import json
from pathlib import Path

from backend.engines import explainer

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "historical_incidents.json"

with open(DATA_PATH, encoding="utf-8") as _f:
    HISTORICAL_INCIDENTS = json.load(_f)

VALID_TOPICS = ["offside", "handball", "goal-line", "penalty"]

TOPIC_MOMENT_IDS = {"offside": "offside_27", "handball": "handball_38"}


def list_topics() -> list[str]:
    return VALID_TOPICS


def _lead_lower(text: str) -> str:
    return text[0].lower() + text[1:] if text else text


def _compare_one(incident: dict, today: dict | None) -> str | None:
    if today is None:
        return None
    tech = _lead_lower(incident["technology_available"])
    if incident["judgment_correct"]:
        return (
            f"In {incident['year']} ({incident['match']}), {tech} correctly determined the outcome. "
            f"Today's \"{today['decision']}\" call reached {today['confidence']:.1%} confidence using "
            f"similar technology-assisted review — both reflect how review technology helps "
            f"officiating get close calls right."
        )
    return (
        f"In {incident['year']} ({incident['match']}), {tech} meant the on-field decision stood "
        f"uncorrected, even though it was wrong. Today's \"{today['decision']}\" call reached "
        f"{today['confidence']:.1%} confidence using review technology unavailable in "
        f"{incident['year']} — illustrating how much officiating has changed since then."
    )


def compare(topic: str) -> dict:
    moment_id = TOPIC_MOMENT_IDS.get(topic)
    moment = explainer.MATCH_DATA["moments"].get(moment_id) if moment_id else None
    today = (
        {"moment_id": moment_id, "decision": moment["decision"], "confidence": moment["confidence"]}
        if moment is not None
        else None
    )
    incidents = [i for i in HISTORICAL_INCIDENTS if i["topic"] == topic]
    return {
        "topic": topic,
        "today": today,
        "historical_incidents": [
            {**incident, "comparison_to_today": _compare_one(incident, today)}
            for incident in incidents
        ],
    }
