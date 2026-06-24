# Live Prediction Confidence Meter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live-updating "confidence the current leader wins" meter to the Live Replay tab, driven by a real documented formula (time-weighted goal lead + a smaller momentum term, through a sigmoid), not an LLM guess.

**Architecture:** A new pure, unit-tested function `analytics.live_win_confidence` computes one confidence point per `momentum_curve` minute (reusing its existing 5-minute grid). `app/main.py` computes it once and embeds it into `match_data`. `app/replay.py`'s self-contained JS island reads it via the same nearest-point lookup pattern it already uses for the momentum chart, and renders a leader/percentage/bar/explanation block.

**Tech Stack:** Python (`backend/engines/analytics.py`), Streamlit (`app/main.py`), vanilla JS inside the existing `st.components.v1.html` island (`app/replay.py`).

## Global Constraints

- Confidence formula: `goal_diff * (1.5 + 2.5 * minute / 90) + 0.05 * momentum_oriented`, run through `sigmoid`. Tied score → `confidence = 0.5`, `leader = None`. These exact coefficients (`1.5`, `2.5`, `0.05`) are illustrative, documented as such — same convention as `offside_probability`/`fatigue_index`.
- Computed at the same 5-minute grid as `momentum_curve` (minutes `0, 5, 10, ..., 90`) — reuse its output directly, don't recompute a separate grid.
- `explanation` is a deterministic f-string template — no LLM call.
- Live Replay tab only — not added to Overview.
- `CLAUDE.md`'s "What NOT to do" section currently says "Do not add score prediction features — explicitly out of scope." This plan includes updating that line to carve out an explicit, narrow exception for this feature (a computed live confidence meter, not a final-score predictor) — this is a deliberate, user-approved scope change, not an oversight to silently work around.

---

### Task 1: `analytics.live_win_confidence`

**Files:**
- Modify: `backend/engines/analytics.py` (add function; add `import math` if not already present — check first)
- Test: `tests/test_analytics.py`

**Interfaces:**
- Consumes: `events: list[dict]` (existing shape: `{"minute": int, "type": str, "team": "home"|"away", "desc": str, "id": str optional}`), `momentum_curve: list[dict]` (existing shape: `{"minute": int, "value": float}`, output of `analytics.momentum_curve`)
- Produces: `live_win_confidence(events, momentum_curve, home_name, away_name) -> list[dict]`, each dict: `{"minute": int, "leader": "home" | "away" | None, "confidence": float, "explanation": str}`

- [ ] **Step 1: Check whether `math` is already imported in analytics.py**

Run: `grep -n "^import math" backend/engines/analytics.py`
If it prints nothing, you'll add the import in Step 3.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_analytics.py`:

