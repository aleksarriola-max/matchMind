# Match Officiating Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small "Match Officiating Summary" card to the Overview tab, naming the fixture's referee and showing real, computed counts of this match's own VAR reviews/penalties/cautions — not a fabricated cross-match tendency profile.

**Architecture:** `sample_match.json` gets a `referee` field and an explicit `outcome` field on its two existing `var_review` events. A new pure function `analytics.referee_profile(events)` computes the summary directly from those events. A new pure function `components.render_referee_card_html` renders it, following the exact pattern of the existing `render_incident_card_html`. `app/overview.py` wires both in.

**Tech Stack:** Python (`backend/data/sample_match.json`, `backend/engines/analytics.py`), Streamlit (`app/main.py`, `app/overview.py`, `app/components.py`).

## Global Constraints

- No fabricated cross-match referee history — every number in `referee_profile`'s output must be a direct, real count from this match's own events list.
- `overturn_rate` is `None` (not `0`) when there are no VAR-review events to compute a rate from.
- `penalties_awarded` and `cautions_issued` count events by exact `type` match (`"penalty"`, `"card"`) — both will be `0` for the current fixture since neither type exists in its events yet, and that's the honest answer, not a hardcoded stand-in.
- Card placement: Overview tab, between the team cards and the momentum chart.
- Card framing says "this match" explicitly — never implies a cross-match behavioral pattern.

---

### Task 1: `referee` field + event `outcome` fields in `sample_match.json`, `analytics.referee_profile`

**Files:**
- Modify: `backend/data/sample_match.json`
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `analytics.referee_profile(events: list) -> dict`, returning `{"var_reviews_triggered": int, "overturned_count": int, "upheld_count": int, "overturn_rate": float | None, "penalty_appeals": int, "penalties_awarded": int, "cautions_issued": int}`

- [ ] **Step 1: Add the `referee` field to `backend/data/sample_match.json`**

Find the top-level `"score"` line:

```json
  "score": {"home": 2, "away": 1},
```

Add a `referee` field right before it:

```json
  "referee": {"name": "Hugo Martínez"},
  "score": {"home": 2, "away": 1},
```

- [ ] **Step 2: Add `outcome` to the two existing `var_review` events**

Find these two lines in the `events` array:

```json
    {"minute": 27, "type": "var_review", "team": "home", "id": "offside_27", "desc": "Argentina's goal is disallowed after a VAR review for offside."},
    {"minute": 38, "type": "var_review", "team": "away", "id": "handball_38", "desc": "France's penalty appeal for handball is rejected."},
```

Replace with:

```json
    {"minute": 27, "type": "var_review", "team": "home", "id": "offside_27", "outcome": "overturned", "desc": "Argentina's goal is disallowed after a VAR review for offside."},
    {"minute": 38, "type": "var_review", "team": "away", "id": "handball_38", "outcome": "upheld", "desc": "France's penalty appeal for handball is rejected."},
```

- [ ] **Step 3: Write the failing tests**

Append to `tests/test_analytics.py`:

