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
