# "Explain My Outrage" — Design

**Goal:** Build `POST /api/outrage` (Phase 2 of 3: evals → outrage → consistency),
matching the schema CLAUDE.md already documents (`{take, language} -> steelman
+ counter + verdict`) and the framing in README.md: "paste your hot take;
MatchMind steelmans YOUR side first, then the strongest counter-case."

**Architecture:** Reuses the existing route → ground pipeline from
`explainer.py`. A new `explainer.outrage(take: str) -> dict` function and a
new `/api/outrage` route in `main.py`. A 4th frontend tab ("Debate") renders
the response. No new data files — draws entirely on `sample_match.json`'s
existing `debate` field (populated only for `offside_27` and `handball_38`).

---

## 1. `backend/engines/explainer.py` — `outrage()`

```python
VERDICT_TEMPLATE = (
    "Both sides raise fair points, but the grounded evidence gives {confidence:.1%} "
    "confidence that the decision under {law} was correct: {decision}."
)

def outrage(take: str) -> dict:
    moment_id = route(take)
    moment = MATCH_DATA["moments"].get(moment_id) if moment_id else None

    if moment is not None and moment["debate"] is not None:
        steelman = moment["debate"]["overturn"]
        counter = moment["debate"]["stands"]
        verdict = VERDICT_TEMPLATE.format(
            confidence=moment["confidence"], law=moment["law"], decision=moment["decision"]
        )
        return {
            "moment_id": moment_id,
            "summary": moment["summary"],
            "steelman": steelman,
            "counter": counter,
            "verdict": verdict,
            "confidence": moment["confidence"],
            "evidence": moment["evidence"],
            "lineage": f"take -> route[{moment_id}] -> debate[overturn/stands] -> verifier[lexical]",
        }

    if moment is not None:
        return {
            "moment_id": moment_id,
            "summary": moment["summary"],
            "steelman": None,
            "counter": None,
            "verdict": None,
            "confidence": moment["confidence"],
            "evidence": None,
            "lineage": f"take -> route[{moment_id}] -> no debate -> verifier[none]",
        }

    retrieved = get_retriever().search(take, k=3)
    summary = retrieved[0]["text"] if retrieved else "No grounded information is available for this take."
    return {
        "moment_id": None,
        "summary": summary,
        "steelman": None,
        "counter": None,
        "verdict": None,
        "confidence": GENERAL_PRIOR_CONFIDENCE,
        "evidence": None,
        "lineage": f"take -> route[none] -> retrieve[{len(retrieved)} chunks] -> verifier[none]",
    }
```

Steelman is always the `overturn` side (the case against the call — "your
side," since outrage implies disagreement with the decision); counter is
always `stands` (the official justification). No sentiment detection —
deterministic, matching the rest of the app's no-fake-NLU demo philosophy.

## 2. `backend/main.py` — request model + route

```python
class OutrageRequest(BaseModel):
    take: str
    language: str = "English"


@app.post("/api/outrage")
def outrage(request: OutrageRequest):
    result = explainer.outrage(request.take)
    verification = None
    if result["counter"] is not None:
        verification = verify(result["counter"], result["evidence"])
    return {
        "take": request.take,
        "language": "English",
        "moment_id": result["moment_id"],
        "summary": result["summary"],
        "steelman": result["steelman"],
        "counter": result["counter"],
        "verdict": result["verdict"],
        "confidence": result["confidence"],
        "verification": verification,
        "lineage": result["lineage"],
    }
```

Only the `counter` text is verified (the evidence-grounded official
explanation, reusing the same `moment["evidence"]` list `/api/ask` uses for
this moment). The `steelman` is explicitly one-sided argumentation, not a
factual claim, so it isn't run through the hallucination firewall.

## 3. Frontend — 4th tab ("Debate")

New `<section id="tab-outrage">` alongside the existing three, added to
`setupTabs()`'s tab list and a `<button>Debate</button>` in the nav.
Contents: a `<textarea>` for the take + submit button (same form pattern as
the Ask MatchMind tab), rendering:

1. Echo of the user's take.
2. `summary` ("What actually happened").
3. If `steelman`/`counter` are present: steelman rendered **first** (per
   README's "steelmans YOUR side first"), then counter — reusing the
   existing `.debate-cols` two-column CSS from the Decision Lab, but with
   the steelman column shown before the counter column rather than as a
   side-by-side stands/overturn pair.
4. `verdict` in a `.callout` block (reusing the counterfactual-callout
   style), with the `verification` badge (reusing `.badge`/`.confidence-card`
   from the Ask MatchMind tab) attached to the counter section specifically.
5. If `steelman` is `null` (no-debate or no-moment case): a short note —
   "This isn't a contested officiating call, so there's no counter-case
   here — just what happened." — instead of the debate columns.

## 4. Tests

`tests/test_api.py`, mirroring the existing `/api/ask` golden-question
pattern — for each test "take," first empirically verify via `route()` that
it routes to the intended moment (or `None`) before asserting on it, same
lesson learned from the Phase 1 eval harness:

- One take for `offside_27` → asserts `steelman == debate.overturn`,
  `counter == debate.stands`, `verdict` contains `"99.7%"`, `verification.verified is True`.
- One take for `handball_38` → same shape, confidence `"74.0%"`.
- One take for a no-debate moment (e.g. `halftime_shift`) → asserts
  `steelman`/`counter`/`verdict`/`verification` are all `None`, `summary`
  equals the moment's `summary` field.
- One off-topic take → asserts `moment_id is None`, `steelman` etc. are
  `None`, `summary` is non-empty (either retrieved text or the fallback
  message).

## Out of scope

- Phase 3 (Decision Consistency Analyzer).
- Telegram bot integration (`integrations/telegram_bot.py` doesn't exist yet
  — separate, later work, despite CLAUDE.md's file map mentioning it reuses
  `outrage`).
- Sentiment/stance detection — steelman is always the `overturn` side.
- Persona parameter — not part of the documented `{take, language}` schema.
