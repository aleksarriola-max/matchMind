# Phase 1: Core Demo-Mode Pipeline — Design Spec

Date: 2026-06-12
Status: Approved, ready for implementation planning

## Context

MatchMind's full design is captured in `CLAUDE.md` (architecture, file map,
API schema, analytics formulas, data schemas, environment variables). That
document specifies the entire project — far too much for one implementation
pass. This spec scopes **Phase 1**: the minimum vertical slice that proves
the core pipeline end-to-end with zero external dependencies (no API keys,
no Docling, no real frontend).

Phase 1's goal: a running FastAPI app where `POST /api/ask` exercises the
full `route -> ground -> reason -> explain -> verify` pipeline in demo mode,
against real (if small) data, with a response that matches the documented
`/api/ask` schema exactly.

## Explicitly out of scope for Phase 1

These are real parts of MatchMind but are deferred to later phases and
**must not be assumed to exist** by Phase 1 code or tests:

- `backend/engines/analytics.py` — all 6 computed models. `/api/match` uses
  the static `momentum` array from `sample_match.json`; `/api/moment/{id}`
  returns the dossier with no computed analytics attached.
- `backend/engines/consistency.py`, `/api/consistency`, `/api/consistency/{topic}`,
  `historical_incidents.json`
- `POST /api/outrage` and `explainer.outrage()`
- watsonx / ollama providers in `llm/adapter.py` (demo only)
- Granite entailment pass in `verifier.py` (lexical only)
- `backend/rag/ingest.py` / Docling
- The real frontend (Decision Lab, voice narration, accessibility features,
  live replay) — Phase 1 ships a bare functional test page only
- `integrations/telegram_bot.py`
- `evals/` harness
- `telemetry.json`

## File structure (Phase 1 deliverables)

```
matchMind/
  backend/
    __init__.py
    main.py
    llm/
      __init__.py
      adapter.py
    rag/
      __init__.py
      retriever.py
    engines/
      __init__.py
      explainer.py
      verifier.py
    data/
      sample_match.json
      knowledge/
        laws_and_tactics.md
  frontend/
    index.html
  tests/
    test_retriever.py
    test_verifier.py
    test_explainer.py
    test_api.py
```

## Data layer

### `backend/data/sample_match.json`

Fixture: **Atlántica 2-1 Borealia**, following the top-level schema in
`CLAUDE.md` (`match_id`, `competition`, `home`, `away`, `score`, `events`,
`momentum`, `moments`).

`events` contains all 7 entries from the Moment IDs table in `CLAUDE.md`:
`offside_27`, `handball_38`, `halftime_shift`, `sub_58`, `goal_home_1`,
`fatigue_71`, `goal_home_2`.

`momentum` is a static array of `{minute, value}` points at 5-minute steps
from 0 to 90 (value range roughly -100..100, home positive). This is the
"static backup" mentioned in `CLAUDE.md`; Phase 1's `/api/match` returns it
as-is. Phase 2 (analytics) replaces this with `momentum_curve()`.

`moments` contains one dossier per moment ID, following the Moment dossier
schema in `CLAUDE.md`. Each dossier's `confidence` and presence of optional
fields (`counterfactual`, `debate`, `pitch`) reflect a `decision_class`,
which the explainer also reports in `confidence_components.decision_class`:

| Moment | decision_class | confidence | pitch | counterfactual | debate |
|---|---|---|---|---|---|
| `offside_27` | `measured` | 0.997 | yes (full geometry) | yes (~16ms) | yes |
| `handball_38` | `judgment` | ~0.74 | no | yes (53ms vs 250ms) | yes |
| `fatigue_71` | `inferred` | ~0.65 | no | no | no |
| `halftime_shift` | `general` | ~0.6 | no | no | no |
| `sub_58` | `general` | ~0.55 | no | no | no |
| `goal_home_1` | `general` | ~0.7 | no | no | no |
| `goal_home_2` | `general` | ~0.7 | no | no | no |

