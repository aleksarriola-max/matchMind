import streamlit as st

from app import components
from backend.engines import analytics, explainer, real_incident

MOMENT_ORDER = [
    "offside_27", "handball_38", "halftime_shift", "sub_58",
    "goal_home_1", "fatigue_71", "goal_home_2",
]
MOMENT_LABELS = {
    "offside_27": "27' Offside review",
    "handball_38": "38' Handball review",
    "halftime_shift": "46' Tactical shift",
    "sub_58": "58' Substitution",
    "goal_home_1": "63' Goal",
    "fatigue_71": "71' Pressing collapse",
    "goal_home_2": "84' Goal",
}


def _moment_analytics(moment_id: str, moment: dict) -> dict | None:
    if moment_id == "offside_27":
        return {
            "offside_probability": analytics.offside_probability(
                moment["margin_cm"], moment["camera_frame_uncertainty_cm"]
            ),
            "offside_sensitivity": analytics.offside_sensitivity(
                moment["margin_cm"], moment["camera_frame_uncertainty_cm"]
            ),
            "counterfactual_timing": analytics.counterfactual_timing(
                moment["margin_cm"], moment["attacker_speed_ms"]
            ),
        }
    if moment_id == "handball_38":
        return {
            "handball_reaction": analytics.handball_reaction(
                moment["deflection_distance_m"], moment["ball_speed_ms"]
            ),
        }
    if moment_id == "fatigue_71":
        telemetry = analytics.TELEMETRY_DATA
        return {
            "fatigue_index": {
                "home": analytics.fatigue_index(telemetry["teams"]["home"])["result"],
                "away": analytics.fatigue_index(telemetry["teams"]["away"])["result"],
            },
            "fatigue_comparison": analytics.fatigue_comparison(
                telemetry["teams"]["home"], telemetry["teams"]["away"]
            )["result"],
        }
    return None


def _render_text_moment(moment: dict, match_data: dict) -> None:
    st.markdown(f"## {moment['title']}")
    if moment.get("law"):
        st.markdown(f'<div class="law-badge">{moment["law"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="decision">{moment["decision"]}</p>', unsafe_allow_html=True)
    st.markdown(components.render_glow_bar_html("Confidence", moment["confidence"], "var(--accent)"), unsafe_allow_html=True)
    st.write(moment["summary"])
    st.markdown("### Evidence")
    for e in moment["evidence"]:
        st.markdown(f"- {e}")

    a = moment.get("analytics")
    if a and a.get("handball_reaction"):
        r = a["handball_reaction"]["result"]
        benchmark = a["handball_reaction"]["inputs"]["reaction_benchmark_ms"]
        st.markdown("### Computed analytics")
        st.write(
            f"Ball reaches the point of contact in {r['time_available_ms']}ms — "
            f"{r['deficit_ratio']}x faster than the {benchmark}ms human reaction benchmark ({r['verdict']})."
        )
    if a and a.get("fatigue_index"):
        home, away = a["fatigue_index"]["home"], a["fatigue_index"]["away"]
        cmp = a["fatigue_comparison"]
        st.markdown("### Computed analytics")
        st.table(
            {
                "Team": [match_data["home"]["name"], match_data["away"]["name"]],
                "Trend": [home["trend"], away["trend"]],
                "Peak window": [home["peak_window"], away["peak_window"]],
            }
        )
        st.write(f"More fatigued by full-time: {cmp['more_fatigued_team']} (diff {cmp['difference'][5]} pts)")


