# MatchMind — AI Inside the Match

**A human-centered, explainable AI companion that helps anyone understand soccer — tactics, refereeing decisions, momentum, and human performance — before, during, and after the match.**

Built for the IBM Soccer Challenge · Powered by IBM Granite, Docling, and retrieval-grounded explainability.

---

## The problem

The World Cup is the most-watched shared moment on Earth — and the least equally understood. A disallowed goal looks like robbery to one fan and routine to another. A halftime tactical shift decides the match, invisibly. VAR draws a line on a screen and a billion people argue about what it means.

The gap isn't information. It's **explanation**. Broadcasts show *what* happened; almost nothing explains *why* — grounded in the actual Laws of the Game, with honest uncertainty, at the level each fan can absorb.

## What MatchMind does

MatchMind answers any question about a match and shows its work:

- **Decision Lab (signature feature)** — an interactive offside/VAR visualizer: pitch view of the disputed moment, the measured margin, a toggleable **referee's sightline view**, and a **±cm uncertainty band** showing how confident the technology really is.
- **Explainable VAR companion** — every officiating answer cites the specific Law (11, 12, VAR protocol), the evidence, and what remains uncertain.
- **Debate Mode** — controversial calls get both sides: why the call stands *and* the best case against it. Trust through contestability, not authority.
- **Counterfactuals (computed)** — "a 16 ms later run — less than one broadcast frame — and the goal stands." The decision boundary is calculated (margin / sprint speed), not narrated.
- **Persona modes** — the same grounded answer rendered for a beginner, a kid, an analyst, or a journalist; multilingual via Granite.
- **Human-performance lens** — fatigue signatures, pressure responses, and momentum shifts narrated as evidence-backed stories.
- **Calibrated confidence everywhere** — every answer carries a confidence score, its basis, retrieval sources, and full lineage. MatchMind never fakes certainty.
- **Verification agent (hallucination firewall)** — every answer is checked against its own evidence before display; users see "verified" or flagged claims. With Granite connected, a second model pass does the checking.
- **Decision Consistency Analyzer** — compares today's call with real World Cup history (Hand of God 1986, Lampard 2010, Japan's 1.88 mm in 2022) and explains why outcomes differed: rules, technology, or judgment.
- **"Explain my outrage"** — paste your hot take; MatchMind steelmans YOUR side first, then the strongest counter-case. Trust through contestability.
- **Live second-screen mode** — replay the match as a simulated live feed; key moments are explained as they happen.
- **Voice narration + accessibility** — every explanation is listenable (Web Speech), colorblind-safe palette, ARIA-labelled, keyboard-navigable.
- **Telegram bot** (`integrations/telegram_bot.py`) — the whole pipeline in any chat app: no download, low bandwidth, global reach.

What MatchMind deliberately is **not**: a score predictor, a referee replacement, or an opaque analytics box.

## AI / technical approach

```
question --> ROUTE (match-moment router)
         --> GROUND (Docling-built knowledge pack + TF-IDF/vector retrieval
                     over IFAB Laws, VAR protocol, tactics, telemetry)
         --> REASON (IBM Granite: persona-, language-, evidence-aware generation)
         --> EXPLAIN (confidence + basis, sources, uncertainty interval,
                      counterfactual, debate, data lineage)
```

