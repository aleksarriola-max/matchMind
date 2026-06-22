import os

import httpx

from backend.engines import explainer
from backend.engines.verifier import verify

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"

VALID_PERSONAS = {"beginner", "analyst", "kid", "journalist", "coach"}
DEFAULT_PERSONA = "beginner"
chat_personas: dict[int, str] = {}

HELP_TEXT = (
    "I'm MatchMind — ask me anything about the match, or:\n"
    "/persona <beginner|analyst|kid|journalist|coach> — change how I explain\n"
    "/outrage <your hot take> — I'll steelman your side, then the counter-case\n"
    "/help — show this message"
)
START_TEXT = "Welcome to MatchMind! " + HELP_TEXT


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def handle_message(text: str, chat_id: int) -> str:
    text = text.strip()
    if text == "/start":
        return START_TEXT
    if text == "/help":
        return HELP_TEXT
    if text.startswith("/persona"):
        return _handle_persona_command(text, chat_id)
    if text.startswith("/outrage"):
        take = text[len("/outrage"):].strip()
        if not take:
            return "Usage: /outrage <your hot take>"
        return _format_outrage_response(take)
    persona = chat_personas.get(chat_id, DEFAULT_PERSONA)
    return _format_ask_response(text, persona)


def _handle_persona_command(text: str, chat_id: int) -> str:
    name = text[len("/persona"):].strip().lower()
    if name not in VALID_PERSONAS:
        return "Usage: /persona <beginner|analyst|kid|journalist|coach>"
    chat_personas[chat_id] = name
    return f"Persona set to {name}."


def _format_ask_response(question: str, persona: str) -> str:
    moment_id = explainer.route(question)
    grounded = explainer.ground(question, moment_id)
    answer = explainer.compose_demo(persona, grounded["moment"], grounded["retrieved"])
    if grounded["moment"] is not None:
        evidence_texts = grounded["moment"]["evidence"]
    else:
        evidence_texts = [r["text"] for r in grounded["retrieved"]]
    verification = verify(answer, evidence_texts)
    ex = explainer.explain(moment_id, grounded["moment"], grounded["retrieved"], verification)

    lines = [f"<b>{_escape_html(answer)}</b>", ""]
    if verification["verified"]:
        lines.append(f"✅ Verified (coverage: {round(verification['coverage'] * 100)}%)")
    else:
        lines.append(f"⚠️ Unverified (coverage: {round(verification['coverage'] * 100)}%)")
    lines.append("")
    lines.append(f"📊 Confidence: {ex['confidence'] * 100:.1f}%")
    lines.append(_escape_html(ex["confidence_basis"]))
    lines.append("")
    lines.append("📚 Sources:")
    for s in ex["sources"]:
        lines.append(f"- {_escape_html(s['title'])} ({_escape_html(s['source'])}, score {s['score']:.2f})")
    lines.append("")
    lines.append("🔍 Evidence:")
    for e in ex["evidence"]:
        lines.append(f"- {_escape_html(e)}")

    if ex["counterfactual"]:
        lines.append("")
        lines.append(f"💡 {_escape_html(ex['counterfactual'])}")

    if ex["debate"]:
        lines.append("")
        lines.append(f"⚖️ Stands: {_escape_html(ex['debate']['stands'])}")
        lines.append(f"⚖️ Overturn: {_escape_html(ex['debate']['overturn'])}")

    return "\n".join(lines)


def _format_outrage_response(take: str) -> str:
    result = explainer.outrage(take)
    lines = ["<b>What actually happened</b>", _escape_html(result["summary"])]

    if result["steelman"] is None:
        lines.append("")
        lines.append(
            "This isn't a contested officiating call, so there's no counter-case here — just what happened."
        )
        return "\n".join(lines)

    verification = verify(result["counter"], result["evidence"])

    lines.append("")
    lines.append(f"🗣 Your side: {_escape_html(result['steelman'])}")
    lines.append("")
    lines.append(f"⚖️ The counter-case: {_escape_html(result['counter'])}")
    lines.append("✅ Verified" if verification["verified"] else "⚠️ Unverified")
    lines.append("")
    lines.append(f"📣 {_escape_html(result['verdict'])}")

    return "\n".join(lines)


def poll_loop() -> None:
    offset = 0
    while True:
        response = httpx.get(
            TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN, method="getUpdates"),
            params={"offset": offset, "timeout": 30},
            timeout=35,
        )
        for update in response.json().get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message or "text" not in message:
                continue
            reply = handle_message(message["text"], message["chat"]["id"])
            httpx.post(
                TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage"),
                json={"chat_id": message["chat"]["id"], "text": reply, "parse_mode": "HTML"},
            )


if __name__ == "__main__":
    poll_loop()
