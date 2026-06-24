import math

EVENT_ICONS = {
    "goal": "⚽",
    "var_review": "🚩",
    "tactical": "🔄",
    "substitution": "🔁",
    "pressure": "😓",
}

TOPIC_ICONS = {
    "offside": "🚩",
    "handball": "✋",
    "goal-line": "📏",
    "penalty": "⚖️",
}

TEAM_FLAGS = {
    "Argentina": (
        '<svg width="20" height="14" viewBox="0 0 30 20" class="flag">'
        '<rect width="30" height="20" fill="#75AADB"/>'
        '<rect y="6.67" width="30" height="6.67" fill="#fff"/></svg>'
    ),
    "France": (
        '<svg width="20" height="14" viewBox="0 0 30 20" class="flag">'
        '<rect width="10" height="20" fill="#0055A4"/>'
        '<rect x="10" width="10" height="20" fill="#fff"/>'
        '<rect x="20" width="10" height="20" fill="#EF4135"/></svg>'
    ),
}


def escape_attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;")


def render_header_html(match_data: dict) -> str:
    home, away, score = match_data["home"], match_data["away"], match_data["score"]
    return (
        '<div class="brand">'
        '<div class="crest"><svg width="20" height="20" viewBox="0 0 20 20">'
        '<circle cx="10" cy="10" r="3" fill="currentColor"/>'
        '<path d="M10 1 L10 5 M10 15 L10 19 M1 10 L5 10 M15 10 L19 10" stroke="currentColor" stroke-width="1.5"/>'
        '</svg></div><span class="wordmark">MatchMind</span></div>'
        f'<p style="color:var(--muted);font-size:0.9em;margin:0 0 4px;">{match_data["competition"]}</p>'
        f'<div class="score-bar" style="background:linear-gradient(90deg, {home["color"]}, {away["color"]})">'
        f'<span class="team-name home">{TEAM_FLAGS.get(home["name"], "")}{home["name"]}</span>'
        f'<span class="score">{score["home"]} – {score["away"]}</span>'
        f'<span class="team-name away">{away["name"]}{TEAM_FLAGS.get(away["name"], "")}</span>'
        "</div>"
    )


def render_event_row_html(event: dict) -> str:
    icon = EVENT_ICONS.get(event["type"], "•")
    return (
        '<li class="event-row">'
        f'<span class="icon">{icon}</span>'
        f'<span class="minute">{event["minute"]}\'</span>'
        f'<span class="event-badge event-badge-{event["type"]}">{event["type"]}</span>'
        f'<span>{event["desc"]}</span></li>'
    )


def render_glow_bar_html(label: str, pct: float, color: str) -> str:
    pct_display = pct * 100
    return (
        f'<div class="glow-bar-label"><span>{label}</span>'
        f'<span style="color:{color};font-weight:700;">{pct_display:.1f}%</span></div>'
        f'<div class="glow-bar"><div class="fill" '
        f'style="width:{pct_display}%;background:{color};color:{color}"></div></div>'
    )


def speak_button_html(text: str) -> str:
    safe_attr = escape_attr(text)
    return (
        "<html><body style=\"margin:0;background:transparent;\">"
        f'<button id="speak-btn" data-text="{safe_attr}" '
        'style="background:none;border:1px solid #2a2a2a;border-radius:4px;color:#00e0ff;'
        'cursor:pointer;padding:2px 8px;font-size:0.9em;">\U0001F50A</button>'
        "<script>"
        "var btn = document.getElementById('speak-btn');"
        "btn.addEventListener('click', function() {"
        "  if (!('speechSynthesis' in window)) return;"
        "  if (window.speechSynthesis.speaking) { window.speechSynthesis.cancel(); return; }"
        "  var u = new SpeechSynthesisUtterance(btn.dataset.text);"
        "  window.speechSynthesis.speak(u);"
        "});"
        "</script></body></html>"
    )


