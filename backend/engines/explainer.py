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


DECISION_CLASS = {
    "offside_27": "measured",
    "handball_38": "judgment",
    "halftime_shift": "general",
    "sub_58": "general",
    "goal_home_1": "general",
    "fatigue_71": "inferred",
    "goal_home_2": "general",
}

GENERAL_PRIOR_CONFIDENCE = 0.5

CONFIDENCE_NOTES = {
    "measured": "Confidence reflects a statistical model with quantified measurement error.",
    "judgment": "Confidence reflects a judgment call calibrated against reaction-time benchmarks.",
    "inferred": "Confidence reflects an inference from indirect indicators, not a direct measurement.",
    "general": "Confidence reflects a general prior for non-decision questions.",
}


def explain(moment_id: str | None, moment: dict | None, retrieved: list[dict], verification: dict) -> dict:
    decision_class = DECISION_CLASS.get(moment_id, "general")
    confidence = moment["confidence"] if moment is not None else GENERAL_PRIOR_CONFIDENCE
    sources = [
        {"title": r["title"], "source": r["source"], "score": r["score"]}
        for r in retrieved
    ]
    evidence = moment["evidence"] if moment is not None else [r["text"] for r in retrieved]
    uncertainty = f"Approximately {round((1 - confidence) * 100, 1)}% residual uncertainty in this explanation."
    return {
        "confidence": confidence,
        "confidence_basis": moment["decision"] if moment is not None else "General response grounded in retrieved knowledge.",
        "confidence_components": {
            "evidence_coverage": verification["coverage"],
            "retrieval_strength_top": retrieved[0]["score"] if retrieved else 0.0,
            "decision_class": decision_class,
            "note": CONFIDENCE_NOTES[decision_class],
        },
        "sources": sources,
        "evidence": evidence,
        "counterfactual": moment["counterfactual"] if moment is not None else None,
        "debate": moment["debate"] if moment is not None else None,
        "uncertainty": uncertainty,
        "lineage": f"question -> route[{moment_id or 'none'}] -> retrieve[{len(retrieved)} chunks] -> demo composer -> verifier[lexical]",
    }
