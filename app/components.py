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


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
