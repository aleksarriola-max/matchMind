import streamlit as st

from app import ask, debate, history, moments, overview, replay, styles
from backend.engines import analytics, explainer

st.set_page_config(page_title="MatchMind", layout="centered")
styles.inject()

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

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay"]
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