```python
def _confidence_events_one_goal_lead():
    return [{"minute": 10, "type": "goal", "team": "home", "desc": "Home scores"}]


def _confidence_momentum_flat():
    return [{"minute": m, "value": 0.0} for m in range(0, 91, 5)]


def test_live_win_confidence_tied_score_is_neutral():
    events = []
    momentum = _confidence_momentum_flat()
    curve = analytics.live_win_confidence(events, momentum, "Argentina", "France")
    for point in curve:
        assert point["leader"] is None
        assert point["confidence"] == 0.5
        assert "level" in point["explanation"].lower()


def test_live_win_confidence_rises_with_time_for_same_lead():
    events = _confidence_events_one_goal_lead()
    momentum = _confidence_momentum_flat()
    curve = analytics.live_win_confidence(events, momentum, "Argentina", "France")
    early = next(p for p in curve if p["minute"] == 10)
    late = next(p for p in curve if p["minute"] == 85)
    assert early["leader"] == "home"
    assert late["leader"] == "home"
    assert late["confidence"] > early["confidence"]


def test_live_win_confidence_two_goal_lead_beats_one_goal_lead():
    momentum = _confidence_momentum_flat()
    one_goal = analytics.live_win_confidence(
        [{"minute": 10, "type": "goal", "team": "home", "desc": "x"}],
        momentum, "Argentina", "France",
    )
    two_goal = analytics.live_win_confidence(
        [
            {"minute": 10, "type": "goal", "team": "home", "desc": "x"},
            {"minute": 20, "type": "goal", "team": "home", "desc": "y"},
        ],
        momentum, "Argentina", "France",
    )
    one_at_50 = next(p for p in one_goal if p["minute"] == 50)
    two_at_50 = next(p for p in two_goal if p["minute"] == 50)
    assert two_at_50["confidence"] > one_at_50["confidence"]


def test_live_win_confidence_leader_changes_on_comeback():
    events = [
        {"minute": 10, "type": "goal", "team": "home", "desc": "Home scores"},
        {"minute": 40, "type": "goal", "team": "away", "desc": "Away equalises"},
        {"minute": 41, "type": "goal", "team": "away", "desc": "Away takes the lead"},
    ]
    momentum = _confidence_momentum_flat()
    curve = analytics.live_win_confidence(events, momentum, "Argentina", "France")
    at_20 = next(p for p in curve if p["minute"] == 20)
    at_45 = next(p for p in curve if p["minute"] == 45)
    assert at_20["leader"] == "home"
    assert at_45["leader"] == "away"


def test_live_win_confidence_explanation_mentions_leader_name():
    events = _confidence_events_one_goal_lead()
    momentum = _confidence_momentum_flat()
    curve = analytics.live_win_confidence(events, momentum, "Argentina", "France")
    at_50 = next(p for p in curve if p["minute"] == 50)
    assert "Argentina" in at_50["explanation"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k live_win_confidence`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'live_win_confidence'`

- [ ] **Step 4: Implement `live_win_confidence` in `backend/engines/analytics.py`**

Add `import math` near the top of the file if Step 1 found it missing. Then add:

```python
def live_win_confidence(events: list, momentum_curve: list, home_name: str, away_name: str) -> list:
    """
    One point per momentum_curve minute. Confidence is always P(current
    leader wins) -- 0.5 when scores are level (no leader).

    Illustrative formula (same convention as offside_probability/fatigue_index):
        goal_diff = |home_goals - away_goals| at this minute
        momentum_oriented = momentum value, sign-flipped to align with
            whichever team currently leads (positive = leader's favor)
        raw = goal_diff * (1.5 + 2.5 * minute / 90) + 0.05 * momentum_oriented
        confidence = sigmoid(raw)

    The time-weighting term means the same goal lead is worth more
    confidence as the match runs out of clock; momentum is a smaller
    secondary signal.
    """
    points = []
    for m in momentum_curve:
        minute = m["minute"]
        home_goals = sum(1 for e in events if e["type"] == "goal" and e["team"] == "home" and e["minute"] <= minute)
        away_goals = sum(1 for e in events if e["type"] == "goal" and e["team"] == "away" and e["minute"] <= minute)

        if home_goals == away_goals:
            points.append({
                "minute": minute,
                "leader": None,
                "confidence": 0.5,
                "explanation": f"Scores level at {home_goals}-{away_goals} — no clear favorite yet.",
            })
            continue

        leader = "home" if home_goals > away_goals else "away"
        leader_name = home_name if leader == "home" else away_name
        goal_diff = abs(home_goals - away_goals)
        momentum_oriented = m["value"] if leader == "home" else -m["value"]

        raw = goal_diff * (1.5 + 2.5 * minute / 90) + 0.05 * momentum_oriented
        confidence = 1 / (1 + math.exp(-raw))
        pct = round(confidence * 100)
        minutes_left = 90 - minute

        if abs(momentum_oriented) >= 15:
            momentum_clause = f"plus strongly positive momentum ({momentum_oriented:+.1f}), "
        else:
            momentum_clause = ""

        explanation = (
            f"{leader_name}'s {goal_diff}-goal lead with {minutes_left} minutes left, "
            f"{momentum_clause}gives an estimated {pct}% chance of winning."
        )

        points.append({
            "minute": minute,
            "leader": leader,
            "confidence": round(confidence, 4),
            "explanation": explanation,
        })

    return points
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k live_win_confidence`
Expected: 6 passed

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (109 — 103 existing + 6 new)

- [ ] **Step 7: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "Add live_win_confidence analytics model"
```