def lighten_for_fill(hex_color: str) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    mix = lambda c: round(c + (255 - c) * 0.45)
    return f"rgb({mix(r)},{mix(g)},{mix(b)})"


def render_momentum_chart_html(title_html: str, match_data: dict, current_minute: int | None = None) -> str:
    curve = match_data["momentum"]
    max_abs = max(1.0, max(abs(p["value"]) for p in curve))
    width, height, margin_x, baseline_y, half_height = 380, 130, 10, 65, 50
    clipped = current_minute is not None
    visible = [p for p in curve if not clipped or p["minute"] <= current_minute] if clipped else curve

    def x_pos(minute):
        return margin_x + (minute / 90) * (width - 2 * margin_x)

    def y_pos(value):
        return baseline_y - (value / max_abs) * half_height

    points = " ".join(f"{x_pos(p['minute'])},{y_pos(p['value'])}" for p in visible)

    home_color, away_color = match_data["home"]["color"], match_data["away"]["color"]

    area_path = ""
    if len(visible) > 1:
        first_x, last_x = x_pos(visible[0]["minute"]), x_pos(visible[-1]["minute"])
        mid = " L ".join(f"{x_pos(p['minute'])},{y_pos(p['value'])}" for p in visible)
        area_path = f"M {first_x},{baseline_y} L {mid} L {last_x},{baseline_y} Z"

    now_marker = ""
    if clipped and visible:
        last = visible[-1]
        now_marker = (
            f'<circle cx="{x_pos(last["minute"])}" cy="{y_pos(last["value"])}" r="4" fill="#fff" '
            f'class="pulse"/>'
        )

    clip_above = (
        f'<clipPath id="clip-above"><rect x="0" y="0" width="{width}" height="{baseline_y}"/></clipPath>'
    )
    clip_below = (
        f'<clipPath id="clip-below"><rect x="0" y="{baseline_y}" width="{width}" '
        f'height="{height - baseline_y}"/></clipPath>'
    )

    area_above = (
        f'<path d="{area_path}" fill="{lighten_for_fill(home_color)}" opacity="0.35" clip-path="url(#clip-above)"/>'
        if area_path else ""
    )
    area_below = (
        f'<path d="{area_path}" fill="{lighten_for_fill(away_color)}" opacity="0.35" clip-path="url(#clip-below)"/>'
        if area_path else ""
    )

    return (
        f'<div class="momentum-chart-wrap">{title_html}'
        f'<svg viewBox="0 0 {width} {height}" class="momentum-chart-svg">'
        f"<defs>{clip_above}{clip_below}</defs>"
        f"{area_above}{area_below}"
        f'<line x1="{margin_x}" y1="{baseline_y}" x2="{width - margin_x}" y2="{baseline_y}" '
        'stroke="#333" stroke-width="1" stroke-dasharray="3,3"/>'
        f'<polyline points="{points}" fill="none" stroke="{home_color}" stroke-width="2.5"/>'
        f"{now_marker}"
        f'<text x="{margin_x}" y="{height - 4}" class="axis-label">0\'</text>'
        f'<text x="{width - margin_x}" y="{height - 4}" class="axis-label" text-anchor="end">90\'</text>'
        "</svg></div>"
    )


def player_circle_html(x: float, y: float, label: str, fill_color: str, stroke_color: str, stroke_width: float) -> str:
    number = label.split("#")[1] if "#" in label else label
    return (
        f'<circle cx="{x}" cy="{y}" r="1.6" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>'
        f'<text x="{x}" y="{y + 0.7}" fill="#fff" font-size="1.8" text-anchor="middle">{number}</text>'
    )


