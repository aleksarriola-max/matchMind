import os

import httpx

PROVIDER = os.environ.get("MATCHMIND_LLM_PROVIDER", "demo").lower()
MODEL_ID = os.environ.get("GRANITE_MODEL_ID", "ibm/granite-3-3-8b-instruct")
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


def health_info() -> dict:
    if PROVIDER == "demo":
        model = None
    elif PROVIDER == "ollama":
        model = OLLAMA_MODEL
    else:
        model = MODEL_ID
    return {
        "provider": PROVIDER,
        "model": model,
    }
