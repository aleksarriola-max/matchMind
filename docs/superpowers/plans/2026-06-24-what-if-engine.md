# What-If Scenario Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an 8th "What If" tab letting users toggle 3 real, score-independent match events off and see the existing momentum formula recompute live with that event excluded.

**Architecture:** A single new `app/what_if.py` tab module. No new backend analytics function and no new component builder — it reuses `analytics.momentum_curve`, `analytics.momentum_summary`, and `components.render_momentum_chart_html` exactly as they already exist, just feeding them a filtered copy of `match_data["events"]`.

**Tech Stack:** Streamlit (`app/main.py`, new `app/what_if.py`), existing `backend/engines/analytics.py` and `app/components.py` functions (unmodified).

## Global Constraints

- Toggleable events are exactly these 3 (by `id`): `halftime_shift` (46'), `sub_58` (58'), `fatigue_71` (71'). The two `var_review` events (`offside_27`, `handball_38`) are explicitly NOT toggleable in this pass — they affect the score, which this feature does not recompute.
- No new backend function. No new `app/components.py` function. This task only creates `app/what_if.py` and modifies `app/main.py`.
- New tab placed 8th, after "Tactical DNA".
- The UI must include the honesty callout distinguishing "what the momentum model would score" from "a prediction of what actually would have happened on the pitch."

---

### Task 1: `app/what_if.py` tab + wire into `app/main.py`

**Files:**
- Create: `app/what_if.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `analytics.momentum_curve(events, weights) -> list` (existing), `analytics.momentum_summary(curve) -> dict` (existing), `components.render_momentum_chart_html(title_html, match_data, current_minute=None) -> str` (existing)
- Produces: `render_what_if(match_data: dict) -> None`

- [ ] **Step 1: Create `app/what_if.py`**

```python
import streamlit as st

from app import components
from backend.engines import analytics

TOGGLEABLE_EVENT_IDS = ["halftime_shift", "sub_58", "fatigue_71"]


def render_what_if(match_data: dict) -> None:
    st.markdown("## What If")
    st.write(
        "Toggle a real event off and see how the momentum model would have "
        "scored the match without it — not a prediction of what actually "
        "would have happened on the pitch, just the same formula re-run on "
        "a different event list."
    )

    toggleable_events = [e for e in match_data["events"] if e.get("id") in TOGGLEABLE_EVENT_IDS]
    removed_ids = set()
    for event in toggleable_events:
        keep = st.checkbox(f"{event['minute']}' — {event['desc']}", value=True, key=f"whatif_{event['id']}")
        if not keep:
            removed_ids.add(event["id"])

    weights = analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    actual_curve = match_data["momentum"]
    what_if_events = [e for e in match_data["events"] if e.get("id") not in removed_ids]
    what_if_curve = analytics.momentum_curve(what_if_events, weights)

    actual_match_data = {**match_data, "momentum": actual_curve}
    what_if_match_data = {**match_data, "momentum": what_if_curve}

    st.markdown(
        components.render_momentum_chart_html("<h3>Actual</h3>", actual_match_data),
        unsafe_allow_html=True,
    )
    st.markdown(
        components.render_momentum_chart_html("<h3>What If</h3>", what_if_match_data),
        unsafe_allow_html=True,
    )

    if removed_ids:
        actual_summary = analytics.momentum_summary(actual_curve)
        what_if_summary = analytics.momentum_summary(what_if_curve)
        removed_descs = [e["desc"] for e in toggleable_events if e["id"] in removed_ids]
        st.write(
            f"Without {' and '.join(removed_descs)}: final momentum would be "
            f"{what_if_summary['final_value']} (actual: {actual_summary['final_value']}), "
            f"{what_if_summary['dominant_team']} "
            f"{'still' if what_if_summary['dominant_team'] == actual_summary['dominant_team'] else 'now'} dominant."
        )
    else:
        st.write("No events removed — the What If curve matches the actual match.")
```

- [ ] **Step 2: Wire into `app/main.py`**

Current file:

```python
import streamlit as st

from app import ask, debate, history, moments, overview, replay, styles, tactical_dna
from backend.engines import analytics, explainer

st.set_page_config(page_title="MatchMind", layout="centered")
styles.inject()

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
match_data["win_confidence"] = analytics.live_win_confidence(
    match_data["events"], match_data["momentum"], match_data["home"]["name"], match_data["away"]["name"],
)

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA"]
)