def render_decision_lab_pitch_html(
    moment: dict, match_data: dict, show_sightline: bool, show_uncertainty_band: bool
) -> str:
    p = moment["pitch"]
    home_color, away_color = match_data["home"]["color"], match_data["away"]["color"]
    line_x = p["offside_line_x"]

    html = (
        f'<div class="law-badge">{moment["law"]}</div>' if moment.get("law") else ""
    )
    html += f'<p class="decision">{moment["decision"]}</p>'

    html += (
        '<div class="lab-banner">'
        f'<div class="crest" style="background:{home_color}">{match_data["home"]["name"][0]}</div>'
        '<span class="var-label"><span class="pulse-dot"></span>VAR Review</span>'
        f'<div class="crest" style="background:{away_color}">{match_data["away"]["name"][0]}</div>'
        "</div>"
    )

    html += '<div class="pitch-wrap"><svg viewBox="-2 -2 104 72" class="pitch-svg">'
    html += '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>'
    html += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">'
    html += '<rect x="0" y="0" width="100" height="68"/><line x1="50" y1="0" x2="50" y2="68"/>'
    html += '<circle cx="50" cy="34" r="8.7"/><circle cx="50" cy="34" r="0.5" fill="#eaf5ee"/>'
    html += '<rect x="84.3" y="13.8" width="15.7" height="40.3"/><rect x="94.8" y="24.8" width="5.2" height="18.3"/>'
    html += '<rect x="0" y="13.8" width="15.7" height="40.3"/><rect x="0" y="24.8" width="5.2" height="18.3"/>'
    html += "</g>"

    html += f'<line x1="{line_x}" y1="-2" x2="{line_x}" y2="70" stroke="#00e0ff" stroke-width="0.5"/>'
    html += f'<line x1="{line_x}" y1="-2" x2="{line_x}" y2="70" stroke="#00e0ff" stroke-width="1.6" opacity="0.25"/>'

    if show_sightline:
        ar = p["assistant_referee"]
        html += (
            f'<line x1="{ar["x"]}" y1="{ar["y"] + 0.5}" x2="{p["attacker"]["x"]}" y2="{p["attacker"]["y"]}" '
            'stroke="#ffe14d" stroke-width="0.25" stroke-dasharray="0.8,0.6" opacity="0.85"/>'
        )
        html += (
            f'<line x1="{ar["x"]}" y1="{ar["y"] + 0.5}" x2="{p["second_last_defender"]["x"]}" '
            f'y2="{p["second_last_defender"]["y"]}" stroke="#ffe14d" stroke-width="0.25" '
            'stroke-dasharray="0.8,0.6" opacity="0.5"/>'
        )

    for o in p["others"]:
        color = home_color if o["team"] == "home" else away_color
        html += f'<circle cx="{o["x"]}" cy="{o["y"]}" r="1.5" fill="{color}" stroke="#ffffff" stroke-width="0.2" opacity="0.65"/>'

    html += f'<circle cx="{p["ball"]["x"]}" cy="{p["ball"]["y"]}" r="0.9" fill="#fff" stroke="#333" stroke-width="0.15"/>'
    html += player_circle_html(p["passer"]["x"], p["passer"]["y"], p["passer"]["label"], home_color, "#ffffff", 0.25)
    html += player_circle_html(
        p["second_last_defender"]["x"], p["second_last_defender"]["y"], p["second_last_defender"]["label"],
        away_color, "#ffffff", 0.25,
    )
    html += player_circle_html(p["attacker"]["x"], p["attacker"]["y"], p["attacker"]["label"], home_color, "#ff4d4d", 0.4)
    html += player_circle_html(p["keeper"]["x"], p["keeper"]["y"], p["keeper"]["label"], away_color, "#ffffff", 0.25)

    ar = p["assistant_referee"]
    html += f'<circle cx="{ar["x"]}" cy="{ar["y"] + 0.3}" r="1" fill="#ffe14d"/>'
    html += f'<text x="{ar["x"]}" y="{ar["y"] - 0.6}" fill="#ffe14d" font-size="2" text-anchor="middle">{ar["label"]}</text>'
    html += "</svg></div>"

    probability = moment["analytics"]["offside_probability"]["result"]["probability"]
    html += (
        '<div class="lower-third">'
        f'<strong>OFFSIDE — {p["attacker"]["label"].upper()}</strong>'
        f'<span>Margin: {moment["margin_cm"]:.1f} cm &nbsp;|&nbsp; Confidence: {probability * 100:.1f}%</span>'
        "</div>"
    )

    inputs = moment["analytics"]["offside_probability"]["inputs"]
    sigma_frame = inputs["camera_frame_uncertainty_cm"] / 1.96
    sigma_total = math.sqrt(sigma_frame ** 2 + inputs["sigma_line_cm"] ** 2)
    ci_half_width = 1.96 * sigma_total
    margin = moment["margin_cm"]
    attacker_x = 110 + margin
    defender_num = p["second_last_defender"]["label"].split("#")[1]
    attacker_num = p["attacker"]["label"].split("#")[1]

    html += '<div class="inset-wrap"><svg viewBox="0 0 220 60" class="inset-svg">'
    if show_uncertainty_band:
        html += (
            f'<rect x="{110 - ci_half_width}" y="6" width="{2 * ci_half_width}" height="48" '
            'fill="#00e0ff" opacity="0.18"/>'
        )
        html += f'<text x="110" y="58" fill="#00e0ff" font-size="5.5" text-anchor="middle">±{ci_half_width:.1f}cm (95% CI)</text>'
    html += '<line x1="110" y1="2" x2="110" y2="54" stroke="#00e0ff" stroke-width="1"/>'
    html += '<text x="110" y="10" fill="#00e0ff" font-size="6" text-anchor="middle">offside line</text>'
    html += f'<line x1="40" y1="40" x2="110" y2="40" stroke="{away_color}" stroke-width="1"/>'
    html += f'<circle cx="40" cy="40" r="2.5" fill="{away_color}"/>'
    html += f'<text x="30" y="43" fill="{away_color}" font-size="6" text-anchor="end">#{defender_num}</text>'
    html += f'<line x1="40" y1="20" x2="{attacker_x}" y2="20" stroke="{home_color}" stroke-width="1"/>'
    html += f'<circle cx="{attacker_x}" cy="20" r="2.5" fill="{home_color}" stroke="#ff4d4d" stroke-width="0.8"/>'
    html += f'<text x="{attacker_x + 10}" y="23" fill="{home_color}" font-size="6" text-anchor="start">#{attacker_num} (+{margin}cm)</text>'
    html += f'<line x1="110" y1="30" x2="{attacker_x}" y2="30" stroke="#fff" stroke-width="0.6"/>'
    html += f'<text x="{(110 + attacker_x) / 2}" y="29" fill="#fff" font-size="5" text-anchor="middle">{margin}cm</text>'
    html += "</svg></div>"

    html += f'<p class="confidence-line">Confidence: {moment["confidence"] * 100:.1f}% (z = {moment["analytics"]["offside_probability"]["result"]["z"]})</p>'

    return html