`offside_27`'s `pitch` object follows the schema in `CLAUDE.md` exactly
(`offside_line_x`, `ball`, `passer`, `attacker`, `second_last_defender`,
`keeper`, `others`, `assistant_referee`) — built now even though the
Decision Lab UI that renders it is a later phase, because the data is cheap
to write alongside the rest of the dossier and avoids a later schema-fixup
pass.

Every number that appears in a dossier's `evidence`, `counterfactual`, or
`referee_view` (e.g. `11 cm`, `99.7%`, `16 ms`, `53 ms`, `250 ms`) must also
appear verbatim in either that dossier's own `evidence` list or in the
knowledge pack, so the Phase 1 lexical verifier's numeric-consistency check
is meaningful rather than vacuously true.

### `backend/data/knowledge/laws_and_tactics.md`

A markdown file with `##`-level sections, each one TF-IDF-retrievable and
substantive enough to ground at least one moment:

1. Law 11 — Offside offence (rule definition, semi-automated offside
   technology, margin/calibration, the 11cm / 99.7% / z=2.78 figures)
2. Law 12 — Handball (deliberate vs. accidental, penalty criteria, the
   53ms / 250ms reaction figures)
3. VAR Protocol ("clear and obvious error" standard, review process)
4. Formation changes & tactical shifts (4-3-3 <-> 4-4-2 trade-offs)
5. Substitutions & game management
6. Wide overloads / attacking patterns
7. Set-piece & second-phase routines
8. Fatigue, pressing intensity, and late-game decline
9. Human reaction time & officiating benchmarks

This is a subset of the eventual 17-section pack described in `CLAUDE.md`;
later phases (Docling ingestion) extend it.

## Pipeline components

### `backend/rag/retriever.py`

- `get_retriever()` — module-level singleton. On first call, reads every
  `.md` file in `backend/data/knowledge/`, splits each on `##` headers into
  chunks of `{source, title, text}`.
- TF-IDF implemented in pure Python (no numpy/sklearn dependency, consistent
  with the "dependency-free retrieval" design decision in `CLAUDE.md`).
- `search(query, k=3) -> list[{source, title, text, score}]`, ranked by
  cosine similarity, highest first.

### `backend/llm/adapter.py`

- `PROVIDER = os.environ.get("MATCHMIND_LLM_PROVIDER", "demo").lower()`
- `generate(system, prompt, max_tokens=700) -> str`
- `demo` branch: returns `""` immediately.
- `watsonx` / `ollama` branches: raise `NotImplementedError("<provider> not implemented until Phase 6")` — explicit placeholders, not silent failures, so any accidental config of a non-demo provider in Phase 1 fails loudly.

### `backend/engines/explainer.py`

- `route(question: str) -> str | None` — keyword-based router. A dict maps
  each of the 7 moment IDs to a set of trigger words/phrases derived from
  its title and topic (e.g. `offside_27` <- {"offside", "disallowed", "27",
  "var"}). The moment with the most keyword hits wins; ties broken by lowest
  minute. No hits -> `None` (general question).
- `ground(question, moment_id) -> {retrieved, moment}` — `retriever.search(question, k=3)`
  plus the moment dossier (or `None` if `moment_id` is `None`).
- `reason(...)` — calls `adapter.generate`; always `""` in demo mode.
- `_compose_demo(question, persona, moment, retrieved) -> str` — builds the
  answer text directly from `moment["summary"]`/`moment["decision"]`/`moment["evidence"]`
  (or, if `moment is None`, from the retrieved chunks only), phrased per
  persona:
  - `beginner`: everyday analogy + plain definition
  - `analyst`: precise vocabulary, quantified, states caveats
  - `kid`: short sentences, playful tone
  - `journalist`: facts first, quotable framing, explicit uncertainty
  - `coach`: pattern -> why it works -> one concrete coaching point
- `explain(question, persona, moment, retrieved, answer) -> dict` — builds
  the `explainability` block of the `/api/ask` response: `confidence` (from
  the moment dossier, or a fixed prior per `decision_class` for general
  questions — e.g. `general` -> 0.5), `confidence_basis`,
  `confidence_components` (`evidence_coverage`, `retrieval_strength_top` =
  top retrieved chunk's score, `decision_class`, `note`), `sources` (from
  `retrieved`), `evidence` (from the moment dossier, empty list if none),
  `counterfactual`/`debate` (pass through from dossier, `null` if absent),
  `uncertainty` (templated string derived from `confidence`), `lineage`
  (the pipe-delimited trace string shown in `CLAUDE.md`).
