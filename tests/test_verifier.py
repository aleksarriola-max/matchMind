import importlib
import json

import pytest

from backend.engines.verifier import verify

EVIDENCE = [
    "Law 11 defines offside as any part of the head, body, or feet being nearer to the opponents' goal line than both the ball and the second-last opponent when the ball is played.",
    "Semi-automated offside technology measured the attacker 11 cm beyond the second-last France defender at the moment the pass was played.",
    "Combining these uncertainties gives roughly 99.7% confidence that the attacker was genuinely in an offside position.",
]


def test_grounded_answer_is_verified():
    answer = EVIDENCE[1]
    result = verify(answer, EVIDENCE)
    assert result["verified"] is True
    assert result["coverage"] == 1.0
    assert result["checked_sentences"] == 1
    assert result["unsupported"] == []
    assert result["method"] == "lexical"


def test_fabricated_number_is_flagged():
    answer = "Semi-automated offside technology measured the attacker 55 cm beyond the second-last France defender."
    result = verify(answer, EVIDENCE)
    assert result["verified"] is False
    assert result["unsupported"] == [answer]


def test_unrelated_sentence_is_flagged():
    answer = "The stadium concession stands sell delicious tacos and lemonade."
    result = verify(answer, EVIDENCE)
    assert result["verified"] is False
    assert result["unsupported"] == [answer]


def test_mixed_answer_partial_coverage():
    grounded = EVIDENCE[1]
    unrelated = "The stadium concession stands sell delicious tacos and lemonade."
    answer = f"{grounded} {unrelated}"
    result = verify(answer, EVIDENCE)
    assert result["checked_sentences"] == 2
    assert result["coverage"] == 0.5
    assert result["unsupported"] == [unrelated]
    assert result["verified"] is False


def test_empty_answer_is_trivially_verified():
    result = verify("", EVIDENCE)
    assert result["checked_sentences"] == 0
    assert result["coverage"] == 1.0
    assert result["verified"] is True


@pytest.fixture(autouse=True)
def _restore_adapter_demo_mode():
    yield
    from backend.llm import adapter
    importlib.reload(adapter)


def _use_ollama_provider(monkeypatch):
    monkeypatch.setenv("MATCHMIND_LLM_PROVIDER", "ollama")
    from backend.llm import adapter
    return importlib.reload(adapter)


def test_granite_entailment_success(monkeypatch):
    adapter = _use_ollama_provider(monkeypatch)
    grounded = EVIDENCE[1]
    unrelated = "The stadium concession stands sell delicious tacos and lemonade."
    answer = f"{grounded} {unrelated}"
    monkeypatch.setattr(adapter, "generate", lambda system, prompt, max_tokens=700: json.dumps([unrelated]))

    result = verify(answer, EVIDENCE)
    assert result["method"] == "granite"
    assert result["verified"] is False
    assert result["unsupported"] == [unrelated]
    assert result["checked_sentences"] == 2
    assert result["coverage"] == 0.5


def test_granite_entailment_falls_back_on_failure(monkeypatch):
    adapter = _use_ollama_provider(monkeypatch)
    answer = EVIDENCE[1]

    def _raise(*args, **kwargs):
        raise RuntimeError("ollama unreachable")

    monkeypatch.setattr(adapter, "generate", _raise)

    result = verify(answer, EVIDENCE)
    assert result["method"] == "lexical"
    assert result["verified"] is True
    assert result["coverage"] == 1.0
