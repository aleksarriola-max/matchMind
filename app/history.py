import streamlit as st

from app import components
from backend.engines import consistency

TOPICS = ["offside", "handball", "goal-line", "penalty"]
TOPIC_LABELS = {"offside": "🚩 offside", "handball": "✅ handball", "goal-line": "📏 goal-line", "penalty": "⚖️ penalty"}


def render_history() -> None:
    st.markdown("## Decision Consistency Analyzer")
    st.write("Compare today's call with real World Cup history.")

    topic = st.radio("Topic", TOPICS, format_func=lambda t: TOPIC_LABELS[t], key="history_topic")
    data = consistency.compare(topic)

    if data["today"]:
        st.markdown(
            f'<div class="confidence-card">'
            f'{components.render_glow_bar_html("Today\'s call confidence", data["today"]["confidence"], "var(--accent)")}'
            f'<div style="margin-top:6px;">Today\'s call: {data["today"]["decision"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.write(f"This match has no {topic} review to compare against — here's the history.")

    for incident in data["historical_incidents"]:
        st.markdown(components.render_incident_card_html(incident), unsafe_allow_html=True)