- `outrage()` — **not implemented**; no route registers it.

### `backend/engines/verifier.py`

- `verify(answer: str, evidence_texts: list[str]) -> dict`
- Splits `answer` into sentences.
- For each sentence: (a) content-word overlap with the concatenation of
  `evidence_texts` must be >= 35%; (b) every number appearing in the sentence
  must appear verbatim somewhere in `evidence_texts`.
- Returns `{verified: bool, coverage: float, checked_sentences: int,
  unsupported: list[str], method: "lexical"}`.
- No Granite entailment pass (that's `provider != demo`, Phase 6).

### `backend/main.py`

FastAPI app with exactly these routes:

- `GET /` -> serves `frontend/index.html`
- `GET /api/health` -> `{provider, model, chunk_count}` (provider/model from
  `llm.adapter`, chunk_count from `rag.retriever`)
- `GET /api/match` -> `{match_id, competition, home, away, score, events, momentum}`
  read straight from `sample_match.json` (no analytics)
- `GET /api/moment/{id}` -> the dossier from `sample_match.json["moments"][id]`,
  404 if `id` not present
- `POST /api/ask` -> body `{question: str, persona: str, language: str}`.
  `persona` validated against the 5 keys in `CLAUDE.md` (422 if invalid).
  `language` is accepted but Phase 1 always responds in English (demo mode
  has no translation capability) — this is a known, documented Phase 1
  limitation, not a bug. Runs the full pipeline and returns the exact
  `/api/ask` response shape from `CLAUDE.md`, including the `llm` block
  (`{"provider": "demo", "model": null}` or similar).

## Testing strategy (TDD)

Tests are written before implementation, per component:

- `tests/test_retriever.py` — chunking splits correctly on `##`; `search()`
  returns ranked, topically-relevant results for a query per knowledge
  section (9 sections -> at least 9 targeted queries).
- `tests/test_verifier.py` — answers fully grounded in evidence are
  `verified: true`; answers with fabricated numbers or unsupported claims
  are flagged with the offending sentence in `unsupported`.
- `tests/test_explainer.py` — `route()` maps a representative question to
  each of the 7 moment IDs plus one general (no-match) case;
  `_compose_demo()` output for each persona contains persona-appropriate
  markers (e.g. `kid` answers use short sentences); `explain()` output has
  every key required by the `/api/ask` schema, including
  `confidence_components` and a well-formed `lineage` string.
- `tests/test_api.py` — `TestClient` smoke tests for all 5 routes; a full
  `POST /api/ask` round trip for each of the 5 personas against at least one
  moment-routed question and one general question, asserting
  `verification.verified is True` and `verification.method == "lexical"`.

## `frontend/index.html`

A single static page, no build step, no framework:

- A `<select>` for persona (5 options) and a `<select>` for language
  (English only, disabled/fixed in Phase 1 — present in the markup so
  Phase-later wiring doesn't require restructuring).
- A text `<input>` for the question and a "Ask" button.
- On submit, `fetch("/api/ask", {method: "POST", ...})` and render the JSON
  response as plain formatted text/lists: answer, confidence, sources,
  evidence, counterfactual/debate if present, verification status.
- No styling polish, no charts, no Decision Lab. This page exists purely so
  a human (or the test suite, via TestClient) can exercise `/api/ask`
  manually. It will be replaced wholesale in the frontend phase.

## Acceptance criteria

Phase 1 is done when:

1. `uvicorn backend.main:app --reload` starts with zero environment
   variables set and zero external API calls.
2. All `tests/` pass.
3. `POST /api/ask` for a question about each of the 7 moments returns a
   response matching the documented schema, with `verification.verified == true`.
4. `GET /api/health`, `/api/match`, `/api/moment/{id}` (for all 7 ids, plus a
   404 for an unknown id) work as specified.
5. The bare `frontend/index.html` can drive `/api/ask` from a browser and
   display the result.
