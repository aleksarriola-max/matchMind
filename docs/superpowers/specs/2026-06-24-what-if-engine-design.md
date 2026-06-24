# What-If Scenario Engine — Design

**Goal:** Let users toggle off one of this match's real events and see the
momentum model recompute live — using the SAME existing
`analytics.momentum_curve`/`momentum_summary` functions with a filtered
event list, not a new simulation engine and not an LLM-generated narrative.

**Why this scope, not free-text questions:** The original pitch ("ask any
what-if question") would require generating speculative prose about events
that never happened — there's no real evidence to verify that against,
which conflicts with this app's verifier-everything ethos. Toggling real
events and recomputing a real, already-tested formula keeps every number
honest: it's not a claim about what would have actually happened on the
pitch, it's an honest "here's what the momentum model would have scored
without this event."

**Toggleable events (3, deliberately excludes the two VAR-review events):**
`halftime_shift` (46', tactical), `sub_58` (58', substitution), `fatigue_71`
(71', pressure). These three only affect momentum, not the score — toggling
them off requires no score/win-confidence cascading. The two `var_review`
events are out of scope for this pass: removing one would mean the
original on-field call stands, which changes the score and would need to
cascade into `live_win_confidence` and the Match Officiating card — a
larger, separate piece of work if picked up later.

## 1. `app/what_if.py` — new tab module

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
            f"{what_if_summary['dominant_team']} {'still' if what_if_summary['dominant_team'] == actual_summary['dominant_team'] else 'now'} dominant."
        )
    else:
        st.write("No events removed — the What If curve matches the actual match.")
```

No new backend function. `momentum_curve` and `momentum_summary` are called
exactly as they already are elsewhere in the app (e.g. `app/main.py`'s
`match_data["momentum"]` computation) — just with a filtered `events` list
as input. `render_momentum_chart_html` is called twice with two small
dict literals that share every key with `match_data` except `momentum`
(Python's `{**match_data, "momentum": ...}` spread, not a new data shape).

## 2. `app/main.py`

Wired as an 8th tab, "What If," after "Tactical DNA":

```python
from app import ask, debate, history, moments, overview, replay, styles, tactical_dna, what_if
```

```python
tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna, tab_what_if = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA", "What If"]
)
```

```python
with tab_what_if:
    what_if.render_what_if(match_data)
```

## 3. Testing

No new analytics tests — `momentum_curve` and `momentum_summary` are
already tested. No automated tests for `app/what_if.py` itself (pure
Streamlit orchestration, consistent with every other tab module's
testing approach in this app) — verified manually via a live browser
check: toggle each of the 3 events off individually, confirm the "What
If" chart visibly differs from "Actual" and the summary sentence updates
with real, correctly-computed numbers (not just that the page doesn't
error).

## Out of scope

- The two `var_review` events (deliberately deferred — see above).
- Any free-text question input.
- Any new backend analytics function — this reuses `momentum_curve` and
  `momentum_summary` exactly as they exist today.
- Toggling combinations beyond independent checkboxes (no "what if X but
  not Y" preset scenarios — each event is just an independent on/off).