```python
def test_referee_profile_counts_var_reviews_and_overturn_rate():
    events = [
        {"minute": 27, "type": "var_review", "team": "home", "outcome": "overturned", "desc": "x"},
        {"minute": 38, "type": "var_review", "team": "away", "outcome": "upheld", "desc": "y"},
    ]
    profile = analytics.referee_profile(events)
    assert profile["var_reviews_triggered"] == 2
    assert profile["overturned_count"] == 1
    assert profile["upheld_count"] == 1
    assert profile["overturn_rate"] == 0.5


def test_referee_profile_overturn_rate_is_none_without_var_reviews():
    events = [{"minute": 19, "type": "goal", "team": "home", "desc": "x"}]
    profile = analytics.referee_profile(events)
    assert profile["var_reviews_triggered"] == 0
    assert profile["overturn_rate"] is None


def test_referee_profile_counts_penalty_appeals_from_descriptions():
    events = [
        {"minute": 38, "type": "var_review", "team": "away", "outcome": "upheld", "desc": "France's penalty appeal for handball is rejected."},
    ]
    profile = analytics.referee_profile(events)
    assert profile["penalty_appeals"] == 1
    assert profile["penalties_awarded"] == 0


def test_referee_profile_counts_cautions_by_exact_type():
    events = [
        {"minute": 50, "type": "card", "team": "home", "desc": "Yellow card shown."},
        {"minute": 60, "type": "goal", "team": "away", "desc": "Goal scored."},
    ]
    profile = analytics.referee_profile(events)
    assert profile["cautions_issued"] == 1


def test_referee_profile_on_real_fixture_events():
    from backend.engines import explainer
    profile = analytics.referee_profile(explainer.MATCH_DATA["events"])
    assert profile["var_reviews_triggered"] == 2
    assert profile["overturned_count"] == 1
    assert profile["upheld_count"] == 1
    assert profile["overturn_rate"] == 0.5
    assert profile["penalties_awarded"] == 0
    assert profile["cautions_issued"] == 0
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k referee_profile`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'referee_profile'`

- [ ] **Step 5: Implement `referee_profile` in `backend/engines/analytics.py`**

Add at the end of the file:

```python
def referee_profile(events: list) -> dict:
    """
    Single-match officiating summary, computed purely from this match's own
    events -- not a cross-match behavioral tendency (matchMind has no real
    multi-match referee history to compute one from).
    """
    var_reviews = [e for e in events if e["type"] == "var_review"]
    overturned = sum(1 for e in var_reviews if e.get("outcome") == "overturned")
    upheld = sum(1 for e in var_reviews if e.get("outcome") == "upheld")
    return {
        "var_reviews_triggered": len(var_reviews),
        "overturned_count": overturned,
        "upheld_count": upheld,
        "overturn_rate": round(overturned / len(var_reviews), 2) if var_reviews else None,
        "penalty_appeals": sum(1 for e in events if "penalty" in e["desc"].lower()),
        "penalties_awarded": sum(1 for e in events if e["type"] == "penalty"),
        "cautions_issued": sum(1 for e in events if e["type"] == "card"),
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k referee_profile`
Expected: 5 passed

- [ ] **Step 7: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (115 — 110 existing + 5 new)

- [ ] **Step 8: Commit**

```bash
git add backend/data/sample_match.json backend/engines/analytics.py tests/test_analytics.py
git commit -m "Add referee field, var_review outcomes, and referee_profile analytics"
```

---

### Task 2: `components.render_referee_card_html`

**Files:**
- Modify: `app/components.py`
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `render_referee_card_html(referee_name: str, profile: dict) -> str`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_components.py`:

```python
def test_render_referee_card_html_includes_name_and_counts():
    profile = {
        "var_reviews_triggered": 2,
        "overturned_count": 1,
        "upheld_count": 1,
        "overturn_rate": 0.5,
        "penalty_appeals": 1,
        "penalties_awarded": 0,
        "cautions_issued": 0,
    }
    html = components.render_referee_card_html("Hugo Martínez", profile)
    assert "Hugo Martínez" in html
    assert "this match" in html.lower()
    assert "2" in html  # var reviews triggered
    assert "1 overturned" in html
    assert "1 upheld" in html
    assert "0 penalties awarded" in html
    assert "1 appeal" in html
    assert "0 cautions" in html


def test_render_referee_card_html_handles_no_var_reviews():
    profile = {
        "var_reviews_triggered": 0,
        "overturned_count": 0,
        "upheld_count": 0,
        "overturn_rate": None,
        "penalty_appeals": 0,
        "penalties_awarded": 0,
        "cautions_issued": 0,
    }
    html = components.render_referee_card_html("Hugo Martínez", profile)
    assert "0 VAR reviews" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components.py -v -k referee_card`
Expected: FAIL with `AttributeError: module 'app.components' has no attribute 'render_referee_card_html'`

- [ ] **Step 3: Implement `render_referee_card_html` in `app/components.py`**

Add at the end of the file:

```python
def render_referee_card_html(referee_name: str, profile: dict) -> str:
    return (
        '<div class="team-card">'
        f"<h3>Match Officiating</h3>"
        f"<div>{referee_name}</div>"
        f'<div>{profile["var_reviews_triggered"]} VAR reviews this match — '
        f'{profile["overturned_count"]} overturned, {profile["upheld_count"]} upheld</div>'
        f'<div>{profile["penalties_awarded"]} penalties awarded '
        f'({profile["penalty_appeals"]} appeal{"s" if profile["penalty_appeals"] != 1 else ""} reviewed)</div>'
        f'<div>{profile["cautions_issued"]} cautions issued</div>'
        "</div>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v -k referee_card`
Expected: 2 passed

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (117 — 115 + 2 new)

- [ ] **Step 6: Commit**

```bash
git add app/components.py tests/test_components.py
git commit -m "Add render_referee_card_html to app/components.py"
```

---

### Task 3: Wire into `app/main.py` and `app/overview.py`

**Files:**
- Modify: `app/main.py`
- Modify: `app/overview.py`

**Interfaces:**
- Consumes: `analytics.referee_profile(events) -> dict` (Task 1), `components.render_referee_card_html(referee_name, profile) -> str` (Task 2)
- Produces: `match_data["referee"]` — available to `app/overview.py`

- [ ] **Step 1: Add `referee` to `match_data` in `app/main.py`**

Find:

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

Add `"referee": explainer.MATCH_DATA["referee"],` after the `"score"` line:

```python
match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "referee": explainer.MATCH_DATA["referee"],
    "events": explainer.MATCH_DATA["events"],
    "momentum": analytics.momentum_curve(
        explainer.MATCH_DATA["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    ),
}
```

- [ ] **Step 2: Add the officiating card to `app/overview.py`**

Current file:

```python
import streamlit as st

from app import components


def render_overview(match_data: dict) -> None:
    st.markdown(components.render_header_html(match_data), unsafe_allow_html=True)

    cards_html = '<div class="team-cards">'
    for team in (match_data["home"], match_data["away"]):
        cards_html += (
            f'<div class="team-card"><h3><span class="swatch" style="background:{team["color"]}"></span>'
            f'{team["name"]}</h3><div>{team["formation_start"]} → {team["formation_end"]}</div></div>'
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown(
        components.render_momentum_chart_html("<h3>Momentum</h3>", match_data),
        unsafe_allow_html=True,
    )

    st.markdown("## Match events")
    rows = "".join(components.render_event_row_html(e) for e in match_data["events"])
    st.markdown(f'<ul class="event-list">{rows}</ul>', unsafe_allow_html=True)
```

Replace with:

```python
import streamlit as st

from app import components
from backend.engines import analytics


def render_overview(match_data: dict) -> None:
    st.markdown(components.render_header_html(match_data), unsafe_allow_html=True)

    cards_html = '<div class="team-cards">'
    for team in (match_data["home"], match_data["away"]):
        cards_html += (
            f'<div class="team-card"><h3><span class="swatch" style="background:{team["color"]}"></span>'
            f'{team["name"]}</h3><div>{team["formation_start"]} → {team["formation_end"]}</div></div>'
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    profile = analytics.referee_profile(match_data["events"])
    st.markdown(
        components.render_referee_card_html(match_data["referee"]["name"], profile),
        unsafe_allow_html=True,
    )

    st.markdown(
        components.render_momentum_chart_html("<h3>Momentum</h3>", match_data),
        unsafe_allow_html=True,
    )

    st.markdown("## Match events")
    rows = "".join(components.render_event_row_html(e) for e in match_data["events"])
    st.markdown(f'<ul class="event-list">{rows}</ul>', unsafe_allow_html=True)
```

- [ ] **Step 3: Verify the app boots**

Run: `python -m streamlit run app/main.py --server.headless true --server.port 8530 &`, then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8530 --max-time 10`
Expected: `200`. Stop the server afterward.

- [ ] **Step 4: Manually verify with a live browser check**

Using the chrome-devtools MCP tool: navigate to the app, confirm the Overview tab shows a "Match Officiating" card between the team cards and the momentum chart, naming "Hugo Martínez," showing "2 VAR reviews this match — 1 overturned, 1 upheld," "0 penalties awarded (1 appeal reviewed)," and "0 cautions issued."

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (117), no regressions

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/overview.py
git commit -m "Wire Match Officiating Summary card into Overview tab"
```

---

## Self-Review Notes

**Spec coverage:** `referee` field + event `outcome` fields (Task 1, Steps 1-2), `referee_profile` (Task 1, Steps 3-7), `render_referee_card_html` (Task 2), Overview-tab placement between team cards and momentum chart (Task 3, Step 2) — all covered. The spec's "no fabricated cross-match history" constraint is enforced by `referee_profile` only ever reading the real `events` list.

**No placeholders:** every step has complete, real code.

**Type consistency:** `referee_profile`'s return dict keys (`var_reviews_triggered`, `overturned_count`, `upheld_count`, `overturn_rate`, `penalty_appeals`, `penalties_awarded`, `cautions_issued`) are defined once in Task 1 and consumed with the exact same keys in Task 2's `render_referee_card_html` and Task 3's wiring — no naming drift.
