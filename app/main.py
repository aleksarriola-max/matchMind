import streamlit as st

from app import styles
from backend.engines import explainer

st.set_page_config(page_title="MatchMind", layout="centered")
styles.inject()

match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "events": explainer.MATCH_DATA["events"],
}

st.write(f"## {match_data['home']['name']} {match_data['score']['home']} – {match_data['score']['away']} {match_data['away']['name']}")

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay"]
)

with tab_overview:
    st.write("Overview — coming in Task 4")

with tab_moments:
    st.write("Moments — coming in Task 6")

with tab_ask:
    st.write("Ask MatchMind — coming in Task 7")

with tab_debate:
    st.write("Debate — coming in Task 8")

with tab_history:
    st.write("History — coming in Task 9")

with tab_replay:
    st.write("Live Replay — coming in Task 10")