def _render_real_incident(match_data: dict) -> None:
    if "real_incident_data" not in st.session_state:
        if st.button("\U0001F30D Show a real incident: 2022 World Cup Final"):
            try:
                st.session_state["real_incident_data"] = real_incident.get_real_incident()
            except Exception:
                st.error("Could not load real incident data — StatsBomb's open-data repo may be unreachable.")
        return

    data = st.session_state["real_incident_data"]
    st.markdown(
        f'<div class="incident-meta">{data["match"]["competition"]} — '
        f'{data["match"]["home_team"]} vs {data["match"]["away_team"]}, {data["match"]["date"]}</div>',
        unsafe_allow_html=True,
    )
    st.write(f"{data['minute']}' — {data['passer']} → {data['recipient']} (offside, real StatsBomb data)")

    scale_x, scale_y = 100 / 120, 68 / 80
    mb, defn = data["mbappe_position"], data["second_last_opponent_position"]
    svg = '<svg viewBox="-2 -2 104 72" class="pitch-svg"><rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>'
    svg += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.7"><rect x="0" y="0" width="100" height="68"/>'
    svg += '<line x1="50" y1="0" x2="50" y2="68"/><circle cx="50" cy="34" r="8.7"/></g>'
    for p in data["freeze_frame"]:
        color = match_data["away"]["color"] if p["teammate"] else match_data["home"]["color"]
        svg += f'<circle cx="{p["location"][0] * scale_x}" cy="{p["location"][1] * scale_y}" r="1.3" fill="{color}" stroke="#fff" stroke-width="0.2" opacity="0.7"/>'
    svg += f'<line x1="{defn[0] * scale_x}" y1="-2" x2="{defn[0] * scale_x}" y2="70" stroke="#00e0ff" stroke-width="0.4" opacity="0.6"/>'
    svg += components.player_circle_html(mb[0] * scale_x, mb[1] * scale_y, "M", match_data["away"]["color"], "#ff4d4d", 0.4)
    svg += components.player_circle_html(defn[0] * scale_x, defn[1] * scale_y, "D", match_data["home"]["color"], "#ffffff", 0.25)
    svg += "</svg>"

    st.markdown(f'<div class="pitch-wrap">{svg}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="confidence-line">Real measured margin: {data["margin_cm"]:.1f} cm</p>', unsafe_allow_html=True)
    st.markdown(
        '<div class="callout">Illustrative — applies our uncertainty model to real position data. '
        "StatsBomb does not publish camera/tracking error margins, so this is not an official measurement.</div>",
        unsafe_allow_html=True,
    )
    for note in data["approximation_notes"]:
        st.markdown(f"- {note}")
    st.markdown(
        f'<p class="lineage">Data: <a href="{data["source_url"]}" target="_blank" rel="noopener">'
        "StatsBomb — Data Champions.</a> (Open Data, used under their research/analysis license)</p>",
        unsafe_allow_html=True,
    )


def render_moments(match_data: dict) -> None:
    moments = explainer.MATCH_DATA["moments"]
    selected = st.radio(
        "Select a moment",
        MOMENT_ORDER,
        format_func=lambda mid: MOMENT_LABELS[mid],
        key="selected_moment",
    )

    moment = dict(moments[selected])
    moment["analytics"] = _moment_analytics(selected, moments[selected])

    if moment.get("pitch"):
        show_sightline = st.checkbox("Referee sightline", key="show_sightline")
        show_uncertainty_band = st.checkbox("Uncertainty band", value=True, key="show_uncertainty_band")
        st.markdown(
            components.render_decision_lab_pitch_html(moment, match_data, show_sightline, show_uncertainty_band),
            unsafe_allow_html=True,
        )
        if moment.get("counterfactual"):
            frames = moment["analytics"]["counterfactual_timing"]["result"]["frames_at_50fps"]
            st.markdown(
                f'<div class="callout">{moment["counterfactual"]} ({frames} frames at 50fps — not detectable on broadcast)</div>',
                unsafe_allow_html=True,
            )
        if moment.get("debate"):
            st.markdown(
                '<div class="debate-cols">'
                f'<div><h4>Stands</h4><p>{moment["debate"]["stands"]}</p></div>'
                f'<div><h4>Overturn</h4><p>{moment["debate"]["overturn"]}</p></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="real-incident-wrap"></div>', unsafe_allow_html=True)
        _render_real_incident(match_data)
    else:
        _render_text_moment(moment, match_data)
