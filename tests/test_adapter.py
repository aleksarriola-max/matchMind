import importlib

import httpx
import pytest


@pytest.fixture(autouse=True)
def _restore_adapter_demo_mode():
    yield
    from backend.llm import adapter
    importlib.reload(adapter)


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


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def test_health_info_ollama(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="ollama")
    info = adapter.health_info()
    assert info == {"provider": "ollama", "model": "granite3.3:8b"}


def test_ollama_generate_success(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="ollama")

    def fake_post(url, json, timeout):
        assert url == "http://localhost:11434/api/chat"
        assert json["model"] == "granite3.3:8b"
        assert json["messages"] == [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ]
        return _FakeResponse({"message": {"content": "fake answer"}})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert adapter.generate("system prompt", "user prompt") == "fake answer"


def test_ollama_generate_propagates_http_error(monkeypatch):
    adapter = _reload_adapter(monkeypatch, provider="ollama")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse({}, status_code=500))
    with pytest.raises(httpx.HTTPStatusError):
        adapter.generate("system prompt", "user prompt")
