# Ollama/Granite Integration — Design

**Goal:** Make `MATCHMIND_LLM_PROVIDER=ollama` actually call a real Granite model
(`granite3.3:8b` via local Ollama), and use that same call to add a Granite
entailment pass to the verifier, satisfying the AI Builders Challenge's
"use at least one of IBM Granite / Docling / Langflow / Context Forge / IBM Bob"
requirement with a real, working integration.

**Architecture:** Two independent consumers of `adapter.generate()`:
1. `adapter.generate()` itself, implemented for the `ollama` provider.
2. `verifier.verify()`, which uses `adapter.generate()` (when provider != `demo`)
   to ask Granite which sentences in an answer aren't supported by the evidence,
   falling back to the existing lexical check on any failure.

The demo-mode answer composer (`explainer.compose_demo`) and `/api/ask` are
**not** changed — they keep calling the deterministic composer for the answer
text. Only the verifier gets a real Granite-backed check layered on top.

---

## 1. `backend/llm/adapter.py`

```python
import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite3.3:8b")
OLLAMA_TIMEOUT_S = 120

def generate(system: str, prompt: str, max_tokens: int = 700) -> str:
    if PROVIDER == "demo":
        return ""
    if PROVIDER == "watsonx":
        raise NotImplementedError("watsonx provider is not implemented until Phase 6")
    if PROVIDER == "ollama":
        return _generate_ollama(system, prompt, max_tokens)
    raise ValueError(f"Unknown MATCHMIND_LLM_PROVIDER: {PROVIDER!r}")

def _generate_ollama(system: str, prompt: str, max_tokens: int) -> str:
    response = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=OLLAMA_TIMEOUT_S,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
```

- `health_info()` reports `{"provider": "ollama", "model": "granite3.3:8b"}` —
  no change needed, already generic over `MODEL_ID`/`OLLAMA_MODEL` naming
  (model name surfaced via `OLLAMA_MODEL` when provider is `ollama`).
- Errors (connection refused, timeout, non-2xx, malformed JSON) propagate as
  exceptions. `adapter.generate()` does not catch anything itself — callers
  decide whether a failure should be fatal or should fall back.
- `watsonx` remains `NotImplementedError` — out of scope for this task.

## 2. `backend/engines/verifier.py`

Existing lexical logic is renamed to `_verify_lexical(answer, evidence_texts)`
with unchanged behavior. `verify()` becomes:

```python
def verify(answer: str, evidence_texts: list[str]) -> dict:
    lexical_result = _verify_lexical(answer, evidence_texts)
    if adapter.PROVIDER == "demo":
        return lexical_result
    try:
        return _verify_granite(answer, evidence_texts, lexical_result)
    except Exception:
        return lexical_result
```

`_verify_granite` builds a strict-format prompt:

- System: instructs Granite to act as a fact-checker, comparing ANSWER
  sentences against EVIDENCE, and to respond with **only** a JSON array of
  the unsupported sentences (exact substrings from ANSWER), or `[]` if all
  sentences are supported.
- User: `EVIDENCE:\n<joined evidence texts>\n\nANSWER:\n<answer>`

Parsing:
- `json.loads()` the response. If it's not a list, or any element isn't a
  string, raise (caught by the outer `except Exception` in `verify()`).
- `checked_sentences` reuses the existing `_sentences(answer)` count (same
  sentence-splitting as the lexical method, so the two methods are
  comparable).
- `coverage = (checked - len(unsupported)) / checked if checked else 1.0`.
- `verified = len(unsupported) == 0`.
- `method = "granite"`.

Any exception anywhere in this path (network error, timeout, JSON parse
failure, unexpected shape) falls back to `lexical_result` — `method` stays
`"lexical"` in that case, exactly as `CLAUDE.md` already documents.

## 3. Tests

- `tests/test_adapter.py`: remove `test_ollama_not_implemented`. Add:
  - `test_ollama_generate_success` — monkeypatch `httpx.post` to return a
    fake response object with `.json()` returning
    `{"message": {"content": "fake answer"}}` and `.raise_for_status()` as
    a no-op; assert `generate(...)` returns `"fake answer"`.
  - `test_ollama_generate_propagates_http_error` — monkeypatch `httpx.post`
    to return a response whose `.raise_for_status()` raises
    `httpx.HTTPStatusError`; assert it propagates.
- `tests/test_verifier.py`: add, with `MATCHMIND_LLM_PROVIDER=ollama` set via
  monkeypatch + adapter reload (same pattern as `test_adapter.py`):
  - `test_granite_entailment_success` — monkeypatch `adapter.generate` to
    return a JSON array naming one unsupported sentence; assert
    `method == "granite"` and that sentence appears in `unsupported`.
  - `test_granite_entailment_falls_back_on_failure` — monkeypatch
    `adapter.generate` to raise; assert the result matches what
    `_verify_lexical` alone would produce (`method == "lexical"`).
- No real network/Ollama calls in the automated suite.

## 4. Config

Create `.env.example` (referenced by `CLAUDE.md`'s Quick Start but missing
from the repo):

```
MATCHMIND_LLM_PROVIDER=demo
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
GRANITE_MODEL_ID=ibm/granite-3-3-8b-instruct
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=granite3.3:8b
TELEGRAM_BOT_TOKEN=
```

## Out of scope

- Wiring `adapter.generate()` into the actual `/api/ask` answer text
  (still uses `compose_demo()`).
- `watsonx` provider implementation.
- Any frontend changes (response shape is unchanged; `verification.method`
  already flows through to the Ask MatchMind tab's existing rendering).

## Manual verification

Once `ollama pull granite3.3:8b` completes locally, run a one-off script
calling `adapter.generate()` directly with `MATCHMIND_LLM_PROVIDER=ollama`
set, and call `verify()` with a deliberately wrong claim to confirm the
Granite entailment pass actually flags it (not just the lexical fallback).
