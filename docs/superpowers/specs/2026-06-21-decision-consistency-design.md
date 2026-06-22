# Decision Consistency Analyzer — Design

**Goal:** Build Phase 3 of 3 (evals → outrage → consistency): the
"Decision Consistency Analyzer" CLAUDE.md and README.md already document —
comparing today's match decisions against real World Cup history and
explaining why outcomes differed (rules, technology, or judgment).

**Architecture:** A new static data file of real historical incidents, a
new `consistency.py` engine that pairs each incident with today's matching
moment (when one exists) and generates a deterministic comparison, two new
GET routes, and a 5th frontend tab. No LLM/verifier involvement — this
data is curated historical fact, not a generated claim needing a
hallucination check.

---

## 1. `backend/data/historical_incidents.json`

6 real World Cup incidents (1986–2022), each shaped:

```json
{
  "id": "hand_of_god_1986",
  "year": 1986,
  "match": "Argentina vs England, World Cup quarterfinal",
  "topic": "handball",
  "title": "Maradona's \"Hand of God\"",
  "description": "Diego Maradona punched the ball into the net with his hand during a quarterfinal against England.",
  "decision": "Goal awarded — the referee and linesman did not see the handball and the goal stood.",
  "technology_available": "None — no video assistant referee, no goal-line or handball review technology existed.",
  "rule_at_time": "Law 12 handball decisions relied entirely on the on-field officials' live view.",
  "judgment_correct": false
}
```

The 6 incidents:

| id | year | topic | judgment_correct |
|----|------|-------|-------------------|
| `hand_of_god_1986` | 1986 | handball | false |
| `lampard_2010` | 2010 | goal-line | false |
| `suarez_handball_2010` | 2010 | handball | true |
| `var_penalty_2018` | 2018 | penalty | true |
| `argentina_saudi_offside_2022` | 2022 | offside | true |
| `japan_spain_goal_line_2022` | 2022 | goal-line | true |

`judgment_correct` reflects whether the contemporaneous decision-making
process (human-only or tech-assisted) reached the factually correct
outcome — not a judgment on the rule itself.

## 2. `backend/engines/consistency.py`

```python
VALID_TOPICS = ["offside", "handball", "goal-line", "penalty"]

TOPIC_MOMENT_IDS = {"offside": "offside_27", "handball": "handball_38"}

def list_topics() -> list[str]:
    return VALID_TOPICS

def compare(topic: str) -> dict:
    moment_id = TOPIC_MOMENT_IDS.get(topic)
    moment = explainer.MATCH_DATA["moments"].get(moment_id) if moment_id else None
    today = (
        {"moment_id": moment_id, "decision": moment["decision"], "confidence": moment["confidence"]}
        if moment is not None else None
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

def _compare_one(incident: dict, today: dict | None) -> str | None:
    if today is None:
        return None
    if incident["judgment_correct"]:
        return (
            f"In {incident['year']} ({incident['match']}), {incident['technology_available'].lower()} "
            f"correctly determined the outcome. Today's {today['decision'].lower()} call reached "
            f"{today['confidence']:.1%} confidence using similar technology-assisted review — both "
            f"reflect how review technology helps officiating get close calls right."
        )
    return (
        f"In {incident['year']} ({incident['match']}), {incident['technology_available'].lower()} "
        f"meant the on-field decision stood uncorrected, even though it was wrong. Today's "
        f"{today['decision'].lower()} call reached {today['confidence']:.1%} confidence using "
        f"review technology unavailable in {incident['year']} — illustrating how much officiating "
        f"has changed since then."
    )
```

(Exact prose wording may be refined slightly during implementation — the
structure and the technology/correctness contrast are the load-bearing
part.) `compare()` raises `KeyError`/returns `None` is not used —
`main.py`'s route validates `topic` against `VALID_TOPICS` before calling
and returns 404 for anything else.

## 3. `backend/main.py`

```python
@app.get("/api/consistency")
def consistency_topics():
    return {"topics": consistency.list_topics()}


@app.get("/api/consistency/{topic}")
def consistency_compare(topic: str):
    if topic not in consistency.VALID_TOPICS:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {topic!r}")
    return consistency.compare(topic)
```

## 4. Frontend — 5th tab ("History")

New `<section id="tab-history">`: 4 topic buttons (Offside / Handball /
Goal-line / Penalty) above a result area. Clicking a topic fetches
`GET /api/consistency/{topic}` and renders:

1. If `today` is present: a short "Today's call" card (reusing
   `.confidence-card`) showing the moment's decision + confidence.
2. Each historical incident as a card: year, match, title, description,
   decision, and (if `comparison_to_today` is non-null) the comparison text
   in a `.callout` block. If `today` was null, just the incident's own
   facts with no callout.

## 5. Tests

`tests/test_consistency.py` (new file, mirroring `test_verifier.py`'s
flat style) — one test per topic asserting: correct `today` value (or
`None` for goal-line/penalty), correct incident count for that topic, and
that `comparison_to_today` is non-null exactly when `today` is non-null.
`tests/test_api.py` — add `GET /api/consistency` and one
`GET /api/consistency/{topic}` happy-path test plus a 404 test for an
invalid topic.

## Out of scope

- Any LLM/verifier involvement — this is curated historical fact, not a
  generated claim.
- Topics beyond the 4 documented ones.
- Telegram bot integration.
