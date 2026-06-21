import json
from pathlib import Path

from backend.engines import analytics, explainer
from backend.engines.verifier import verify

EVALS_DIR = Path(__file__).resolve().parent
GOLDEN_PATH = EVALS_DIR / "golden_questions.json"
RESULTS_PATH = EVALS_DIR / "results.json"


def _load_golden() -> list[dict]:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def _evaluate_question(entry: dict) -> dict:
    question = entry["question"]
    moment_id = explainer.route(question)
    grounded = explainer.ground(question, moment_id)
    retrieved_titles = [r["title"] for r in grounded["retrieved"]]

    result = {
        "category": entry["category"],
        "routing_correct": None,
        "retrieval_rank": None,
        "verified": None,
        "coverage": None,
    }

    if entry["category"] in ("moment", "offtopic"):
        result["routing_correct"] = moment_id == entry["expected_moment_id"]

    if entry["category"] in ("moment", "knowledge") and entry["expected_top_source"]:
        result["retrieval_rank"] = (
            retrieved_titles.index(entry["expected_top_source"]) + 1
            if entry["expected_top_source"] in retrieved_titles
            else None
        )

    if entry["category"] in ("moment", "knowledge"):
        answer = explainer.compose_demo("analyst", grounded["moment"], grounded["retrieved"])
        if grounded["moment"] is not None:
            evidence_texts = grounded["moment"]["evidence"]
        else:
            evidence_texts = [r["text"] for r in grounded["retrieved"]]
        verification = verify(answer, evidence_texts)
        result["verified"] = verification["verified"]
        result["coverage"] = verification["coverage"]

    return result


def run_golden_harness() -> dict:
    entries = _load_golden()
    results = [_evaluate_question(entry) for entry in entries]

    routing_checked = [r for r in results if r["routing_correct"] is not None]
    retrieval_checked = [r for r in results if r["retrieval_rank"] is not None or r["category"] in ("moment", "knowledge")]
    retrieval_scored = [r for r in results if r["category"] in ("moment", "knowledge")]
    verification_checked = [r for r in results if r["verified"] is not None]

    routing_accuracy = sum(r["routing_correct"] for r in routing_checked) / len(routing_checked)
    precision_at_1 = sum(1 for r in retrieval_scored if r["retrieval_rank"] == 1) / len(retrieval_scored)
    mrr = sum((1 / r["retrieval_rank"]) if r["retrieval_rank"] else 0 for r in retrieval_scored) / len(retrieval_scored)
    verification_pass_rate = sum(r["verified"] for r in verification_checked) / len(verification_checked)
    mean_coverage = sum(r["coverage"] for r in verification_checked) / len(verification_checked)

    return {
        "total_questions": len(entries),
        "routing_accuracy": round(routing_accuracy, 4),
        "retrieval_precision_at_1": round(precision_at_1, 4),
        "mrr": round(mrr, 4),
        "verification_pass_rate": round(verification_pass_rate, 4),
        "mean_coverage": round(mean_coverage, 4),
    }


def run_momentum_sanity_checks() -> dict:
    events = explainer.MATCH_DATA["events"]
    weights = analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    curve = analytics.momentum_curve(events, weights)
    by_minute = {p["minute"]: p["value"] for p in curve}

    checks = {
        "dips_after_19th_minute_away_goal": by_minute[20] < 0,
        "recovers_after_63rd_minute_equaliser": by_minute[65] > by_minute[45],
        "all_points_finite_and_bounded": (
            [p["minute"] for p in curve] == list(range(0, 91, 5))
            and all(-100 <= p["value"] <= 100 for p in curve)
        ),
    }
    return {"passed": sum(checks.values()), "total": len(checks), "checks": checks}


def main() -> None:
    golden = run_golden_harness()
    momentum = run_momentum_sanity_checks()

    output = {**golden, "momentum_sanity_checks": {"passed": momentum["passed"], "total": momentum["total"]}}
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("Golden harness results")
    print("-----------------------")
    print(f"Total questions:           {golden['total_questions']}")
    print(f"Routing accuracy:          {golden['routing_accuracy']:.1%}")
    print(f"Retrieval precision@1:     {golden['retrieval_precision_at_1']:.1%}")
    print(f"MRR:                       {golden['mrr']:.4f}")
    print(f"Verification pass rate:    {golden['verification_pass_rate']:.1%}")
    print(f"Mean coverage:             {golden['mean_coverage']:.4f}")
    print()
    print("Momentum sanity checks")
    print("-----------------------")
    for name, passed in momentum["checks"].items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    print(f"{momentum['passed']}/{momentum['total']} passed")
    print()
    print(f"Results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