---

### Task 2: Wire into `app/main.py`, update `CLAUDE.md`

**Files:**
- Modify: `app/main.py`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `analytics.live_win_confidence(events, momentum_curve, home_name, away_name) -> list[dict]` (Task 1)
- Produces: `match_data["win_confidence"]` — the new list, available to `app/replay.py` (Task 3) via the `match_data` dict already passed into `replay.render_replay`

- [ ] **Step 1: Modify `app/main.py`**

Current relevant block:

```python
match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "events": explainer.MATCH_DATA["events"],
    "momentum": analytics.momentum_curve(
        explainer.MATCH_DATA["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    ),
}
```

Replace with:

```python
match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "events": explainer.MATCH_DATA["events"],
    "momentum": analytics.momentum_curve(
        explainer.MATCH_DATA["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    ),
}
match_data["win_confidence"] = analytics.live_win_confidence(
    match_data["events"], match_data["momentum"], match_data["home"]["name"], match_data["away"]["name"],
)
```

- [ ] **Step 2: Update `CLAUDE.md`'s "What NOT to do" section**

Find:

```markdown
## What NOT to do

- Do not add score prediction features — explicitly out of scope.
```

Replace with:

```markdown
## What NOT to do

- Do not add final-score prediction (e.g. "predicted final score: 2-1") — that's a
  different product (a betting/forecasting tool), not an explainability companion.
  The one narrow exception is the Live Replay tab's win-confidence meter
  (`analytics.live_win_confidence`) — it explains *why* the current leader looks
  likely to hold on, using the same computed-analytics-with-explicit-formula
  pattern as everything else, not a opaque predictive model. Don't generalize
  from that one exception to "predictive features are fine now."
```

- [ ] **Step 3: Add a model entry to `CLAUDE.md`'s "Computed analytics models" section**

Find the end of section "### 6. Offside sensitivity analysis" (right before the `---` that follows it) and add a new subsection after it:

```markdown

### 7. Live win confidence (Live Replay tab only)
```
goal_diff = |home_goals - away_goals| at this minute
momentum_oriented = momentum value, sign-flipped toward whichever team leads
raw = goal_diff * (1.5 + 2.5 * minute / 90) + 0.05 * momentum_oriented
confidence = sigmoid(raw)
```
Tied score -> confidence = 0.5, no leader. Same goal lead is worth more
confidence as the clock runs down. `analytics.live_win_confidence()` returns
one point per `momentum_curve` minute; `app/replay.py`'s embedded JS looks
up the nearest point each tick.
```

- [ ] **Step 4: Verify the app still boots**

