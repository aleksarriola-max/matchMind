# MatchMind — CLAUDE.md

> AI-powered explainability companion for soccer. Built for the IBM Soccer Challenge.
> Stack: FastAPI · IBM Granite (watsonx.ai / Ollama) · Docling · TF-IDF RAG · vanilla HTML+JS.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
# -> http://localhost:8000
```

Switch to real Granite (one env var, nothing else changes):

```bash
cp .env.example .env          # fill WATSONX_API_KEY + WATSONX_PROJECT_ID
export MATCHMIND_LLM_PROVIDER=watsonx   # or: ollama
```

Grow the knowledge pack with Docling:

```bash
pip install docling
python -m backend.rag.ingest Laws_of_the_Game_2025_26.pdf
```

Run evals:

```bash
python -m evals.run_evals          # 75-question golden harness
python -m evals.verifier_redteam  # red-team the hallucination firewall
```

Telegram bot:

```bash
export TELEGRAM_BOT_TOKEN=<token>
python -m integrations.telegram_bot
```

---

## Architecture — one pipeline, every question

```
question
  |
  v
ROUTE     backend/engines/explainer.py::route()
          Keyword router maps question to a match moment id
          (offside_27 | handball_38 | halftime_shift | fatigue_71 | sub_58 | goal_home_1 | goal_home_2)
          Upgrade path: Granite function-calling
  |
  v
GROUND    retriever.search(query, k=3)  +  moment dossier from sample_match.json
          TF-IDF cosine over ## sections of backend/data/knowledge/*.md
          Swap point: watsonx embeddings + vector store
  |
  v
REASON    backend/llm/adapter.py::generate(system, prompt)
          Provider selected by MATCHMIND_LLM_PROVIDER env var:
            "watsonx"  -> ibm/granite-3-3-8b-instruct via watsonx.ai REST
            "ollama"   -> granite3.3:8b via local Ollama
            "demo"     -> deterministic composer (same output schema, zero keys)
  |
  v
EXPLAIN   confidence · sources · uncertainty interval · counterfactual · debate · lineage
  |
  v
VERIFY    backend/engines/verifier.py::verify(answer, evidence_texts)
          Lexical coverage check + numeric consistency rule
          Second Granite pass when provider != demo
```

---

## File map

```
backend/
  main.py                       FastAPI app — all API routes defined here
  llm/
    adapter.py                  Single generate(system, prompt) interface; three providers
  rag/
    ingest.py                   Docling PDF -> markdown chunks in data/knowledge/
    retriever.py                TF-IDF retriever; get_retriever() singleton
  engines/
    explainer.py                Main pipeline: route -> ground -> reason -> explain
                                Also: outrage() for "explain my outrage" endpoint
    verifier.py                 Hallucination firewall (lexical + optional Granite)
    consistency.py              Decision Consistency Analyzer (historical incidents)
    analytics.py                All computed models (offside probability, fatigue index,
                                momentum reconstruction, counterfactual, handball reaction,
                                sensitivity analysis)
  data/
    sample_match.json           Demo fixture (Atlántica 2-1 Borealia) + moment dossiers
    historical_incidents.json   Real World Cup incidents 1986-2022 (6 incidents)
    telemetry.json              Per-15min windowed physical/positional data (both teams)
    knowledge/
      laws_and_tactics.md       Retrieval knowledge pack — 17 ## sections covering
                                Law 11, Law 12, VAR protocol, SAOT, tactics, coaching,
                                human performance
frontend/
  index.html                    Single-file UI — no build step
                                Sections: timeline · Decision Lab · Ask MatchMind ·
                                Explain My Outrage · Decision Consistency · Live Replay
                                Features: voice narration · colorblind palette · ARIA
integrations/
  telegram_bot.py               Long-polling Telegram bot; reuses explainer + outrage
evals/
  run_evals.py                  75-question golden harness (routing / retrieval / verification)
  verifier_redteam.py           Attacks the hallucination firewall
  golden_questions.json         Test questions + expected routes/answers
  results.json                  Last harness run results
  redteam_results.json          Last red-team results
