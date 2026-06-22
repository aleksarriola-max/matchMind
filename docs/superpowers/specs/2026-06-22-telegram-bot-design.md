# Telegram Bot — Design

**Goal:** Phase 3 of a 4-phase initiative (Live Replay → Voice narration →
Telegram bot → Docling ingestion). Build the `integrations/telegram_bot.py`
CLAUDE.md and README.md already document — the same explainer pipeline in
any chat app — using raw HTTP calls via `httpx` (zero extra dependencies,
per README's explicit framing).

---

## 1. Module structure

```python
# integrations/telegram_bot.py
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
```

## 2. `handle_message(text: str, chat_id: int) -> str`

Pure dispatch + formatting function, no network calls — fully unit-testable.

```python
def handle_message(text: str, chat_id: int) -> str:
    text = text.strip()
    if text in ("/start",):
        return START_TEXT
    if text in ("/help",):
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
```

## 3. `_format_ask_response(question, persona) -> str`

Mirrors `/api/ask`'s pipeline exactly (`route` → `ground` → `compose_demo`
→ `verify` → `explain`), formatted as Telegram HTML:

```
<b>{answer}</b>

✅ Verified (coverage: 94%)        [or ⚠️ Unverified (coverage: NN%)]

📊 Confidence: 99.7%
{confidence_basis}

📚 Sources:
- {title} ({source}, score {score})
...

🔍 Evidence:
- {evidence sentence}
...

💡 {counterfactual}                [only if present]

⚖️ Stands: {debate.stands}
⚖️ Overturn: {debate.overturn}     [only if debate present]
```

All interpolated text is passed through `_escape_html()` (escapes `&`,
`<`, `>`) before insertion, since it appears inside an HTML-parsed message.

## 4. `_format_outrage_response(take) -> str`

Mirrors `/api/outrage`'s pipeline (`explainer.outrage()` + `verify()` on
the counter when present):

```
<b>What actually happened</b>
{summary}

🗣 Your side: {steelman}

⚖️ The counter-case: {counter}
✅ Verified              [or ⚠️ Unverified, only when steelman/counter present]

📣 {verdict}
```
When `steelman` is `None` (no-debate moment, or no moment matched at all),
instead: `"This isn't a contested officiating call, so there's no
counter-case here — just what happened."` (same fallback text as the
frontend's Debate tab).

## 5. `poll_loop()` — network loop, not unit-tested

```python
def poll_loop():
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
```
This function is intentionally not unit-tested in this phase — it requires
a real `TELEGRAM_BOT_TOKEN` and live Telegram servers to exercise
meaningfully. `handle_message` and the two formatters carry all the
testable logic.

## 6. Testing

New `tests/test_telegram_bot.py`:
- `/start`, `/help` return the expected text.
- `/persona analyst` then a follow-up question uses that persona for that
  `chat_id` (and a *different* `chat_id` still gets the default) —
  confirms the in-memory dict is correctly keyed.
- `/persona nonsense` returns the usage message, doesn't change state.
- `/outrage <text>` for a moment with debate (offside_27) — checks the
  formatted reply contains steelman/counter/verdict and a verified badge.
- `/outrage <text>` for a moment without debate, and for an off-topic
  take — checks the no-counter-case fallback text appears.
- A plain question routing to a moment, and an off-topic plain question
  — checks the formatted ask reply's structure (verified badge,
  confidence, sources, evidence) and the graceful fallback respectively.
- HTML escaping: a question/take containing `<`, `>`, or `&` doesn't
  break the output (defensive check, even though current data doesn't
  contain these characters).

## Out of scope

- Phase 4 (Docling ingestion) — separate spec.
- Live network verification — left for later with a real bot token.
- Any change to `backend/` or `frontend/` — this phase only adds the new
  `integrations/telegram_bot.py` module and its test file.
- Persisting `chat_personas` across process restarts — in-memory only,
  matching the bot's simple, stateless-between-runs scope.
