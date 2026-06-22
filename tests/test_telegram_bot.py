import pytest

from integrations import telegram_bot
from integrations.telegram_bot import DEFAULT_PERSONA, handle_message


@pytest.fixture(autouse=True)
def _reset_chat_personas():
    telegram_bot.chat_personas.clear()
    yield
    telegram_bot.chat_personas.clear()


def test_start_command():
    assert handle_message("/start", 1) == telegram_bot.START_TEXT


def test_help_command():
    assert handle_message("/help", 1) == telegram_bot.HELP_TEXT


def test_persona_command_sets_persona():
    response = handle_message("/persona analyst", 1)
    assert response == "Persona set to analyst."
    assert telegram_bot.chat_personas[1] == "analyst"


def test_persona_command_invalid_name():
    response = handle_message("/persona nonsense", 1)
    assert response == "Usage: /persona <beginner|analyst|kid|journalist|coach>"
    assert 1 not in telegram_bot.chat_personas


def test_persona_persists_per_chat_and_does_not_leak():
    handle_message("/persona kid", 1)
    assert telegram_bot.chat_personas.get(1) == "kid"
    assert telegram_bot.chat_personas.get(2, DEFAULT_PERSONA) == DEFAULT_PERSONA


def test_plain_question_routes_to_moment():
    response = handle_message("Why was the goal disallowed for offside in the 27th minute?", 1)
    assert "<b>" in response
    assert "✅ Verified" in response
    assert "📊 Confidence: 99.7%" in response
    assert "📚 Sources:" in response
    assert "🔍 Evidence:" in response
    assert "⚖️ Stands:" in response
    assert "⚖️ Overturn:" in response


def test_plain_question_offtopic_has_no_debate_section():
    response = handle_message("What is the weather like today?", 1)
    assert "<b>" in response
    assert "📊 Confidence: 50.0%" in response
    assert "⚖️ Stands:" not in response


def test_outrage_command_requires_take():
    assert handle_message("/outrage", 1) == "Usage: /outrage <your hot take>"
    assert handle_message("/outrage   ", 1) == "Usage: /outrage <your hot take>"


def test_outrage_command_with_debate():
    response = handle_message("/outrage That offside call was robbery, the goal should have stood!", 1)
    assert "<b>What actually happened</b>" in response
    assert "🗣 Your side:" in response
    assert "⚖️ The counter-case:" in response
    assert "✅ Verified" in response
    assert "📣" in response


def test_outrage_command_no_debate_moment():
    response = handle_message("/outrage Switching to a 4-4-2 at halftime was a disaster tactically.", 1)
    assert "<b>What actually happened</b>" in response
    assert "🗣 Your side:" not in response
    assert "no counter-case here" in response


def test_outrage_command_offtopic():
    response = handle_message("/outrage What is the weather like today?", 1)
    assert "no counter-case here" in response


def test_escape_html_escapes_angle_brackets_and_ampersand():
    assert telegram_bot._escape_html("<b>A & B</b>") == "&lt;b&gt;A &amp; B&lt;/b&gt;"