docs/
  ARCHITECTURE.md               System diagram + API schema + scaling path
  METHODOLOGY.md                Math behind every number (offside model, fatigue index,
                                momentum reconstruction, confidence calibration)
  BUILD_PLAN.md                 3-week roadmap to submission
  DEMO_SCRIPT.md                Demo flow script
  LANGFLOW.md                   LangFlow orchestration guide
requirements.txt                fastapi · uvicorn · pydantic (docling + ibm-watsonx-ai optional)
.env.example                    All env vars with defaults
```

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serves `frontend/index.html` |
| GET | `/api/health` | Provider, model, chunk count |
| GET | `/api/match` | Match header + events + computed momentum curve |
| GET | `/api/moment/{id}` | Full moment dossier + computed analytics |
| POST | `/api/ask` | `{question, persona, language}` -> full explainability payload |
| POST | `/api/outrage` | `{take, language}` -> steelman + counter + verdict |
| GET | `/api/analytics` | All six computed models with formulas and inputs |
| GET | `/api/consistency/{topic}` | Historical comparison (offside\|handball\|goal-line\|penalty) |
| GET | `/api/consistency` | List available topics |

### POST /api/ask — response schema

```json
{
  "answer": "string",
  "persona": "beginner|analyst|kid|journalist|coach",
  "language": "English",
  "moment_id": "offside_27 | null",
  "verification": {
    "verified": true,
    "coverage": 0.94,
    "checked_sentences": 6,
    "unsupported": [],
    "method": "lexical|granite"
  },
  "explainability": {
    "confidence": 0.82,
    "confidence_basis": "string",
    "confidence_components": {
      "evidence_coverage": 0.94,
      "retrieval_strength_top": 0.16,
      "decision_class": "measured|judgment|inferred|general",
      "note": "string"
    },
    "sources": [{"title": "Law 11 — Offside offence", "source": "laws_and_tactics.md", "score": 0.16}],
    "evidence": ["string"],
    "counterfactual": "string | null",
    "debate": {"stands": "string", "overturn": "string"} | null,
    "uncertainty": "string",
    "lineage": "question -> route[offside_27] -> retrieve[3 chunks] -> ibm/granite-3-3-8b-instruct -> verifier[lexical]"
  },
  "llm": {"provider": "watsonx", "model": "ibm/granite-3-3-8b-instruct"}
}
```

---

## Moment IDs (routable via question keywords)

| ID | Minute | What happened |
|----|--------|---------------|
| `offside_27` | 27' | Atlántica goal disallowed, 11 cm margin — has pitch geometry + offside model |
| `handball_38` | 38' | Penalty appeal rejected — has handball reaction model |
| `halftime_shift` | 46' | Atlántica 4-3-3 -> 4-4-2, no analytics model |
| `fatigue_71` | 71' | Borealia collapse — has fatigue index model |
| `sub_58` | 58' | Atlántica winger substitution |
| `goal_home_1` | 63' | 1-1 equaliser from left overload |
| `goal_home_2` | 84' | 2-1 winner from second-phase corner |

---

## Computed analytics models (backend/engines/analytics.py)

### 1. Offside decision model
```
sigma_frame = frame_uncertainty_cm / 1.96
sigma_total = sqrt(sigma_frame^2 + sigma_line^2)   # sigma_line default 2.5 cm
z = margin_cm / sigma_total
P(offside) = Phi(z)
```
Demo values: margin=11 cm, frame_uncertainty=6 cm -> P=99.7%, z=2.78

### 2. Fatigue index
Four indicators per 15-min window vs first-half baseline (windows 0-2):
- `sprint_decline = (base_sprints - sprints[i]) / base_sprints`
- `line_stretch = (line_gap[i] - base_gap) / base_gap`
- `long_pass_drift = (long_pass[i] - base_long) / base_long`
- `pressing_decay = (ppda[i] - base_ppda) / base_ppda`
- `fatigue_index = 100 * mean(four indicators)`

### 3. Momentum reconstruction
Event-weighted, exponentially decayed per 5-min step (decay=0.85).
Weights in `telemetry.json -> event_weights_for_momentum`.
`GET /api/match` returns this series; that's what the UI chart renders.

### 4. Counterfactual timing
`delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000`
Demo: 11 cm / 7 m/s = 15.7 ms — less than one broadcast frame.

### 5. Handball reaction
`time_available_ms = deflection_distance_m / ball_speed_ms * 1000`
Compare vs human motor reaction ~250 ms. Demo: 53 ms — 4.7x deficit.

### 6. Offside sensitivity analysis
Sweeps sigma_line from 1.5-4.0 cm; proves P(offside) is stable across
plausible skeletal-tracking implementations.

---

## LLM adapter — provider switching

```python
# backend/llm/adapter.py
PROVIDER = os.environ.get("MATCHMIND_LLM_PROVIDER", "demo").lower()