def render_incident_card_html(incident: dict) -> str:
    html = (
        '<div class="incident-card">'
        f'<h4>{incident["title"]} ({incident["year"]})</h4>'
        f'<div class="incident-meta">{incident["match"]}</div>'
        f'<p>{incident["description"]}</p>'
        f'<p><strong>Decision:</strong> {incident["decision"]}</p>'
    )
    if incident.get("comparison_to_today"):
        html += f'<div class="callout">{incident["comparison_to_today"]}</div>'
    html += "</div>"
    return html


def render_referee_card_html(referee_name: str, profile: dict) -> str:
    return (
        '<div class="team-card">'
        f"<h3>Match Officiating</h3>"
        f"<div>{referee_name}</div>"
        f'<div>{profile["var_reviews_triggered"]} VAR reviews this match — '
        f'{profile["overturned_count"]} overturned, {profile["upheld_count"]} upheld</div>'
        f'<div>{profile["penalties_awarded"]} penalties awarded '
        f'({profile["penalty_appeals"]} appeal{"s" if profile["penalty_appeals"] != 1 else ""} reviewed)</div>'
        f'<div>{profile["cautions_issued"]} cautions issued</div>'
        "</div>"
    )


def render_tactical_dna_radar_html(
    home_name: str, away_name: str, home_scores: dict, away_scores: dict,
    home_color: str, away_color: str,
) -> str:
    axis_order = ["pressing_intensity", "directness", "defensive_compactness", "transition_speed"]
    axis_labels = {
        "pressing_intensity": "Pressing Intensity",
        "directness": "Directness",
        "defensive_compactness": "Defensive Compactness",
        "transition_speed": "Transition Speed",
    }
    cx, cy, radius = 110, 110, 90

    def point(i, score):
        angle = math.radians(-90 + i * 90)
        r = radius * (score / 100)
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    def polygon_points(scores):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, scores[axis]) for i, axis in enumerate(axis_order)))

    grid_circles = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{radius * pct}" fill="none" stroke="#333" stroke-width="0.5"/>'
        for pct in (0.25, 0.5, 0.75, 1.0)
    )

    labels = ""
    for i, axis in enumerate(axis_order):
        lx, ly = point(i, 118)
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#999" font-size="9" text-anchor="middle">{axis_labels[axis]}</text>'

    home_poly = polygon_points(home_scores)
    away_poly = polygon_points(away_scores)

    return (
        '<svg viewBox="-60 -10 340 270" class="momentum-chart-svg">'
        f"{grid_circles}"
        f'<polygon points="{home_poly}" fill="{home_color}" fill-opacity="0.3" stroke="{home_color}" stroke-width="1.5"/>'
        f'<polygon points="{away_poly}" fill="{away_color}" fill-opacity="0.3" stroke="{away_color}" stroke-width="1.5"/>'
        f"{labels}"
        f'<text x="-50" y="252" fill="{home_color}" font-size="10">{home_name}</text>'
        f'<text x="200" y="252" fill="{away_color}" font-size="10">{away_name}</text>'
        "</svg>"
    )


