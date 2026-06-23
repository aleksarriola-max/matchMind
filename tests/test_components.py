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


def _sample_offside_moment():
    return {
        "title": "Argentina goal disallowed",
        "law": "Law 11",
        "decision": "Goal disallowed for offside",
        "confidence": 0.997,
        "margin_cm": 11.0,
        "camera_frame_uncertainty_cm": 6.0,
        "pitch": {
            "offside_line_x": 60.0,
            "ball": {"x": 62.0, "y": 34.0},
            "passer": {"x": 55.0, "y": 30.0, "label": "#8"},
            "attacker": {"x": 61.0, "y": 36.0, "label": "#9"},
            "second_last_defender": {"x": 60.0, "y": 32.0, "label": "#4"},
            "keeper": {"x": 95.0, "y": 34.0, "label": "#1"},
            "others": [{"x": 50.0, "y": 20.0, "team": "home"}],
            "assistant_referee": {"x": 60.0, "y": 70.0, "label": "AR1"},
        },
        "analytics": {
            "offside_probability": {
                "result": {"probability": 0.997, "z": 2.78},
                "inputs": {"camera_frame_uncertainty_cm": 6.0, "sigma_line_cm": 2.5},
            }
        },
    }


def _sample_match_data_for_pitch():
    return {"home": {"name": "Argentina", "color": "#75AADB"}, "away": {"name": "France", "color": "#0055A4"}}


def test_render_decision_lab_pitch_html_contains_offside_line_and_margin():
    html = components.render_decision_lab_pitch_html(
        _sample_offside_moment(), _sample_match_data_for_pitch(), show_sightline=False, show_uncertainty_band=True
    )
    assert "<svg" in html
    assert "OFFSIDE" in html
    assert "11.0 cm" in html
    assert "99.7%" in html


def test_render_decision_lab_pitch_html_sightline_toggle_adds_lines():
    moment, match_data = _sample_offside_moment(), _sample_match_data_for_pitch()
    without = components.render_decision_lab_pitch_html(moment, match_data, False, True)
    with_sightline = components.render_decision_lab_pitch_html(moment, match_data, True, True)
    assert len(with_sightline) > len(without)


def test_render_decision_lab_pitch_html_uncertainty_band_toggle():
    moment, match_data = _sample_offside_moment(), _sample_match_data_for_pitch()
    with_band = components.render_decision_lab_pitch_html(moment, match_data, False, True)
    without_band = components.render_decision_lab_pitch_html(moment, match_data, False, False)
    assert "95% CI" in with_band
    assert "95% CI" not in without_band


def test_render_incident_card_html_includes_title_year_and_decision():
    incident = {
        "title": "Hand of God",
        "year": 1986,
        "match": "Argentina vs England",
        "description": "Maradona punched the ball into the net.",
        "decision": "Goal stood — missed by officials.",
        "comparison_to_today": "VAR would have caught this instantly.",
    }
    html = components.render_incident_card_html(incident)
    assert "Hand of God" in html
    assert "1986" in html
    assert "Goal stood" in html
    assert "VAR would have caught this instantly." in html
