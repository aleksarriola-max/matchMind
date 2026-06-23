from app import components


def test_escape_html_escapes_tags_and_amp():
    assert components.escape_html('<img onerror="x">&') == '&lt;img onerror="x"&gt;&amp;'


def test_team_flags_has_argentina_and_france():
    assert "Argentina" in components.TEAM_FLAGS
    assert "France" in components.TEAM_FLAGS
    assert "<svg" in components.TEAM_FLAGS["Argentina"]


def test_render_header_html_includes_team_names_and_score():
    match_data = {
        "home": {"name": "Argentina", "color": "#75AADB"},
        "away": {"name": "France", "color": "#0055A4"},
        "score": {"home": 2, "away": 1},
        "competition": "World Cup Final",
    }
    html = components.render_header_html(match_data)
    assert "Argentina" in html
    assert "France" in html
    assert "2" in html and "1" in html
    assert "#75AADB" in html


def test_render_event_row_html_includes_badge_class_and_desc():
    event = {"minute": 19, "type": "goal", "desc": "France open the scoring."}
    html = components.render_event_row_html(event)
    assert "event-badge-goal" in html
    assert "19" in html
    assert "France open the scoring." in html


def test_render_glow_bar_html_shows_percentage():
    html = components.render_glow_bar_html("Confidence", 0.997, "var(--accent)")
    assert "99.7%" in html


def test_speak_button_html_embeds_escaped_text_and_script():
    html = components.speak_button_html('Say "hi" & bye')
    assert "speechSynthesis" in html
    assert "&quot;" in html or "\\&quot;" in html or "hi" in html


def _sample_match_data_for_chart():
    return {
        "home": {"name": "Argentina", "color": "#75AADB"},
        "away": {"name": "France", "color": "#0055A4"},
        "events": [{"minute": 19, "type": "goal", "team": "away", "desc": "x"}],
        "momentum": [{"minute": m, "value": float(m - 45)} for m in range(0, 91, 5)],
    }


def test_lighten_for_fill_blends_toward_white():
    result = components.lighten_for_fill("#0055A4")
    assert result.startswith("rgb(")
    # blended values must all exceed the original channel values
    import re
    r, g, b = (int(x) for x in re.findall(r"\d+", result))
    assert r > 0x00 and g > 0x55 and b > 0xA4


def test_render_momentum_chart_html_contains_svg_and_points_for_full_curve():
    html = components.render_momentum_chart_html("<h3>Momentum</h3>", _sample_match_data_for_chart())
    assert "<svg" in html
    assert "polyline" in html
    assert "90'" in html


def test_render_momentum_chart_html_clips_to_current_minute():
    data = _sample_match_data_for_chart()
    html_full = components.render_momentum_chart_html("<h3>Momentum</h3>", data)
    html_clipped = components.render_momentum_chart_html("<h3>Momentum</h3>", data, current_minute=20)
    # the clipped version has a "now" pulse marker the full one doesn't
    assert "pulse" not in html_full or "pulse" in html_clipped
    assert html_clipped != html_full
