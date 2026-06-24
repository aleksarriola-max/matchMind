import streamlit as st

from app import components
from backend.engines import analytics

AXIS_LABELS = {
    "pressing_intensity": "Pressing Intensity (inverse of PPDA)",
    "directness": "Directness (long-pass share)",
    "defensive_compactness": "Defensive Compactness (inverse of line gap)",
    "transition_speed": "Transition Speed (sprints — a proxy, not a literal measurement)",
}


def render_tactical_dna(match_data: dict) -> None:
    st.markdown("## Tactical DNA")
    st.write(
        "Each team's playing-style fingerprint, computed from real per-window "
        "telemetry — not a fabricated cross-match benchmark."
    )

    home_telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    away_telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    dna = analytics.tactical_dna(home_telemetry, away_telemetry)

    svg = components.render_tactical_dna_radar_html(
        match_data["home"]["name"],
        match_data["away"]["name"],
        dna["home"],
        dna["away"],
        match_data["home"]["color"],
        match_data["away"]["color"],
    )
    st.markdown(f'<div class="momentum-chart-wrap">{svg}</div>', unsafe_allow_html=True)

    st.markdown("### Real numbers behind the chart")
    for axis, raw in dna["raw_inputs"].items():
        st.write(f"**{AXIS_LABELS[axis]}**: {match_data['home']['name']} {raw['home']} vs {match_data['away']['name']} {raw['away']}")
