import os

PROVIDER = os.environ.get("MATCHMIND_LLM_PROVIDER", "demo").lower()
MODEL_ID = os.environ.get("GRANITE_MODEL_ID", "ibm/granite-3-3-8b-instruct")


def generate(system: str, prompt: str, max_tokens: int = 700) -> str:
    if PROVIDER == "demo":
        return ""
    if PROVIDER == "watsonx":
        raise NotImplementedError("watsonx provider is not implemented until Phase 6")
    if PROVIDER == "ollama":
        raise NotImplementedError("ollama provider is not implemented until Phase 6")
    raise ValueError(f"Unknown MATCHMIND_LLM_PROVIDER: {PROVIDER!r}")


def health_info() -> dict:
    return {
        "provider": PROVIDER,
        "model": MODEL_ID if PROVIDER != "demo" else None,
    }
