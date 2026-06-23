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
