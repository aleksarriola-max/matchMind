# Live Prediction Confidence Meter — Design

**Goal:** Add a live-updating "confidence the current leader wins" meter to the
Live Replay tab, computed from a real, documented formula (goal lead,
time remaining, momentum) rather than an LLM guess — consistent with every
other number in matchMind.

**Scope:** Live Replay tab only. Not added to Overview (a single fixed
end-of-match number there would be a much weaker version of the same idea
the team already gets from Overview's existing momentum chart and event
list).

## 1. `backend/engines/analytics.py` — `live_win_confidence`

```python
import math

def live_win_confidence(events: list, momentum_curve: list, home_name: str, away_name: str) -> list:
    """
    One point per momentum_curve minute. Confidence is always P(current
    leader wins) -- 0.5 when scores are level (no leader).

    Formula (illustrative coefficients, same convention as
    offside_probability/fatigue_index):
        goal_diff = |home_goals - away_goals| at this minute
        momentum_oriented = momentum_value, sign-flipped to align with
            whichever team currently leads (positive = leader's favor)
        raw = goal_diff * (1.5 + 2.5 * minute / 90) + 0.05 * momentum_oriented
        confidence = sigmoid(raw)

    The (1.5 + 2.5 * minute/90) term means the same goal lead is worth more
    confidence as time runs out (~65% for a 1-goal lead at minute 0, ~93%+
    near full time). Momentum is a smaller secondary signal.
    """
```

Returns `[{"minute": int, "leader": "home" | "away" | None, "confidence": float, "explanation": str}, ...]`, one entry per `momentum_curve` point (same 5-minute grid, reusing it directly rather than recomputing goal state on a separate grid).

`explanation` is a deterministic f-string template, two variants:
- No leader: `"Scores level at {h}-{a} — no clear favorite yet."`
- Leader exists: `"{leader_name}'s {goal_diff}-goal lead with {minutes_left} minutes left, {momentum_clause}gives an estimated {pct}% chance of winning."` where `momentum_clause` is `"plus strongly positive momentum ({value:+.1f}), "` (or "fading"/omitted for small values — exact wording thresholds decided during implementation) and empty string when momentum is negligible.

## 2. `app/main.py`

```python
match_data["win_confidence"] = analytics.live_win_confidence(
    explainer.MATCH_DATA["events"], match_data["momentum"],
    match_data["home"]["name"], match_data["away"]["name"],
)
```

Added right after the existing `momentum_curve` call, reusing its output — no new backend dependency, no network/HTTP involved.

## 3. `app/replay.py` (the JS island)

`match_data["win_confidence"]` is serialized into the same `payload` JSON
already embedded for `home`/`away`/`events`/`momentum`. A new UI block sits
below the minute/score header: leader name + percentage, a small inline-
styled progress bar (visual style modeled on the app's existing glow-bar
look, hand-rolled in this file's own CSS since the iframe is self-contained
and can't reuse `app/components.py`), and the explanation sentence. Updated
every tick in `renderState()` via the same nearest-point-at-or-before-minute
lookup the momentum chart already uses against `matchData.momentum`.

## 4. Testing

`tests/test_analytics.py` new cases:
- Tied score → `confidence == 0.5`, `leader is None`.
- One-goal lead at minute 0 vs. minute 85 → confidence strictly higher at 85.
- Two-goal lead vs. one-goal lead at the same minute → two-goal is higher.
- A lead change mid-match (e.g. away scores twice after home's early goal) →
  `leader` flips from `"home"` to `"away"` at the correct minute, and
  confidence resets relative to the new leader (not carried over from the
  old one).

## Out of scope

- Overview tab placement (decided against — see Scope above).
- Any of the other 7 brainstormed feature ideas from this round — each
  would get its own brainstorming pass if picked up later.
- Real social-sentiment data, real win-probability ML models, or any
  external data source — this is a hand-computed illustrative formula like
  every other analytics model in this app.
