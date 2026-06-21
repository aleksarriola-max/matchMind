# Eval Harness — Design

**Goal:** Build the `evals/` package that `CLAUDE.md` already documents but
doesn't exist, replacing the currently-unverified "Evaluation results" table
with real, reproducible numbers. This is Phase 1 of a three-phase plan
(eval harness → outrage endpoint → consistency analyzer); Phases 2–3 are
out of scope here.

**Architecture:** Two independent, manually-run scripts (no CI wiring),
matching the commands `CLAUDE.md`'s Quick Start already documents:

```
python -m evals.run_evals          # golden harness: routing/retrieval/verification
python -m evals.verifier_redteam   # adversarial attacks on the verifier
```

Both exercise existing pipeline code (`explainer.route/ground/compose_demo`,
`verify`, `momentum_curve`) — no new application code is added to
`backend/`, only the `evals/` package and a `CLAUDE.md` table update.

---

## 1. `evals/golden_questions.json`

75 entries, each shaped:

```json
{"question": "...", "expected_moment_id": "offside_27", "expected_top_source": "Law 11 — Offside Offence"}
```

`expected_moment_id` is `null` for questions that should not route to any
moment. `expected_top_source` is the knowledge-base section title
(`## heading` in `laws_and_tactics.md`) the retriever should surface as its
top result; `null` for the 10 off-topic questions where no section is
relevant.

Distribution (75 total):
- **56**: 7 moments (`offside_27`, `handball_38`, `halftime_shift`, `sub_58`,
  `goal_home_1`, `fatigue_71`, `goal_home_2`) × 8 paraphrased question
  variants each, reusing/extending the keyword sets already in
  `explainer.ROUTE_KEYWORDS` so each variant is plausible. Each variant's
  `expected_top_source` is the knowledge-base section most relevant to that
  moment (e.g. all 8 `offside_27` variants expect `"Law 11 — Offside
  Offence"`).
- **9**: one general-knowledge question per knowledge-base section (the 9
  `## ` headings in `laws_and_tactics.md`), with `expected_moment_id: null`
  but a real `expected_top_source` — isolates retrieval quality from
  moment-routing.
- **10**: off-topic questions (stadium logistics, weather, ticket prices,
  unrelated football trivia) with `expected_moment_id: null` and
  `expected_top_source: null` — confirms `route()` correctly returns
  nothing and the retriever isn't graded on these.

## 2. `evals/run_evals.py`

Runs in `demo` mode only (routing/retrieval/verification don't depend on
the LLM provider). For each entry in `golden_questions.json`:

1. `moment_id = explainer.route(question)` → compare to `expected_moment_id`.
2. `grounded = explainer.ground(question, moment_id)` → check whether
   `expected_top_source` appears in `grounded["retrieved"]` (precision\@1:
   is it `retrieved[0]["title"]`; MRR: `1 / rank` of first match, `0` if
   absent), skipped when `expected_top_source` is `null`.
3. `answer = explainer.compose_demo(...)`, `verification = verify(answer, evidence_texts)`
   → collect `verification["verified"]` and `["coverage"]` for the 65
   grounded questions (moment or knowledge-section variants); skipped for
   the 10 off-topic questions (nothing to verify against).

Aggregate metrics: routing accuracy, retrieval precision\@1, MRR,
verification pass rate, mean coverage.

**Momentum sanity checks** (3, against `GET /api/match`'s computed curve
via `analytics.momentum_curve()`):
1. Value at minute 20 is negative (dip following the 19' away goal).
2. Value at minute 65 is greater than the value at minute 45 (recovery
   following the 63' equaliser).
3. All 19 points are finite numbers within `[-100, 100]` (no NaN/runaway
   values) and minutes run `0, 5, ..., 90` in order.

Writes `evals/results.json`:
```json
{
  "routing_accuracy": 0.97,
  "retrieval_precision_at_1": 0.95,
  "mrr": 0.84,
  "verification_pass_rate": 1.0,
  "mean_coverage": 0.92,
  "momentum_sanity_checks": {"passed": 3, "total": 3},
  "total_questions": 75
}
```
Prints the same as a human-readable summary table. Exits 0 always (this is
a reporting tool, not a CI gate, matching the "manual scripts" framing).

## 3. `evals/verifier_redteam.py`

4 attack categories, each a hand-written `(grounded_evidence, attack_answer)`
pair reusing real moment evidence:

- **Numeric corruption**: a true sentence with one number changed (e.g.
  margin "11 cm" → "55 cm").
- **Fabrication**: a sentence with no basis in any evidence (invented
  stat or claim).
- **Entity-swap**: a true sentence with team names swapped (e.g. "France"
  ↔ "Argentina") — both names exist somewhere in the evidence corpus, so
  lexical overlap stays high.
- **Negation**: a true sentence inverted ("disallowed" → "allowed",
  "no penalty" → "a penalty was given") — lexical overlap stays high.

Each attack runs twice:
- `MATCHMIND_LLM_PROVIDER=demo` → lexical-only `verify()`. Expected: catches
  numeric corruption and fabrication, **misses** entity-swap and negation
  (this is the documented blind spot).
- `MATCHMIND_LLM_PROVIDER=ollama` → Granite entailment `verify()` (requires
  a running local Ollama with `granite3.3:8b`, per the Phase 0 work).
  Expected: catches all 4.

Writes `evals/redteam_results.json`:
```json
{
  "demo": {"numeric_corruption": "caught", "fabrication": "caught", "entity_swap": "missed", "negation": "missed"},
  "ollama": {"numeric_corruption": "caught", "fabrication": "caught", "entity_swap": "caught", "negation": "caught"}
}
```
If Ollama isn't reachable when the script runs, the `ollama` section
reports `"skipped (ollama unreachable)"` per category rather than failing
the whole script — these are diagnostic scripts, not gated tests.

## 4. `CLAUDE.md` update

Replace the current "Evaluation results (last run)" table with the real
values from a completed `evals/results.json` + `evals/redteam_results.json`
run, and update the "Run:" line to reflect that `evals/__init__.py` now
exists and the commands work as documented.

## Out of scope

- Outrage endpoint, consistency analyzer (Phases 2–3).
- CI/pre-commit wiring of these scripts.
- Any change to `backend/` application code — this phase only adds
  `evals/` and updates documentation.