generate(system, prompt, max_tokens=700)
  -> watsonx  : IBM watsonx.ai chat REST, IAM token exchange, granite-3-3-8b-instruct
  -> ollama   : local Ollama /api/chat, granite3.3:8b
  -> demo     : returns "" — engines compose grounded answers themselves
```

The demo composer in `explainer.py::_compose_demo()` produces the **identical
response schema** from the same grounded inputs. Swapping providers changes
one env var; nothing downstream changes.

---

## RAG retriever — how to extend the knowledge pack

```python
# backend/rag/retriever.py
# Chunks = every ## section of every .md in backend/data/knowledge/
# TF-IDF cosine similarity; get_retriever() is a module-level singleton

retriever.search(query, k=3)
# returns: [{"source": "laws_and_tactics.md", "title": "Law 11 — Offside offence",
#             "text": "...", "score": 0.16}]
```

To add knowledge:
1. `pip install docling`
2. `python -m backend.rag.ingest path/to/document.pdf`
3. Restart the server — retriever re-initialises on first request.

Or write `.md` files directly into `backend/data/knowledge/` with `## Heading` sections.

---

## Verification agent — how it works

```python
# backend/engines/verifier.py
verify(answer: str, evidence_texts: list[str]) -> dict

# Step 1 — lexical coverage (always runs):
#   Each sentence's content words must overlap >=35% with the evidence corpus.
#   Every number in a sentence must exist verbatim in the evidence.

# Step 2 — Granite entailment (runs when provider != demo):
#   Second Granite call: "list claims not supported by the evidence"
#   Falls back to lexical result if this call fails.
```

Known blind spots (documented in evals/redteam_results.json):
- Entity-swap attacks (e.g. "Borealia" -> "Atlántica") pass lexical check if both
  names appear in evidence. The Granite pass catches these.
- Paraphrase/negation: lexical overlap is high even for inverted claims.

---

## Personas

| Key | Description |
|-----|-------------|
| `beginner` | Friendly, everyday analogies, no jargon without definition |
| `analyst` | Precise vocabulary, quantified evidence, honest caveats |
| `kid` | 10-year-old level, playful, very short sentences |
| `journalist` | Verifiable facts first, quotable framing, explicit uncertainty |
| `coach` | Pattern -> why it works -> one concrete drill/coaching point |

---

## Data schemas

### sample_match.json — top level
```json
{
  "match_id": "string",
  "competition": "string",
  "home": {"name": "string", "color": "#hex", "formation_start": "string", "formation_end": "string"},
  "away": {same},
  "score": {"home": int, "away": int},
  "events": [{"minute": int, "type": "goal|chance|var_review|card|tactical|substitution|pressure",
               "team": "home|away", "id": "string (optional)", "desc": "string"}],
  "momentum": [{"minute": int, "value": float}],  // static backup; /api/match uses computed version
  "moments": {"moment_id": {see below}}
}
```

### Moment dossier schema
```json
{
  "title": "string",
  "law": "string | null",
  "decision": "string",
  "confidence": 0.0-1.0,
  "margin_cm": float,                    // offside moments only
  "camera_frame_uncertainty_cm": float,  // offside moments only
  "summary": "string",
  "pitch": {                             // offside moments only — rendered by Decision Lab
    "offside_line_x": float,
    "ball": {"x": float, "y": float},
    "passer": {"x": float, "y": float, "label": "string"},
    "attacker": {"x": float, "y": float, "label": "string", "offside": bool},
    "second_last_defender": {"x": float, "y": float, "label": "string"},
    "keeper": {"x": float, "y": float, "label": "string"},
    "others": [{"x": float, "y": float, "team": "home|away"}],
    "assistant_referee": {"x": float, "y": float, "label": "string"}
  },
  "evidence": ["string"],
  "counterfactual": "string | null",
  "referee_view": "string | null",
  "debate": {"stands": "string", "overturn": "string"} | null
}
```