with tab_overview:
    overview.render_overview(match_data)

with tab_moments:
    moments.render_moments(match_data)

with tab_ask:
    ask.render_ask()

with tab_debate:
    debate.render_debate()

with tab_history:
    history.render_history()

with tab_replay:
    replay.render_replay(match_data)

with tab_tactical_dna:
    tactical_dna.render_tactical_dna(match_data)
```

Replace with:

```python
import streamlit as st

from app import ask, debate, history, moments, overview, replay, styles, tactical_dna, what_if
from backend.engines import analytics, explainer

st.set_page_config(page_title="MatchMind", layout="centered")
styles.inject()

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
match_data["win_confidence"] = analytics.live_win_confidence(
    match_data["events"], match_data["momentum"], match_data["home"]["name"], match_data["away"]["name"],
)

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna, tab_what_if = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA", "What If"]
)

with tab_overview:
    overview.render_overview(match_data)

with tab_moments:
    moments.render_moments(match_data)

with tab_ask:
    ask.render_ask()

with tab_debate:
    debate.render_debate()

with tab_history:
    history.render_history()

with tab_replay:
    replay.render_replay(match_data)

with tab_tactical_dna:
    tactical_dna.render_tactical_dna(match_data)

with tab_what_if:
    what_if.render_what_if(match_data)
```

- [ ] **Step 3: Verify the app boots**

Run: `python -m streamlit run app/main.py --server.headless true --server.port 8570 &`, then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8570 --max-time 10`
Expected: `200`. Stop the server afterward.

- [ ] **Step 4: Manually verify all 3 toggles with a live browser check**

Using the chrome-devtools MCP tool: navigate to the app, click the "What If" tab (8th tab, after "Tactical DNA"), confirm two momentum charts render ("Actual" and "What If", identical at first since all 3 checkboxes default to checked/kept) plus the "no events removed" message. Then:
- Uncheck the 46' tactical-shift checkbox — confirm the "What If" chart visibly changes shape from "Actual" and the summary sentence updates with real numbers (expect final momentum around 39.8 vs actual 41.0, based on the real fixture's telemetry — confirm the actual displayed numbers, don't just assume these match exactly).
- Re-check it, then uncheck the 58' substitution checkbox instead — confirm the chart and summary update again with a different real number.
- Re-check it, then uncheck the 71' fatigue-collapse checkbox — confirm the chart and summary update with yet another different real number.

Take a screenshot of at least one toggled state as evidence.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (122), no regressions — this task adds no new Python tests since it introduces no new backend/component logic, only orchestration reusing already-tested functions.

- [ ] **Step 6: Commit**

```bash
git add app/what_if.py app/main.py
git commit -m "Add What-If Scenario Engine tab"
```

---

## Self-Review Notes

**Spec coverage:** The 3 toggleable events with their exact IDs (Global Constraints), the reuse-only architecture (no new backend/component code), the honesty callout text, and the 8th-tab placement are all covered in this single task. The spec's "no new analytics tests needed" and "no automated tests for the tab module itself" testing approach is reflected in Step 5 (full suite, no new tests) and Step 4 (live browser verification instead).

**No placeholders:** the task has complete, real code for both the new file and the `app/main.py` before/after diff.

**Type consistency:** `TOGGLEABLE_EVENT_IDS` matches the exact `id` values used in `backend/data/sample_match.json`'s events (`halftime_shift`, `sub_58`, `fatigue_71`) — verified against the real fixture file, not assumed.
