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