### telemetry.json schema
```json
{
  "windows": ["0-15", "15-30", "30-45", "45-60", "60-75", "75-90"],
  "teams": {
    "home|away": {
      "sprints": [int x6],
      "line_gap_def_mid_m": [float x6],
      "long_pass_share": [float x6],
      "ppda": [float x6]
    }
  },
  "event_weights_for_momentum": {"goal": 30, "chance": 12, ...}
}
```

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MATCHMIND_LLM_PROVIDER` | `demo` | `demo` / `watsonx` / `ollama` |
| `WATSONX_API_KEY` | — | Required for watsonx provider |
| `WATSONX_PROJECT_ID` | — | Required for watsonx provider |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | watsonx regional endpoint |
| `GRANITE_MODEL_ID` | `ibm/granite-3-3-8b-instruct` | Model ID on watsonx |
| `OLLAMA_URL` | `http://localhost:11434` | Local Ollama base URL |
| `OLLAMA_MODEL` | `granite3.3:8b` | Model tag in Ollama |
| `TELEGRAM_BOT_TOKEN` | — | Required for Telegram bot |

---

## Key design decisions

**Demo-mode parity.** The demo composer consumes the same grounded inputs and emits
the same response schema as Granite. The app runs with zero credentials; one env var
wires real Granite. Nothing downstream changes.

**Dependency-free retrieval.** TF-IDF over Docling-produced chunks is transparent —
every chunk's retrieval score is reported in `sources[].score`. The retriever is 60
lines; replacing it with watsonx embeddings is a contained swap.

**Calibrated confidence.** Two quantities, never conflated:
- *Decision probability* (e.g. 99.7%): P(the measured offside is real), from
  Gaussian error propagation. Shown in the "Computed decision model" box.
- *Explanation confidence* (e.g. 82%): calibrated prior by decision class
  (measured > judgment > inferred > general). Shown on the confidence bar.

**Computed analytics, not narration.** Every number in the UI is derived from
`analytics.py` with explicit formula, inputs, and uncertainty. The UI chart is the
`momentum_curve()` output; the counterfactual is `delay_needed = margin / speed`.

**Verification before display.** `verifier.verify()` runs on every answer before it
reaches the user. The "verified" badge or flagged claims are part of the contract,
not a nice-to-have.

---

## What NOT to do

- Do not add score prediction features — explicitly out of scope.
- Do not let the system override or replace referee decisions — it explains them.
- Do not display unverified numbers — every figure must exist in the evidence corpus.
- Do not change the response schema of `/api/ask` without updating the frontend and
  the Telegram bot — both parse the same payload.

---

## Evaluation results (last run)

| Metric | Score |
|--------|-------|
| Routing accuracy | 100% |
| Retrieval precision | 100% |
| MRR | 0.84 |
| Verification pass rate | 100% |
| Answer coverage | 0.92 |
| Momentum sanity checks | 3/3 |
| Red-team: numeric corruption caught | 4/4 |
| Red-team: fabrication caught | 4/4 |
| Red-team: entity-swap (lexical blind spot) | documented |
| Red-team: negation (lexical blind spot) | documented |

Run: `python -m evals.run_evals` and `python -m evals.verifier_redteam`

---

## Build status

This repository is being built incrementally, phase by phase. See
`docs/superpowers/specs/` for phase design docs. **Phase 1 (in progress):**
core demo-mode pipeline — FastAPI backend, TF-IDF retriever, demo LLM
composer, lexical verifier, routes for `/`, `/api/health`, `/api/match`,
`/api/moment/{id}`, `/api/ask`. Analytics models, the real frontend,
consistency analyzer, outrage endpoint, real Granite providers, Docling
ingestion, evals, and the Telegram bot are later phases — do not assume
they exist until their phase doc says so.