def _blend_toward_red(hex_color: str, intensity: float) -> str:
    """intensity is expected roughly in [0, 100]; clamped so an out-of-range
    fatigue_index value (it can run slightly negative, e.g. -2.0, when a
    team is fresher than their own first-half baseline) never produces an
    invalid blend ratio."""
    ratio = max(0.0, min(1.0, intensity / 100))
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    blend = lambda c, target: round(c + (target - c) * ratio)
    return f"rgb({blend(r, 204)},{blend(g, 51)},{blend(b, 51)})"


def render_fatigue_zone_pitch_html(
    home_name: str, away_name: str, home_color: str, away_color: str,
    home_fatigue: float, home_spread: float, away_fatigue: float, away_spread: float,
) -> str:
    home_radius = 8 + home_spread / 100 * 10
    away_radius = 8 + away_spread / 100 * 10
    home_fill = _blend_toward_red(home_color, home_fatigue)
    away_fill = _blend_toward_red(away_color, away_fatigue)

    return (
        '<svg viewBox="-2 -2 104 72" class="pitch-svg">'
        '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>'
        '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">'
        '<rect x="0" y="0" width="100" height="68"/>'
        '<line x1="50" y1="0" x2="50" y2="68"/>'
        '<circle cx="50" cy="34" r="8.7"/>'
        "</g>"
        f'<ellipse cx="30" cy="34" rx="{home_radius:.1f}" ry="{home_radius:.1f}" '
        f'fill="{home_fill}" fill-opacity="0.6" stroke="{home_color}" stroke-width="0.5"/>'
        f'<ellipse cx="70" cy="34" rx="{away_radius:.1f}" ry="{away_radius:.1f}" '
        f'fill="{away_fill}" fill-opacity="0.6" stroke="{away_color}" stroke-width="0.5"/>'
        f'<text x="30" y="60" fill="{home_color}" font-size="4" text-anchor="middle">{home_name}</text>'
        f'<text x="70" y="60" fill="{away_color}" font-size="4" text-anchor="middle">{away_name}</text>'
        "</svg>"
    )