- **IBM Granite** (`ibm/granite-3-3-8b-instruct` on watsonx.ai, or open Granite via Ollama) performs all reasoning and generation. The prompt forces grounding: answer only from retrieved context, cite the law, state uncertainty.
- **Docling** converts the IFAB Laws of the Game, officiating guidance, and tactical references from PDF into the markdown knowledge pack (`backend/rag/ingest.py`).
- **RAG retriever** (`backend/rag/retriever.py`) — dependency-free TF-IDF over chunked sections; swap-in point for watsonx embeddings.
- **Explainability layer** — inspired by IBM's AI Explainability 360 framing: confidence calibration against measurement error, counterfactual explanations, contestable debate views, and end-to-end lineage on every response.
- **Provider adapter** (`backend/llm/adapter.py`) — one env var switches `demo` -> `ollama` -> `watsonx`. The demo composer produces the identical payload shape from the same grounded inputs, so the prototype runs with zero keys.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/main.py
# open http://localhost:8501
```

Runs out of the box in demo mode, so no API keys are needed.

Connect real Granite:

```bash
cp .env.example .env        # add WATSONX_API_KEY + WATSONX_PROJECT_ID
export MATCHMIND_LLM_PROVIDER=watsonx
# or local: ollama pull granite3.3:8b && export MATCHMIND_LLM_PROVIDER=ollama
```

Grow the knowledge pack with Docling:

```bash
pip install docling
python -m backend.rag.ingest Laws_of_the_Game_2025_26.pdf
```

## Analytical depth (the part that isn't a demo trick)

Every number in the UI is **computed, with an error model, and evaluated**:

- **Probabilistic offside model** — the 27' call is treated as statistical inference: Gaussian error propagation over kick-point (sigma ~3.1 cm) and limb-line placement (sigma=2.5 cm) gives P(truly offside) = 99.7%, z = 2.78, 95% CI [3.3, 18.7] cm. Decision probability and explanation confidence are deliberately separated (formulas in `backend/engines/analytics.py`; summary in `CLAUDE.md`).
- **Computed fatigue index** — the "late collapse" is a four-indicator composite (sprint decline, line stretch, long-pass drift, pressing decay) over windowed telemetry, peaking at 65.2 in minutes 75-90. Every component is exposed by `analytics.py` so the weighting is contestable.
- **Reconstructed momentum** — the timeline chart is an event-weighted, exponentially-decayed computation from the raw feed; change the weights in `telemetry.json` and the chart changes. Reproducible and falsifiable.
- **Computed counterfactual & reaction models** — "16 ms later run = level" (margin / sprint speed) and "53 ms ball travel vs 250 ms human reaction = a 4.7x deficit" for the handball. The decision boundary is calculated, with parameters exposed.
- **Evaluated, with published failures** — 75-run golden harness (`python -m evals.run_evals`): routing 100%, retrieval precision@1 100%, MRR 1.0, verification 100%, coverage 1.0, momentum sanity 3/3 (latest run in `evals/results.json`). The harness caught and documents four real bugs during development.
- **Red-teamed verifier** — we attacked our own hallucination firewall (`python -m evals.verifier_redteam`). The lexical demo-mode verifier catches numeric corruption and fabrication but misses entity-swap and negation attacks, a documented blind spot. With Granite running via Ollama, the second entailment pass catches all four attack types (`evals/redteam_results.json`).

## Why it matters for soccer and the World Cup

2026 brings the biggest World Cup ever — 48 teams, 104 matches, billions of viewers, most of them casual. FIFA is already moving toward officiating transparency (semi-automated offside graphics, in-stadium review announcements, referee body-cams). MatchMind extends that movement to every fan's pocket: not *trust us*, but *here is the rule, the evidence, the margin of error, and the strongest case against — decide for yourself*. That is what AI for human understanding should look like.

## Repo map

```
app/                       Streamlit UI (entry point: app/main.py)
  overview.py              match overview + momentum chart
  moments.py               Decision Lab (offside/VAR pitch view) + key moments
  ask.py                   Ask MatchMind chat
  debate.py                Explain-my-outrage / Debate Mode
  history.py               Decision Consistency Analyzer
  replay.py                live second-screen replay
  components.py            HTML/SVG builders (unit-tested)
backend/
  llm/adapter.py           Granite adapter (watsonx | ollama | demo)
  rag/ingest.py            Docling document ingestion
  rag/retriever.py         TF-IDF retrieval over knowledge chunks
  engines/explainer.py     route -> ground -> reason -> explain pipeline
  engines/verifier.py      verification agent (hallucination firewall)
  engines/consistency.py   decision consistency vs World Cup history
  engines/analytics.py     computed models: offside probability, fatigue index, momentum
  data/                    demo fixture, telemetry, historical incidents, knowledge pack
integrations/telegram_bot.py  chat-app front-end (zero extra deps)
evals/                     golden-set harness + red-team, with saved results
tests/                     pytest suite
docs/                      problem statement, demo script, design specs
```

*Demo fixture uses a sample match (Argentina vs France) and demo telemetry; all rule content paraphrases the IFAB Laws of the Game.*

## Build status

All components described above are implemented: the Streamlit app, computed analytics models, verifier, consistency analyzer, Granite providers (watsonx and Ollama), Docling ingestion, evals and the Telegram bot. The pytest suite (129 tests) passes. The app runs in demo mode by default; real Granite answers require watsonx credentials or a local Ollama server. Phase-by-phase design docs are in `docs/superpowers/specs/`.
