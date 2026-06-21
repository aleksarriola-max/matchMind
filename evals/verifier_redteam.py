import importlib
import json
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EVALS_DIR / "redteam_results.json"

EVIDENCE = [
    "Law 11 defines offside as any part of the head, body, or feet being nearer to the opponents' goal line than both the ball and the second-last opponent when the ball is played.",
    "Semi-automated offside technology measured the attacker 11 cm beyond the second-last France defender at the moment the pass was played.",
    "Law 12 does not penalize the ball touching a player's hand or arm if the contact is accidental and the player had no realistic chance to avoid it.",
    "The referee ruled no penalty on the handball appeal, judging the contact accidental because the defender had no realistic time to avoid it.",
]

ATTACKS = {
    "numeric_corruption": (
        "Semi-automated offside technology measured the attacker 55 cm beyond the second-last France defender."
    ),
    "fabrication": (
        "The match was played in Buenos Aires in front of 90,000 fans."
    ),
    "entity_swap": (
        "Semi-automated offside technology measured the attacker 11 cm beyond the second-last Argentina defender."
    ),
    "negation": (
        "The referee ruled a penalty was given on the handball appeal, judging the contact deliberate."
    ),
}


def _run_provider(provider: str) -> dict:
    import os

    os.environ["MATCHMIND_LLM_PROVIDER"] = provider
    from backend.llm import adapter
    importlib.reload(adapter)
    from backend.engines import verifier
    importlib.reload(verifier)

    results = {}
    for name, answer in ATTACKS.items():
        result = verifier.verify(answer, EVIDENCE)
        if provider == "ollama" and result["method"] != "granite":
            # verify() swallows adapter failures and falls back to the
            # lexical method internally, so a method mismatch here means
            # the entailment call itself never ran (e.g. Ollama unreachable).
            results[name] = "skipped (ollama unreachable, fell back to lexical)"
            continue
        results[name] = "caught" if not result["verified"] else "missed"
    return results


def main() -> None:
    demo_results = _run_provider("demo")
    ollama_results = _run_provider("ollama")

    output = {"demo": demo_results, "ollama": ollama_results}
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Red-team results")
    print("-----------------")
    for provider, results in output.items():
        print(f"{provider}:")
        for name, outcome in results.items():
            print(f"  {name}: {outcome}")
    print()
    print(f"Results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
