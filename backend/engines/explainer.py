import json
from pathlib import Path

from backend.llm import adapter
from backend.rag.retriever import get_retriever

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_match.json"

with open(DATA_PATH, encoding="utf-8") as _f:
    MATCH_DATA = json.load(_f)

MOMENT_MINUTES = {
    "offside_27": 27,
    "handball_38": 38,
    "halftime_shift": 46,
    "sub_58": 58,
    "goal_home_1": 63,
    "fatigue_71": 71,
    "goal_home_2": 84,
}

ROUTE_KEYWORDS = {
    "offside_27": {"offside", "disallowed", "var", "27th", "flag"},
    "handball_38": {"handball", "hand ball", "penalty", "38th", "arm"},
    "halftime_shift": {"halftime", "half-time", "formation", "4-4-2", "4-3-3", "46th", "reshape"},
    "sub_58": {"substitution", "substitute", "winger", "58th", "replace"},
    "goal_home_1": {"equaliser", "equalizer", "1-1", "63rd", "overload"},
    "fatigue_71": {"fatigue", "tired", "tiring", "71st", "collapse", "pressing"},
    "goal_home_2": {"winner", "winning goal", "2-1", "84th", "corner"},
}


def route(question: str) -> str | None:
    q = question.lower()
    best_id = None
    best_score = 0
    for moment_id, _minute in sorted(MOMENT_MINUTES.items(), key=lambda kv: kv[1]):
        score = sum(1 for kw in ROUTE_KEYWORDS[moment_id] if kw in q)
        if score > best_score:
            best_score = score
            best_id = moment_id
    return best_id


PERSONA_TEMPLATES = {
    "beginner": ("Here's a simple way to think about it", "In short, that's the key idea."),
    "analyst": ("Based on the available evidence", "Confidence here is calibrated to the decision class noted above."),
    "kid": ("Okay, here's the fun part", "Pretty cool, right?"),
    "journalist": ("Here's what we know", "As always, some uncertainty remains."),
    "coach": ("Here's the pattern to watch for", "That's the coaching point to take away."),
}


def ground(question: str, moment_id: str | None) -> dict:
    retrieved = get_retriever().search(question, k=3)
    moment = MATCH_DATA["moments"].get(moment_id) if moment_id else None
    return {"retrieved": retrieved, "moment": moment}


def reason(question: str) -> str:
    return adapter.generate("", question)


def compose_demo(persona: str, moment: dict | None, retrieved: list[dict]) -> str:
    intro, outro = PERSONA_TEMPLATES[persona]
    if moment is not None:
        body = moment["decision"] + " — " + " ".join(moment["evidence"][:2])
    elif retrieved:
        body = retrieved[0]["text"].replace("\n", " ")
    else:
        body = "No grounded information is available for this question."
    body = body.rstrip(".")
    return f"{intro} — {body} — {outro}"