Run: `python -m streamlit run app/main.py --server.headless true --server.port 8510 &`, then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8510 --max-time 10`
Expected: `200`. Stop the server afterward.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing, no regressions

- [ ] **Step 6: Commit**

```bash
git add app/main.py CLAUDE.md
git commit -m "Wire live_win_confidence into match_data; update CLAUDE.md scope rule"
```

---

### Task 3: Confidence meter UI in `app/replay.py`

**Files:**
- Modify: `app/replay.py`

**Interfaces:**
- Consumes: `match_data["win_confidence"]` (Task 2), already present in the `match_data` dict passed into `render_replay(match_data)`

- [ ] **Step 1: Read the current `app/replay.py` in full**

Confirm the exact current structure of the `payload` JSON build, the CSS block, the HTML body, and `renderState()` before editing — this task adds to all four without disturbing existing behavior (play/pause/speed/seek/banner/momentum/ticker must keep working exactly as before).

- [ ] **Step 2: Add `win_confidence` to the embedded JSON payload**

In the `payload = json.dumps({...})` call, add `"win_confidence": match_data["win_confidence"],` alongside the existing `"home"`, `"away"`, `"events"`, `"momentum"` keys.

- [ ] **Step 3: Add CSS for the confidence meter**

In the embedded `<style>` block, add:

```css
.confidence-wrap {{ margin-bottom: 14px; }}
.confidence-label {{ display: flex; justify-content: space-between; font-size: 0.85em; margin-bottom: 4px; }}
.confidence-bar {{ background: #1c1c24; border-radius: 6px; height: 10px; overflow: hidden; }}
.confidence-bar .fill {{ height: 100%; background: #00e0ff; transition: width 0.4s ease-out; }}
.confidence-explanation {{ color: #999; font-size: 0.8em; margin-top: 4px; }}
```

- [ ] **Step 4: Add the HTML element**

In the body, right after the `<div class="replay-header">...</div>` block and before `<div class="replay-controls">`, add:

```html
<div class="confidence-wrap" id="confidence-wrap"></div>
```

- [ ] **Step 5: Add the lookup + render logic in the embedded `<script>`**

Add a helper function near `drawMomentum()`:

```javascript
function nearestConfidence(minute) {{
  var points = matchData.win_confidence.filter(function(p) {{ return p.minute <= minute; }});
  if (points.length === 0) return matchData.win_confidence[0];
  return points[points.length - 1];
}}

function renderConfidence() {{
  var point = nearestConfidence(minute);
  var pct = Math.round(point.confidence * 100);
  var leaderName = point.leader === 'home' ? matchData.home.name : point.leader === 'away' ? matchData.away.name : 'Neither side';
  document.getElementById('confidence-wrap').innerHTML =
    '<div class="confidence-label"><span>' + leaderName + ' to win</span><span>' + pct + '%</span></div>' +
    '<div class="confidence-bar"><div class="fill" style="width:' + pct + '%"></div></div>' +
    '<div class="confidence-explanation">' + point.explanation + '</div>';
}}
```

- [ ] **Step 6: Call `renderConfidence()` from `renderState()`**

Find the `renderState()` function and add a call to `renderConfidence();` right after the existing `drawMomentum();` call, so the meter updates every tick alongside the momentum chart.

- [ ] **Step 7: Manually verify**

Run: `python -m streamlit run app/main.py --server.headless true --server.port 8511 &`, then using the chrome-devtools MCP tool: navigate to the app, click the Live Replay tab, confirm the confidence meter shows immediately at load (minute 0, tied 0-0, "Neither side to win", 50%), click Play, let it run past the 19' goal event, confirm the meter updates to show a leader, a percentage above 50%, a bar width matching the percentage, and an explanation sentence naming the correct team. Stop the server afterward.

- [ ] **Step 8: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing, no regressions (this task adds no new Python tests — pure JS UI, consistent with the rest of `replay.py`)

- [ ] **Step 9: Commit**

```bash
git add app/replay.py
git commit -m "Add live win confidence meter to Live Replay tab"
```

---

## Self-Review Notes

**Spec coverage:** Formula (Task 1), `app/main.py` wiring (Task 2), CLAUDE.md scope-rule update (Task 2), UI placement and visuals (Task 3), testing approach (Task 1 unit tests + Task 3 manual browser verification, consistent with how the rest of `replay.py` was verified during the original rewrite) — all covered.

**Type consistency:** `live_win_confidence`'s return shape (`minute`, `leader`, `confidence`, `explanation`) is defined once in Task 1 and consumed identically in Task 3's JS (`point.minute`, `point.leader`, `point.confidence`, `point.explanation`) — no naming drift.

**No placeholders:** every step has complete, real code.
