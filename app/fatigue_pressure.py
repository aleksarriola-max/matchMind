import streamlit as st

from app import components
from backend.engines import analytics


def render_fatigue_pressure(match_data: dict) -> None:
    st.markdown("## Fatigue & Pressure")
    st.write(
        "One zone per team, not per player — matchMind's data is team-level "
        "aggregate telemetry, not individual player tracking. Zone size "
        "reflects how stretched each team's defensive shape is (the real gap "
        "between their defensive line and midfield); zone color reflects "
        "their real computed fatigue index."
    )

    home_telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    away_telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    zones = analytics.fatigue_pressure_zones(home_telemetry, away_telemetry)

    window_label = st.select_slider("Match window", options=zones["windows"])
    window_index = zones["windows"].index(window_label)

    svg = components.render_fatigue_zone_pitch_html(
        match_data["home"]["name"],
        match_data["away"]["name"],
        match_data["home"]["color"],
        match_data["away"]["color"],
        zones["home"]["fatigue_index"][window_index],
        zones["home"]["spread"][window_index],
        zones["away"]["fatigue_index"][window_index],
        zones["away"]["spread"][window_index],
    )
    st.markdown(f'<div class="pitch-wrap">{svg}</div>', unsafe_allow_html=True)

    st.markdown("### Real numbers behind the zones")
    st.write(
        f"**{match_data['home']['name']}**: fatigue index "
        f"{zones['home']['fatigue_index'][window_index]}, line gap "
        f"{home_telemetry['line_gap_def_mid_m'][window_index]}m"
    )
    st.write(
        f"**{match_data['away']['name']}**: fatigue index "
        f"{zones['away']['fatigue_index'][window_index]}, line gap "
        f"{away_telemetry['line_gap_def_mid_m'][window_index]}m"
    )
