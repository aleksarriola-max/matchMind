# Streamlit Rewrite — Design

**Goal:** Replace matchMind's FastAPI + custom HTML/CSS/JS frontend with a
Streamlit app, so it can be deployed for free on Streamlit Community Cloud
the same way PitchMind is — `share.streamlit.io` connected to
`aleksarriola-max/matchMind`, branch `main`, main file `app/main.py`.
Render was the original plan (config already existed) but the user wants
the same hosting path used for their other competition projects.

**Scope:** Full feature parity in one pass — all 6 tabs (Overview, Moments,
Ask MatchMind, Debate, History, Live Replay) — rather than a phased MVP,
per explicit user choice despite the larger one-shot scope.

## What's reused unchanged

`backend/engines/analytics.py`, `consistency.py`, `explainer.py`,
`real_incident.py`, `verifier.py`, `backend/llm/adapter.py`,
`backend/rag/retriever.py` + `ingest.py` — all pure Python, framework-agnostic,
already called as plain functions internally by the old `backend/main.py`.
The Streamlit app calls these same functions directly — no HTTP, no JSON
round-trip. All their existing tests (113 tests) are untouched and remain
the regression safety net.

## What's retired

- `backend/main.py` (FastAPI routing — superseded, nothing else used it)
- `frontend/index.html` (custom single-page app — replaced by `app/`)
- `render.yaml`, `runtime.txt` (Render deployment config — no longer the
  hosting target)
- `tests/test_api.py` (tests FastAPI routes that no longer exist; its
  assertions duplicate what the engine-level tests already cover)

`requirements.txt` drops `fastapi`, `uvicorn`, `pydantic` (only ever used
by the retired `main.py`) and adds `streamlit`. `httpx` stays — used by
`real_incident.py` (StatsBomb fetch) and `adapter.py` (local Ollama calls
for real-Granite mode).

## New file structure

```
app/
  main.py        — entry point: page config, inject CSS, load match data,
                    st.tabs() dispatch to each render_*() below
  styles.py       — ported CSS (background blobs, badges, flags, crest,
                    chat bubbles) as one string, injected once via
                    st.markdown(..., unsafe_allow_html=True)
  components.py   — shared HTML-building helpers ported from the old
                    frontend's JS (flag SVGs, event badge markup,
                    crest+wordmark header, pitch-SVG player circles)
  overview.py     — render_overview(match_data)
  moments.py      — render_moments(match_data)
  ask.py          — render_ask()
  debate.py       — render_debate()   (the "Debate" tab is the Outrage
                    feature — tab label is "Debate", underlying engine
                    call is explainer.outrage())
  history.py      — render_history()
  replay.py       — render_replay(match_data)
```

Each `render_*` function owns one tab's layout and is independently
readable — consistent with the existing codebase's one-module-per-concern
pattern in `backend/engines/`.

## Embedding mechanism — the key technical decision

Two different mechanisms, chosen per element based on whether it needs to
execute JavaScript:

- **Static/visual markup with no JS** (header, score bar, flags, crest,
  event badges, momentum chart SVG, debate/history cards) →
  `st.markdown(html, unsafe_allow_html=True)`. Cheap, inline, no iframe.
- **Toggle-style interactivity** (Decision Lab's sightline/uncertainty-band
  buttons, the real-incident "show" button) → native `st.checkbox` /
  `st.button` driving `st.session_state`, with the SVG markup conditionally
  built in Python and rendered via plain `st.markdown(unsafe_allow_html=True)`
  on each rerun. Streamlit's rerun-on-interaction model handles "toggle and
  re-render" naturally — no client-side JS needed for this, unlike the old
  frontend where every interaction had to be hand-wired in JS.
- **Continuous, time-based interactivity with no Python equivalent**
  (Live Replay's auto-playing timer/narration only) →
  `st.components.v1.html(html, height=...)`. This is the one case that
  genuinely needs a live client-side JS loop, since Streamlit's rerun model
  has no native "advance every N seconds while idle" primitive.

**Live Replay specifically:** stays a single self-contained
`components.v1.html` island. All needed match/moment data is pre-serialized
to JSON and embedded directly in the HTML string (e.g. via
`json.dumps(match_data)` inside an embedded `<script>` block) instead of
`fetch()`-ed at runtime — there's no backend HTTP server anymore. The
existing `setInterval`-based play/pause/narration JS runs essentially
unchanged once it reads from the embedded JSON instead of an API call.

**Ask MatchMind:** the one tab that drops the custom HTML entirely in favor
of native Streamlit (`st.chat_message`, `st.chat_input`, `st.selectbox` for
persona/language). Reasoning: `components.v1.html` is presentation-only —
bridging a form submission from inside that iframe back into Python isn't
a clean pattern, whereas native chat widgets call `explainer.compose_demo`
and `verify` directly with zero plumbing. Per-message badges (verified/
unverified, coverage %) still render as small embedded HTML inside each
`st.chat_message` block, since that's static markup, not interactive JS.

## State

`st.session_state` holds: selected moment id + sightline/uncertainty-band
toggle states (Moments tab), the lazily-fetched real-incident result
(fetched once, cached for the session — same caching intent as the old
in-memory `_cache` in `real_incident.py`, just scoped per Streamlit session
instead of per server process), and the Ask/Debate chat histories (lists of
prior question/answer pairs for `st.chat_message` replay).

## Testing

No new UI test layer — Streamlit apps aren't meaningfully unit-testable the
way FastAPI routes were via `TestClient`. The 113 existing engine-level
tests are unchanged and remain the regression safety net. Verification of
the rewritten UI itself is manual: `streamlit run app/main.py` plus a
browser, the same way the FastAPI version was verified throughout this
session.

## Deployment steps (user-performed, after merge)

1. `git push` the rewrite to `main` (branch renamed from `master` first).
2. share.streamlit.io → sign in with GitHub → New app → select
   `aleksarriola-max/matchMind`, branch `main`, main file `app/main.py`.
3. Streamlit Cloud installs `requirements.txt` and runs the app — public
   by default on the free tier, no login required for viewers.

## Out of scope

- Telegram bot deployment (stays local-only, unrelated to this rewrite).
- Real Granite/Ollama in the cloud (Streamlit Cloud's free tier has no
  local Ollama; the deployed app runs in demo mode, same constraint that
  applied to the Render plan).
- Any new features — this is a like-for-like port of existing behavior to
  a new UI framework, not a redesign.
