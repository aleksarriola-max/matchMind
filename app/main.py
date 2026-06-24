import sys
from pathlib import Path

import streamlit as st

# Streamlit invokes this file as a standalone script, so the interpreter
# only puts this file's own directory (app/) on sys.path by default --
# the repo root must be added explicitly for "from app import ..." and
# "from backend... import ..." below to resolve regardless of how/from
# where this script is launched.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ask, debate, fatigue_pressure, history, moments, overview, replay, styles, tactical_dna, what_if
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

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna, tab_what_if, tab_fatigue_pressure = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA", "What If", "Fatigue & Pressure"]
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

with tab_fatigue_pressure:
    fatigue_pressure.render_fatigue_pressure(match_data)
