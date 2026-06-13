import importlib

import pytest


def _reload_adapter(monkeypatch, provider=None):
    if provider is None:
        monkeypatch.delenv("MATCHMIND_LLM_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("MATCHMIND_LLM_PROVIDER", provider)
    from backend.llm import adapter
    return importlib.reload(adapter)


def test_default_provider_is_demo(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider=None)
    assert adapter.PROVIDER == "demo"


def test_demo_generate_returns_empty_string(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="demo")
    assert adapter.generate("system prompt", "user prompt") == ""


def test_health_info_demo(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="demo")
    info = adapter.health_info()
    assert info == {"provider": "demo", "model": None}


def test_watsonx_not_implemented(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="watsonx")
    with pytest.raises(NotImplementedError):
        adapter.generate("system prompt", "user prompt")


def test_ollama_not_implemented(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="ollama")
    with pytest.raises(NotImplementedError):
        adapter.generate("system prompt", "user prompt")
