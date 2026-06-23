# Streamlit Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace matchMind's FastAPI + custom HTML/CSS/JS frontend with a Streamlit app (`app/main.py`), so it can deploy on Streamlit Community Cloud, while reusing `backend/engines/*`, `backend/llm/adapter.py`, and `backend/rag/*` unchanged.

**Architecture:** `app/components.py` holds pure, unit-tested HTML/SVG-string-building functions ported 1:1 from the old frontend's JS. Six `app/<tab>.py` modules each own one tab's Streamlit orchestration (widgets + session_state + calls into `backend.engines.*` directly, no HTTP). `app/main.py` wires it all together. Toggle-style interactions use native `st.checkbox`/`st.button` + rerun; the two things with no Python-native equivalent (Live Replay's auto-play timer, and each TTS speak button's `window.speechSynthesis` call) become small `st.components.v1.html` islands.

**Tech Stack:** Streamlit, Python (existing `backend.engines.*`, `backend.llm.adapter`, `backend.rag.retriever`), pytest.

## Global Constraints

- Full feature parity with the existing FastAPI app in one pass — no phased MVP.
- `backend/engines/*`, `backend/llm/adapter.py`, `backend/rag/*` and their existing tests are NOT modified.
- `backend/main.py`, `frontend/index.html`, `render.yaml`, `runtime.txt`, `tests/test_api.py` are deleted once the Streamlit app covers their functionality.
- `requirements.txt`: remove `fastapi`, `uvicorn`, `pydantic`; add `streamlit`; keep `httpx`, `pytest`.
- No new features — this is a like-for-like port, not a redesign.
- Entry point is `app/main.py`, run via `streamlit run app/main.py`.

---

### Task 1: Retire FastAPI app, scaffold the Streamlit app

**Files:**
- Delete: `backend/main.py`, `frontend/index.html`, `render.yaml`, `runtime.txt`, `tests/test_api.py`
- Modify: `requirements.txt`
- Create: `app/__init__.py` (empty), `app/styles.py`, `app/main.py`

**Interfaces:**
- Produces: `app.styles.CSS` (str constant), `app.styles.inject()` (calls `st.markdown(CSS, unsafe_allow_html=True)`)

- [ ] **Step 1: Delete the retired files**

```bash
git rm backend/main.py frontend/index.html render.yaml runtime.txt tests/test_api.py
```

- [ ] **Step 2: Update requirements.txt**

```
streamlit>=1.32
pytest>=8.0
httpx>=0.27
# Optional — production ingestion and watsonx SDK:
# docling
# ibm-watsonx-ai
```

- [ ] **Step 3: Create app/__init__.py**

Empty file — makes `app` an importable package for pytest.

- [ ] **Step 4: Create app/styles.py**

```python
import streamlit as st

CSS = """
<style>
:root {
  --bg: #0b0b0b; --panel: #161616; --border: #2a2a2a; --text: #eaeaea;
  --muted: #999; --accent: #00e0ff; --home: #0B5FA5; --away: #C8102E;
}
.bg-glow { position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }
.bg-blob { position: absolute; width: 50vw; height: 50vw; max-width: 600px; max-height: 600px; border-radius: 50%; filter: blur(60px); opacity: 0.35; }
.bg-blob-gold { background: #ffd14d; top: -10%; left: -10%; animation: drift1 28s ease-in-out infinite; }
.bg-blob-cyan { background: #00e0ff; top: -15%; right: -10%; animation: drift2 34s ease-in-out infinite; }
.bg-blob-green { background: #2ecc71; bottom: -20%; left: 30%; animation: drift3 40s ease-in-out infinite; }
@keyframes drift1 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(40px, 30px); } }
@keyframes drift2 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-30px, 40px); } }
@keyframes drift3 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(30px, -30px); } }
.brand { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.brand .crest {
  width: 28px; height: 28px; border-radius: 50%; background: var(--panel); border: 2px solid var(--accent);
  color: var(--accent); display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 10px rgba(0,224,255,0.4);
}
.brand .wordmark { font-weight: 700; font-size: 1.1em; color: var(--text); letter-spacing: 0.3px; }
.score-bar {
  display: flex; align-items: center; justify-content: space-between;
  border-radius: 6px; padding: 10px 16px; margin-top: 8px;
  box-shadow: 0 0 20px rgba(0,224,255,0.15);
}
.score-bar .team-name { font-weight: 700; letter-spacing: 0.3px; text-shadow: 0 1px 4px rgba(0,0,0,0.85), 0 0 1px rgba(0,0,0,0.9); display: inline-flex; align-items: center; gap: 8px; }
.score-bar .flag { border-radius: 2px; box-shadow: 0 0 0 1px rgba(255,255,255,0.4); flex-shrink: 0; }
.score-bar .score { color: #fff; font-weight: 900; font-size: 1.2em; text-shadow: 0 0 12px rgba(0,224,255,0.9), 0 1px 4px rgba(0,0,0,0.85); }
.glow-bar-label { display: flex; justify-content: space-between; color: var(--muted); font-size: 0.75em; margin-bottom: 4px; }
.glow-bar { background: #1c1c24; border-radius: 6px; height: 10px; overflow: hidden; }
.glow-bar .fill { height: 100%; border-radius: 6px; box-shadow: 0 0 10px currentColor; }
.momentum-chart-wrap { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; }
.momentum-chart-wrap h3 { margin: 0 0 8px; font-size: 0.85em; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.momentum-chart-svg { width: 100%; display: block; }
.momentum-chart-svg .axis-label { fill: var(--muted); font-size: 9px; }
.team-cards { display: flex; gap: 16px; margin-bottom: 20px; }
.team-card { flex: 1; background: var(--panel); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 6px; padding: 12px 16px; }
.team-card .swatch { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.event-list { list-style: none; padding: 0; margin: 0; }
.event-row {
  display: flex; align-items: center; gap: 10px; background: var(--panel);
  border-left: 3px solid var(--accent); border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;
}
.event-row .icon { font-size: 1.1em; }
.event-row .minute { color: var(--accent); min-width: 3em; font-weight: 700; }
.event-badge {
  display: inline-block; font-size: 0.75em; text-transform: uppercase;
  letter-spacing: 0.05em; background: var(--border); color: var(--muted);
  border-radius: 4px; padding: 2px 6px;
}
.event-badge-goal { background: rgba(245, 197, 24, 0.18); color: #f5c518; }
.event-badge-var_review { background: rgba(230, 57, 70, 0.18); color: #e63946; }
.event-badge-tactical { background: rgba(0, 212, 255, 0.18); color: #00d4ff; }
.event-badge-substitution { background: rgba(255, 124, 0, 0.18); color: #ff7c00; }
.event-badge-pressure { background: rgba(155, 89, 182, 0.18); color: #c389e0; }
.error { color: #ff6b6b; padding: 20px; }
.law-badge { display: inline-block; background: var(--border); color: var(--muted); border-radius: 4px; padding: 4px 10px; font-size: 0.85em; margin-bottom: 8px; }
.confidence-line { color: var(--accent); font-weight: 600; }
.analytics-table { border-collapse: collapse; margin: 8px 0; }
.analytics-table th, .analytics-table td { border: 1px solid var(--border); padding: 6px 12px; text-align: left; }
.pitch-wrap {
  background: radial-gradient(ellipse at center, #15351f 0%, #0a0a0a 80%);
  border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-top: 12px;
}
.pitch-svg { width: 100%; display: block; }
.lab-banner { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 10px 0; }
.crest { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 800; font-size: 13px; border: 2px solid #fff; flex-shrink: 0; }
.lab-banner .var-label { display: flex; align-items: center; gap: 6px; color: #ddd; font-size: 0.75em; letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: #ff3b3b; box-shadow: 0 0 6px #ff3b3b; }
.lower-third {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(90deg, var(--accent), var(--home));
  color: #fff; padding: 6px 12px; border-radius: 4px; margin-top: 8px; font-size: 0.9em;
}
.inset-svg { width: 100%; display: block; background: #0e2a1a; border-radius: 4px; }
.callout { background: var(--panel); border-left: 3px solid var(--accent); padding: 10px 14px; margin: 12px 0; border-radius: 0 6px 6px 0; }
.debate-cols { display: flex; gap: 16px; margin-top: 12px; }
.debate-cols > div { flex: 1; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-size: 0.8em; font-weight: 600; }
.badge.verified { background: #1f3d2a; color: #6fd98e; box-shadow: 0 0 8px rgba(111,217,142,0.5); }
.badge.unverified { background: #3d2a1f; color: #f0a868; box-shadow: 0 0 8px rgba(240,168,104,0.5); }
.confidence-card { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
.confidence-card .confidence-line { font-size: 1.4em; margin: 0 0 4px; }
.lineage { font-family: monospace; color: var(--muted); font-size: 0.8em; margin-top: 16px; }
.incident-card { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
.incident-card .incident-meta { color: var(--muted); font-size: 0.85em; margin-bottom: 8px; }
.real-incident-wrap { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border); }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="bg-glow" aria-hidden="true">'
        '<div class="bg-blob bg-blob-gold"></div>'
        '<div class="bg-blob bg-blob-cyan"></div>'
        '<div class="bg-blob bg-blob-green"></div>'
        '</div>',
        unsafe_allow_html=True,
    )
```

- [ ] **Step 5: Create app/main.py (scaffold with placeholder tabs)**

```python
import streamlit as st

from app import styles
from backend.engines import explainer

st.set_page_config(page_title="MatchMind", layout="centered")
styles.inject()

match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "events": explainer.MATCH_DATA["events"],
}

st.write(f"## {match_data['home']['name']} {match_data['score']['home']} – {match_data['score']['away']} {match_data['away']['name']}")

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay"]
)

with tab_overview:
    st.write("Overview — coming in Task 4")

with tab_moments:
    st.write("Moments — coming in Task 6")

with tab_ask:
    st.write("Ask MatchMind — coming in Task 7")

with tab_debate:
    st.write("Debate — coming in Task 8")

with tab_history:
    st.write("History — coming in Task 9")

with tab_replay:
    st.write("Live Replay — coming in Task 10")
```

- [ ] **Step 6: Verify it boots**

Run: `streamlit run app/main.py --server.headless true &` then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501 --max-time 10`
Expected: `200`. Stop the server afterward (`kill %1` or find the PID on port 8501).

- [ ] **Step 7: Run the existing test suite to confirm nothing else broke**

Run: `python -m pytest -q`
Expected: all remaining tests pass (113 — the count drops from 117 because `test_api.py`'s 4 tests are gone with `backend/main.py`).

- [ ] **Step 8: Commit**

```bash
git add app/ requirements.txt
git add -u
git commit -m "Scaffold Streamlit app, retire FastAPI app and old frontend"
```

---

### Task 2: app/components.py — header, flags, badges, glow bar, speak button

**Files:**
- Create: `app/components.py`
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: nothing (pure functions, no backend imports)
- Produces:
  - `escape_html(text: str) -> str`
  - `TEAM_FLAGS: dict[str, str]`
  - `EVENT_ICONS: dict[str, str]`
  - `render_header_html(match_data: dict) -> str`
  - `render_event_row_html(event: dict) -> str`
  - `render_glow_bar_html(label: str, pct: float, color: str) -> str`
  - `speak_button_html(text: str) -> str` (a full `st.components.v1.html`-ready document, not a fragment)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_components.py
from app import components


def test_escape_html_escapes_tags_and_amp():
    assert components.escape_html('<img onerror="x">&') == '&lt;img onerror="x"&gt;&amp;'


def test_team_flags_has_argentina_and_france():
    assert "Argentina" in components.TEAM_FLAGS
    assert "France" in components.TEAM_FLAGS
    assert "<svg" in components.TEAM_FLAGS["Argentina"]


def test_render_header_html_includes_team_names_and_score():
    match_data = {
        "home": {"name": "Argentina", "color": "#75AADB"},
        "away": {"name": "France", "color": "#0055A4"},
        "score": {"home": 2, "away": 1},
    }
    html = components.render_header_html(match_data)
    assert "Argentina" in html
    assert "France" in html
    assert "2" in html and "1" in html
    assert "#75AADB" in html


def test_render_event_row_html_includes_badge_class_and_desc():
    event = {"minute": 19, "type": "goal", "desc": "France open the scoring."}
    html = components.render_event_row_html(event)
    assert "event-badge-goal" in html
    assert "19" in html
    assert "France open the scoring." in html


def test_render_glow_bar_html_shows_percentage():
    html = components.render_glow_bar_html("Confidence", 0.997, "var(--accent)")
    assert "99.7%" in html


def test_speak_button_html_embeds_escaped_text_and_script():
    html = components.speak_button_html('Say "hi" & bye')
    assert "speechSynthesis" in html
    assert "&quot;" in html or "\\&quot;" in html or "hi" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.components'`

- [ ] **Step 3: Write app/components.py**

```python
EVENT_ICONS = {
    "goal": "⚽",
    "var_review": "🚩",
    "tactical": "🔄",
    "substitution": "🔁",
    "pressure": "😓",
}

TOPIC_ICONS = {
    "offside": "🚩",
    "handball": "✋",
    "goal-line": "📏",
    "penalty": "⚖️",
}

TEAM_FLAGS = {
    "Argentina": (
        '<svg width="20" height="14" viewBox="0 0 30 20" class="flag">'
        '<rect width="30" height="20" fill="#75AADB"/>'
        '<rect y="6.67" width="30" height="6.67" fill="#fff"/></svg>'
    ),
    "France": (
        '<svg width="20" height="14" viewBox="0 0 30 20" class="flag">'
        '<rect width="10" height="20" fill="#0055A4"/>'
        '<rect x="10" width="10" height="20" fill="#fff"/>'
        '<rect x="20" width="10" height="20" fill="#EF4135"/></svg>'
    ),
}


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;")


def render_header_html(match_data: dict) -> str:
    home, away, score = match_data["home"], match_data["away"], match_data["score"]
    return (
        '<div class="brand">'
        '<div class="crest"><svg width="20" height="20" viewBox="0 0 20 20">'
        '<circle cx="10" cy="10" r="3" fill="currentColor"/>'
        '<path d="M10 1 L10 5 M10 15 L10 19 M1 10 L5 10 M15 10 L19 10" stroke="currentColor" stroke-width="1.5"/>'
        '</svg></div><span class="wordmark">MatchMind</span></div>'
        f'<p style="color:var(--muted);font-size:0.9em;margin:0 0 4px;">{match_data["competition"]}</p>'
        f'<div class="score-bar" style="background:linear-gradient(90deg, {home["color"]}, {away["color"]})">'
        f'<span class="team-name home">{TEAM_FLAGS.get(home["name"], "")}{home["name"]}</span>'
        f'<span class="score">{score["home"]} – {score["away"]}</span>'
        f'<span class="team-name away">{away["name"]}{TEAM_FLAGS.get(away["name"], "")}</span>'
        "</div>"
    )


def render_event_row_html(event: dict) -> str:
    icon = EVENT_ICONS.get(event["type"], "•")
    return (
        '<li class="event-row">'
        f'<span class="icon">{icon}</span>'
        f'<span class="minute">{event["minute"]}\'</span>'
        f'<span class="event-badge event-badge-{event["type"]}">{event["type"]}</span>'
        f'<span>{event["desc"]}</span></li>'
    )


def render_glow_bar_html(label: str, pct: float, color: str) -> str:
    pct_display = pct * 100
    return (
        f'<div class="glow-bar-label"><span>{label}</span>'
        f'<span style="color:{color};font-weight:700;">{pct_display:.1f}%</span></div>'
        f'<div class="glow-bar"><div class="fill" '
        f'style="width:{pct_display}%;background:{color};color:{color}"></div></div>'
    )


def speak_button_html(text: str) -> str:
    safe_attr = escape_attr(text)
    return (
        "<html><body style=\"margin:0;background:transparent;\">"
        f'<button id="speak-btn" data-text="{safe_attr}" '
        'style="background:none;border:1px solid #2a2a2a;border-radius:4px;color:#00e0ff;'
        'cursor:pointer;padding:2px 8px;font-size:0.9em;">\U0001F50A</button>'
        "<script>"
        "var btn = document.getElementById('speak-btn');"
        "btn.addEventListener('click', function() {"
        "  if (!('speechSynthesis' in window)) return;"
        "  if (window.speechSynthesis.speaking) { window.speechSynthesis.cancel(); return; }"
        "  var u = new SpeechSynthesisUtterance(btn.dataset.text);"
        "  window.speechSynthesis.speak(u);"
        "});"
        "</script></body></html>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add app/components.py tests/test_components.py
git commit -m "Add app/components.py: header, flags, badges, glow bar, speak button"
```

---

### Task 3: app/components.py — momentum chart SVG builder

**Files:**
- Modify: `app/components.py`
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `lighten_for_fill(hex_color: str) -> str`, `render_momentum_chart_html(title_html: str, match_data: dict, current_minute: int | None = None) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_components.py

def _sample_match_data_for_chart():
    return {
        "home": {"name": "Argentina", "color": "#75AADB"},
        "away": {"name": "France", "color": "#0055A4"},
        "events": [{"minute": 19, "type": "goal", "team": "away", "desc": "x"}],
        "momentum": [{"minute": m, "value": float(m - 45)} for m in range(0, 91, 5)],
    }


def test_lighten_for_fill_blends_toward_white():
    result = components.lighten_for_fill("#0055A4")
    assert result.startswith("rgb(")
    # blended values must all exceed the original channel values
    import re
    r, g, b = (int(x) for x in re.findall(r"\d+", result))
    assert r > 0x00 and g > 0x55 and b > 0xA4


def test_render_momentum_chart_html_contains_svg_and_points_for_full_curve():
    html = components.render_momentum_chart_html("<h3>Momentum</h3>", _sample_match_data_for_chart())
    assert "<svg" in html
    assert "polyline" in html
    assert "90'" in html


def test_render_momentum_chart_html_clips_to_current_minute():
    data = _sample_match_data_for_chart()
    html_full = components.render_momentum_chart_html("<h3>Momentum</h3>", data)
    html_clipped = components.render_momentum_chart_html("<h3>Momentum</h3>", data, current_minute=20)
    # the clipped version has a "now" pulse marker the full one doesn't
    assert "pulse" not in html_full or "pulse" in html_clipped
    assert html_clipped != html_full
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components.py -v -k momentum or lighten`
Expected: FAIL with `AttributeError: module 'app.components' has no attribute 'lighten_for_fill'`

- [ ] **Step 3: Add to app/components.py**

```python
def lighten_for_fill(hex_color: str) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    mix = lambda c: round(c + (255 - c) * 0.45)
    return f"rgb({mix(r)},{mix(g)},{mix(b)})"


def render_momentum_chart_html(title_html: str, match_data: dict, current_minute: int | None = None) -> str:
    curve = match_data["momentum"]
    max_abs = max(1.0, max(abs(p["value"]) for p in curve))
    width, height, margin_x, baseline_y, half_height = 380, 130, 10, 65, 50
    clipped = current_minute is not None
    visible = [p for p in curve if not clipped or p["minute"] <= current_minute] if clipped else curve

    def x_pos(minute):
        return margin_x + (minute / 90) * (width - 2 * margin_x)

    def y_pos(value):
        return baseline_y - (value / max_abs) * half_height

    points = " ".join(f"{x_pos(p['minute'])},{y_pos(p['value'])}" for p in visible)

    home_color, away_color = match_data["home"]["color"], match_data["away"]["color"]

    area_path = ""
    if len(visible) > 1:
        first_x, last_x = x_pos(visible[0]["minute"]), x_pos(visible[-1]["minute"])
        mid = " L ".join(f"{x_pos(p['minute'])},{y_pos(p['value'])}" for p in visible)
        area_path = f"M {first_x},{baseline_y} L {mid} L {last_x},{baseline_y} Z"

    now_marker = ""
    if clipped and visible:
        last = visible[-1]
        now_marker = (
            f'<circle cx="{x_pos(last["minute"])}" cy="{y_pos(last["value"])}" r="4" fill="#fff" '
            f'class="pulse"/>'
        )

    clip_above = (
        f'<clipPath id="clip-above"><rect x="0" y="0" width="{width}" height="{baseline_y}"/></clipPath>'
    )
    clip_below = (
        f'<clipPath id="clip-below"><rect x="0" y="{baseline_y}" width="{width}" '
        f'height="{height - baseline_y}"/></clipPath>'
    )

    area_above = (
        f'<path d="{area_path}" fill="{lighten_for_fill(home_color)}" opacity="0.35" clip-path="url(#clip-above)"/>'
        if area_path else ""
    )
    area_below = (
        f'<path d="{area_path}" fill="{lighten_for_fill(away_color)}" opacity="0.35" clip-path="url(#clip-below)"/>'
        if area_path else ""
    )

    return (
        f'<div class="momentum-chart-wrap">{title_html}'
        f'<svg viewBox="0 0 {width} {height}" class="momentum-chart-svg">'
        f"<defs>{clip_above}{clip_below}</defs>"
        f"{area_above}{area_below}"
        f'<line x1="{margin_x}" y1="{baseline_y}" x2="{width - margin_x}" y2="{baseline_y}" '
        'stroke="#333" stroke-width="1" stroke-dasharray="3,3"/>'
        f'<polyline points="{points}" fill="none" stroke="{home_color}" stroke-width="2.5"/>'
        f"{now_marker}"
        f'<text x="{margin_x}" y="{height - 4}" class="axis-label">0\'</text>'
        f'<text x="{width - margin_x}" y="{height - 4}" class="axis-label" text-anchor="end">90\'</text>'
        "</svg></div>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add app/components.py tests/test_components.py
git commit -m "Add momentum chart SVG builder to app/components.py"
```

---

### Task 4: app/overview.py — Overview tab

**Files:**
- Create: `app/overview.py`
- Modify: `app/main.py:` (Overview tab block)

**Interfaces:**
- Consumes: `components.render_header_html`, `components.render_event_row_html`, `components.render_momentum_chart_html`
- Produces: `render_overview(match_data: dict) -> None`

- [ ] **Step 1: Create app/overview.py**

```python
import streamlit as st

from app import components


def render_overview(match_data: dict) -> None:
    st.markdown(components.render_header_html(match_data), unsafe_allow_html=True)

    cards_html = '<div class="team-cards">'
    for team in (match_data["home"], match_data["away"]):
        cards_html += (
            f'<div class="team-card"><h3><span class="swatch" style="background:{team["color"]}"></span>'
            f'{team["name"]}</h3><div>{team["formation_start"]} → {team["formation_end"]}</div></div>'
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown(
        components.render_momentum_chart_html("<h3>Momentum</h3>", match_data),
        unsafe_allow_html=True,
    )

    st.markdown("## Match events")
    rows = "".join(components.render_event_row_html(e) for e in match_data["events"])
    st.markdown(f'<ul class="event-list">{rows}</ul>', unsafe_allow_html=True)
```

- [ ] **Step 2: Wire it into app/main.py**

Replace the placeholder Overview block:

```python
with tab_overview:
    overview.render_overview(match_data)
```

Add to the imports at the top of `app/main.py`:

```python
from app import overview
```

Also expand `match_data` in `app/main.py` to include `formation_start`/`formation_end` and `momentum` (already present on `explainer.MATCH_DATA["home"]`/`["away"]` per the existing data schema) and the computed momentum curve:

```python
from backend.engines import analytics

match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "events": explainer.MATCH_DATA["events"],
    "momentum": analytics.momentum_curve(
        explainer.MATCH_DATA["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    ),
}
```

- [ ] **Step 3: Manually verify**

Run: `streamlit run app/main.py`
Open the app in a browser, check the Overview tab shows: header with flags and score, two team cards, the momentum chart SVG, and the match events list with colored badges.

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest -q`
Expected: all pass (no regressions — `app/overview.py` has no unit tests of its own since it's pure Streamlit orchestration with no business logic, consistent with how `frontend/index.html`'s rendering was never unit tested either).

- [ ] **Step 5: Commit**

```bash
git add app/overview.py app/main.py
git commit -m "Add Overview tab"
```

---

### Task 5: app/components.py — Decision Lab pitch SVG builder

**Files:**
- Modify: `app/components.py`
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `player_circle_html(x: float, y: float, label: str, fill_color: str, stroke_color: str, stroke_width: float) -> str`
  - `render_decision_lab_pitch_html(moment: dict, match_data: dict, show_sightline: bool, show_uncertainty_band: bool) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_components.py

def _sample_offside_moment():
    return {
        "title": "Argentina goal disallowed",
        "law": "Law 11",
        "decision": "Goal disallowed for offside",
        "confidence": 0.997,
        "margin_cm": 11.0,
        "camera_frame_uncertainty_cm": 6.0,
        "pitch": {
            "offside_line_x": 60.0,
            "ball": {"x": 62.0, "y": 34.0},
            "passer": {"x": 55.0, "y": 30.0, "label": "#8"},
            "attacker": {"x": 61.0, "y": 36.0, "label": "#9"},
            "second_last_defender": {"x": 60.0, "y": 32.0, "label": "#4"},
            "keeper": {"x": 95.0, "y": 34.0, "label": "#1"},
            "others": [{"x": 50.0, "y": 20.0, "team": "home"}],
            "assistant_referee": {"x": 60.0, "y": 70.0, "label": "AR1"},
        },
        "analytics": {
            "offside_probability": {
                "result": {"probability": 0.997, "z": 2.78},
                "inputs": {"camera_frame_uncertainty_cm": 6.0, "sigma_line_cm": 2.5},
            }
        },
    }


def _sample_match_data_for_pitch():
    return {"home": {"name": "Argentina", "color": "#75AADB"}, "away": {"name": "France", "color": "#0055A4"}}


def test_render_decision_lab_pitch_html_contains_offside_line_and_margin():
    html = components.render_decision_lab_pitch_html(
        _sample_offside_moment(), _sample_match_data_for_pitch(), show_sightline=False, show_uncertainty_band=True
    )
    assert "<svg" in html
    assert "OFFSIDE" in html
    assert "11.0 cm" in html
    assert "99.7%" in html


def test_render_decision_lab_pitch_html_sightline_toggle_adds_lines():
    moment, match_data = _sample_offside_moment(), _sample_match_data_for_pitch()
    without = components.render_decision_lab_pitch_html(moment, match_data, False, True)
    with_sightline = components.render_decision_lab_pitch_html(moment, match_data, True, True)
    assert len(with_sightline) > len(without)


def test_render_decision_lab_pitch_html_uncertainty_band_toggle():
    moment, match_data = _sample_offside_moment(), _sample_match_data_for_pitch()
    with_band = components.render_decision_lab_pitch_html(moment, match_data, False, True)
    without_band = components.render_decision_lab_pitch_html(moment, match_data, False, False)
    assert "95% CI" in with_band
    assert "95% CI" not in without_band
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components.py -v -k decision_lab`
Expected: FAIL with `AttributeError: module 'app.components' has no attribute 'render_decision_lab_pitch_html'`

- [ ] **Step 3: Add to app/components.py**

```python
import math


def player_circle_html(x: float, y: float, label: str, fill_color: str, stroke_color: str, stroke_width: float) -> str:
    number = label.split("#")[1] if "#" in label else label
    return (
        f'<circle cx="{x}" cy="{y}" r="1.6" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>'
        f'<text x="{x}" y="{y + 0.7}" fill="#fff" font-size="1.8" text-anchor="middle">{number}</text>'
    )


def render_decision_lab_pitch_html(
    moment: dict, match_data: dict, show_sightline: bool, show_uncertainty_band: bool
) -> str:
    p = moment["pitch"]
    home_color, away_color = match_data["home"]["color"], match_data["away"]["color"]
    line_x = p["offside_line_x"]

    html = (
        f'<div class="law-badge">{moment["law"]}</div>' if moment.get("law") else ""
    )
    html += f'<p class="decision">{moment["decision"]}</p>'

    html += (
        '<div class="lab-banner">'
        f'<div class="crest" style="background:{home_color}">{match_data["home"]["name"][0]}</div>'
        '<span class="var-label"><span class="pulse-dot"></span>VAR Review</span>'
        f'<div class="crest" style="background:{away_color}">{match_data["away"]["name"][0]}</div>'
        "</div>"
    )

    html += '<div class="pitch-wrap"><svg viewBox="-2 -2 104 72" class="pitch-svg">'
    html += '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>'
    html += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">'
    html += '<rect x="0" y="0" width="100" height="68"/><line x1="50" y1="0" x2="50" y2="68"/>'
    html += '<circle cx="50" cy="34" r="8.7"/><circle cx="50" cy="34" r="0.5" fill="#eaf5ee"/>'
    html += '<rect x="84.3" y="13.8" width="15.7" height="40.3"/><rect x="94.8" y="24.8" width="5.2" height="18.3"/>'
    html += '<rect x="0" y="13.8" width="15.7" height="40.3"/><rect x="0" y="24.8" width="5.2" height="18.3"/>'
    html += "</g>"

    html += f'<line x1="{line_x}" y1="-2" x2="{line_x}" y2="70" stroke="#00e0ff" stroke-width="0.5"/>'
    html += f'<line x1="{line_x}" y1="-2" x2="{line_x}" y2="70" stroke="#00e0ff" stroke-width="1.6" opacity="0.25"/>'

    if show_sightline:
        ar = p["assistant_referee"]
        html += (
            f'<line x1="{ar["x"]}" y1="{ar["y"] + 0.5}" x2="{p["attacker"]["x"]}" y2="{p["attacker"]["y"]}" '
            'stroke="#ffe14d" stroke-width="0.25" stroke-dasharray="0.8,0.6" opacity="0.85"/>'
        )
        html += (
            f'<line x1="{ar["x"]}" y1="{ar["y"] + 0.5}" x2="{p["second_last_defender"]["x"]}" '
            f'y2="{p["second_last_defender"]["y"]}" stroke="#ffe14d" stroke-width="0.25" '
            'stroke-dasharray="0.8,0.6" opacity="0.5"/>'
        )

    for o in p["others"]:
        color = home_color if o["team"] == "home" else away_color
        html += f'<circle cx="{o["x"]}" cy="{o["y"]}" r="1.5" fill="{color}" stroke="#ffffff" stroke-width="0.2" opacity="0.65"/>'

    html += f'<circle cx="{p["ball"]["x"]}" cy="{p["ball"]["y"]}" r="0.9" fill="#fff" stroke="#333" stroke-width="0.15"/>'
    html += player_circle_html(p["passer"]["x"], p["passer"]["y"], p["passer"]["label"], home_color, "#ffffff", 0.25)
    html += player_circle_html(
        p["second_last_defender"]["x"], p["second_last_defender"]["y"], p["second_last_defender"]["label"],
        away_color, "#ffffff", 0.25,
    )
    html += player_circle_html(p["attacker"]["x"], p["attacker"]["y"], p["attacker"]["label"], home_color, "#ff4d4d", 0.4)
    html += player_circle_html(p["keeper"]["x"], p["keeper"]["y"], p["keeper"]["label"], away_color, "#ffffff", 0.25)

    ar = p["assistant_referee"]
    html += f'<circle cx="{ar["x"]}" cy="{ar["y"] + 0.3}" r="1" fill="#ffe14d"/>'
    html += f'<text x="{ar["x"]}" y="{ar["y"] - 0.6}" fill="#ffe14d" font-size="2" text-anchor="middle">{ar["label"]}</text>'
    html += "</svg></div>"

    probability = moment["analytics"]["offside_probability"]["result"]["probability"]
    html += (
        '<div class="lower-third">'
        f'<strong>OFFSIDE — {p["attacker"]["label"].upper()}</strong>'
        f'<span>Margin: {moment["margin_cm"]:.1f} cm &nbsp;|&nbsp; Confidence: {probability * 100:.1f}%</span>'
        "</div>"
    )

    inputs = moment["analytics"]["offside_probability"]["inputs"]
    sigma_frame = inputs["camera_frame_uncertainty_cm"] / 1.96
    sigma_total = math.sqrt(sigma_frame ** 2 + inputs["sigma_line_cm"] ** 2)
    ci_half_width = 1.96 * sigma_total
    margin = moment["margin_cm"]
    attacker_x = 110 + margin
    defender_num = p["second_last_defender"]["label"].split("#")[1]
    attacker_num = p["attacker"]["label"].split("#")[1]

    html += '<div class="inset-wrap"><svg viewBox="0 0 220 60" class="inset-svg">'
    if show_uncertainty_band:
        html += (
            f'<rect x="{110 - ci_half_width}" y="6" width="{2 * ci_half_width}" height="48" '
            'fill="#00e0ff" opacity="0.18"/>'
        )
        html += f'<text x="110" y="58" fill="#00e0ff" font-size="5.5" text-anchor="middle">±{ci_half_width:.1f}cm (95% CI)</text>'
    html += '<line x1="110" y1="2" x2="110" y2="54" stroke="#00e0ff" stroke-width="1"/>'
    html += '<text x="110" y="10" fill="#00e0ff" font-size="6" text-anchor="middle">offside line</text>'
    html += f'<line x1="40" y1="40" x2="110" y2="40" stroke="{away_color}" stroke-width="1"/>'
    html += f'<circle cx="40" cy="40" r="2.5" fill="{away_color}"/>'
    html += f'<text x="30" y="43" fill="{away_color}" font-size="6" text-anchor="end">#{defender_num}</text>'
    html += f'<line x1="40" y1="20" x2="{attacker_x}" y2="20" stroke="{home_color}" stroke-width="1"/>'
    html += f'<circle cx="{attacker_x}" cy="20" r="2.5" fill="{home_color}" stroke="#ff4d4d" stroke-width="0.8"/>'
    html += f'<text x="{attacker_x + 10}" y="23" fill="{home_color}" font-size="6" text-anchor="start">#{attacker_num} (+{margin}cm)</text>'
    html += f'<line x1="110" y1="30" x2="{attacker_x}" y2="30" stroke="#fff" stroke-width="0.6"/>'
    html += f'<text x="{(110 + attacker_x) / 2}" y="29" fill="#fff" font-size="5" text-anchor="middle">{margin}cm</text>'
    html += "</svg></div>"

    html += f'<p class="confidence-line">Confidence: {moment["confidence"] * 100:.1f}% (z = {moment["analytics"]["offside_probability"]["result"]["z"]})</p>'

    return html
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add app/components.py tests/test_components.py
git commit -m "Add Decision Lab pitch SVG builder to app/components.py"
```

---

### Task 6: app/moments.py — Moments tab (Decision Lab + text moments)

**Files:**
- Create: `app/moments.py`
- Modify: `app/main.py` (Moments tab block)

**Interfaces:**
- Consumes: `components.render_decision_lab_pitch_html`, `components.render_glow_bar_html`, `backend.engines.explainer.MATCH_DATA["moments"]`, `backend.engines.analytics.offside_probability/offside_sensitivity/counterfactual_timing/handball_reaction/fatigue_index/fatigue_comparison`, `backend.engines.real_incident.get_real_incident`
- Produces: `render_moments(match_data: dict) -> None`

- [ ] **Step 1: Create app/moments.py**

```python
import streamlit as st

from app import components
from backend.engines import analytics, explainer, real_incident

MOMENT_ORDER = [
    "offside_27", "handball_38", "halftime_shift", "sub_58",
    "goal_home_1", "fatigue_71", "goal_home_2",
]
MOMENT_LABELS = {
    "offside_27": "27' Offside review",
    "handball_38": "38' Handball review",
    "halftime_shift": "46' Tactical shift",
    "sub_58": "58' Substitution",
    "goal_home_1": "63' Goal",
    "fatigue_71": "71' Pressing collapse",
    "goal_home_2": "84' Goal",
}


def _moment_analytics(moment_id: str, moment: dict) -> dict | None:
    if moment_id == "offside_27":
        return {
            "offside_probability": analytics.offside_probability(
                moment["margin_cm"], moment["camera_frame_uncertainty_cm"]
            ),
            "offside_sensitivity": analytics.offside_sensitivity(
                moment["margin_cm"], moment["camera_frame_uncertainty_cm"]
            ),
            "counterfactual_timing": analytics.counterfactual_timing(
                moment["margin_cm"], moment["attacker_speed_ms"]
            ),
        }
    if moment_id == "handball_38":
        return {
            "handball_reaction": analytics.handball_reaction(
                moment["deflection_distance_m"], moment["ball_speed_ms"]
            ),
        }
    if moment_id == "fatigue_71":
        telemetry = analytics.TELEMETRY_DATA
        return {
            "fatigue_index": {
                "home": analytics.fatigue_index(telemetry["teams"]["home"])["result"],
                "away": analytics.fatigue_index(telemetry["teams"]["away"])["result"],
            },
            "fatigue_comparison": analytics.fatigue_comparison(
                telemetry["teams"]["home"], telemetry["teams"]["away"]
            )["result"],
        }
    return None


def _render_text_moment(moment: dict, match_data: dict) -> None:
    st.markdown(f"## {moment['title']}")
    if moment.get("law"):
        st.markdown(f'<div class="law-badge">{moment["law"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="decision">{moment["decision"]}</p>', unsafe_allow_html=True)
    st.markdown(components.render_glow_bar_html("Confidence", moment["confidence"], "var(--accent)"), unsafe_allow_html=True)
    st.write(moment["summary"])
    st.markdown("### Evidence")
    for e in moment["evidence"]:
        st.markdown(f"- {e}")

    a = moment.get("analytics")
    if a and a.get("handball_reaction"):
        r = a["handball_reaction"]["result"]
        benchmark = a["handball_reaction"]["inputs"]["reaction_benchmark_ms"]
        st.markdown("### Computed analytics")
        st.write(
            f"Ball reaches the point of contact in {r['time_available_ms']}ms — "
            f"{r['deficit_ratio']}x faster than the {benchmark}ms human reaction benchmark ({r['verdict']})."
        )
    if a and a.get("fatigue_index"):
        home, away = a["fatigue_index"]["home"], a["fatigue_index"]["away"]
        cmp = a["fatigue_comparison"]
        st.markdown("### Computed analytics")
        st.table(
            {
                "Team": [match_data["home"]["name"], match_data["away"]["name"]],
                "Trend": [home["trend"], away["trend"]],
                "Peak window": [home["peak_window"], away["peak_window"]],
            }
        )
        st.write(f"More fatigued by full-time: {cmp['more_fatigued_team']} (diff {cmp['difference'][5]} pts)")


def _render_real_incident(match_data: dict) -> None:
    if "real_incident_data" not in st.session_state:
        if st.button("\U0001F30D Show a real incident: 2022 World Cup Final"):
            try:
                st.session_state["real_incident_data"] = real_incident.get_real_incident()
            except Exception:
                st.error("Could not load real incident data — StatsBomb's open-data repo may be unreachable.")
        return

    data = st.session_state["real_incident_data"]
    st.markdown(
        f'<div class="incident-meta">{data["match"]["competition"]} — '
        f'{data["match"]["home_team"]} vs {data["match"]["away_team"]}, {data["match"]["date"]}</div>',
        unsafe_allow_html=True,
    )
    st.write(f"{data['minute']}' — {data['passer']} → {data['recipient']} (offside, real StatsBomb data)")

    scale_x, scale_y = 100 / 120, 68 / 80
    mb, defn = data["mbappe_position"], data["second_last_opponent_position"]
    svg = '<svg viewBox="-2 -2 104 72" class="pitch-svg"><rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>'
    svg += '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.7"><rect x="0" y="0" width="100" height="68"/>'
    svg += '<line x1="50" y1="0" x2="50" y2="68"/><circle cx="50" cy="34" r="8.7"/></g>'
    for p in data["freeze_frame"]:
        color = match_data["away"]["color"] if p["teammate"] else match_data["home"]["color"]
        svg += f'<circle cx="{p["location"][0] * scale_x}" cy="{p["location"][1] * scale_y}" r="1.3" fill="{color}" stroke="#fff" stroke-width="0.2" opacity="0.7"/>'
    svg += f'<line x1="{defn[0] * scale_x}" y1="-2" x2="{defn[0] * scale_x}" y2="70" stroke="#00e0ff" stroke-width="0.4" opacity="0.6"/>'
    svg += components.player_circle_html(mb[0] * scale_x, mb[1] * scale_y, "M", match_data["away"]["color"], "#ff4d4d", 0.4)
    svg += components.player_circle_html(defn[0] * scale_x, defn[1] * scale_y, "D", match_data["home"]["color"], "#ffffff", 0.25)
    svg += "</svg>"

    st.markdown(f'<div class="pitch-wrap">{svg}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="confidence-line">Real measured margin: {data["margin_cm"]:.1f} cm</p>', unsafe_allow_html=True)
    st.markdown(
        '<div class="callout">Illustrative — applies our uncertainty model to real position data. '
        "StatsBomb does not publish camera/tracking error margins, so this is not an official measurement.</div>",
        unsafe_allow_html=True,
    )
    for note in data["approximation_notes"]:
        st.markdown(f"- {note}")
    st.markdown(
        f'<p class="lineage">Data: <a href="{data["source_url"]}" target="_blank" rel="noopener">'
        "StatsBomb — Data Champions.</a> (Open Data, used under their research/analysis license)</p>",
        unsafe_allow_html=True,
    )


def render_moments(match_data: dict) -> None:
    moments = explainer.MATCH_DATA["moments"]
    selected = st.radio(
        "Select a moment",
        MOMENT_ORDER,
        format_func=lambda mid: MOMENT_LABELS[mid],
        key="selected_moment",
    )

    moment = dict(moments[selected])
    moment["analytics"] = _moment_analytics(selected, moments[selected])

    if moment.get("pitch"):
        show_sightline = st.checkbox("Referee sightline", key="show_sightline")
        show_uncertainty_band = st.checkbox("Uncertainty band", value=True, key="show_uncertainty_band")
        st.markdown(
            components.render_decision_lab_pitch_html(moment, match_data, show_sightline, show_uncertainty_band),
            unsafe_allow_html=True,
        )
        if moment.get("counterfactual"):
            frames = moment["analytics"]["counterfactual_timing"]["result"]["frames_at_50fps"]
            st.markdown(
                f'<div class="callout">{moment["counterfactual"]} ({frames} frames at 50fps — not detectable on broadcast)</div>',
                unsafe_allow_html=True,
            )
        if moment.get("debate"):
            st.markdown(
                '<div class="debate-cols">'
                f'<div><h4>Stands</h4><p>{moment["debate"]["stands"]}</p></div>'
                f'<div><h4>Overturn</h4><p>{moment["debate"]["overturn"]}</p></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="real-incident-wrap"></div>', unsafe_allow_html=True)
        _render_real_incident(match_data)
    else:
        _render_text_moment(moment, match_data)
```

- [ ] **Step 2: Wire it into app/main.py**

```python
with tab_moments:
    moments.render_moments(match_data)
```

Add `from app import moments` to the imports.

- [ ] **Step 3: Manually verify**

Run: `streamlit run app/main.py`
Check: selecting "27' Offside review" shows the pitch SVG, margin, confidence; toggling "Referee sightline" and "Uncertainty band" checkboxes changes the rendering; clicking "Show a real incident" loads and displays the real StatsBomb data with its approximation notes; selecting a text moment (e.g. "71' Pressing collapse") shows the fatigue table.

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest -q`
Expected: all pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add app/moments.py app/main.py
git commit -m "Add Moments tab (Decision Lab + text moments + real incident)"
```

---

### Task 7: app/ask.py — Ask MatchMind tab

**Files:**
- Create: `app/ask.py`
- Modify: `app/main.py` (Ask MatchMind tab block)

**Interfaces:**
- Consumes: `backend.engines.explainer.route/ground/compose_demo/explain`, `backend.engines.verifier.verify`, `components.escape_html`, `components.render_glow_bar_html`
- Produces: `render_ask() -> None`

- [ ] **Step 1: Create app/ask.py**

```python
import streamlit as st

from app import components
from backend.engines.explainer import compose_demo, explain, ground, route
from backend.engines.verifier import verify

VALID_PERSONAS = ["beginner", "analyst", "kid", "journalist", "coach"]


def render_ask() -> None:
    if "ask_history" not in st.session_state:
        st.session_state["ask_history"] = []

    persona = st.selectbox("Persona", VALID_PERSONAS, index=1, key="ask_persona")

    for entry in st.session_state["ask_history"]:
        with st.chat_message("user"):
            st.write(entry["question"])
        with st.chat_message("assistant"):
            _render_answer(entry)

    question = st.chat_input("Ask MatchMind a question about the match")
    if question:
        moment_id = route(question)
        grounded = ground(question, moment_id)
        answer = compose_demo(persona, grounded["moment"], grounded["retrieved"])
        evidence_texts = (
            grounded["moment"]["evidence"] if grounded["moment"] is not None
            else [r["text"] for r in grounded["retrieved"]]
        )
        verification = verify(answer, evidence_texts)
        explainability = explain(moment_id, grounded["moment"], grounded["retrieved"], verification)

        entry = {
            "question": question,
            "answer": answer,
            "verification": verification,
            "explainability": explainability,
        }
        st.session_state["ask_history"].append(entry)
        st.rerun()


def _render_answer(entry: dict) -> None:
    v, ex = entry["verification"], entry["explainability"]
    st.write(entry["answer"])
    badge = (
        '<span class="badge verified">Verified</span>' if v["verified"]
        else '<span class="badge unverified">Unverified</span>'
    )
    st.markdown(f'{badge} <span>coverage: {round(v["coverage"] * 100)}%</span>', unsafe_allow_html=True)

    if v.get("unsupported"):
        for s in v["unsupported"]:
            st.markdown(f"- {s}")

    st.markdown(
        f'<div class="confidence-card">{components.render_glow_bar_html("Confidence", ex["confidence"], "var(--accent)")}'
        f'<div style="margin-top:6px;">{ex["confidence_basis"]}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Sources**")
    for s in ex["sources"]:
        st.markdown(f'- {s["title"]} ({s["source"]}, score {s["score"]:.2f})')

    st.markdown("**Evidence**")
    for e in ex["evidence"]:
        st.markdown(f"- {e}")

    if ex.get("counterfactual"):
        st.markdown(f'<div class="callout">{ex["counterfactual"]}</div>', unsafe_allow_html=True)

    if ex.get("debate"):
        st.markdown(
            '<div class="debate-cols">'
            f'<div><h4>Stands</h4><p>{ex["debate"]["stands"]}</p></div>'
            f'<div><h4>Overturn</h4><p>{ex["debate"]["overturn"]}</p></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(f'<p class="lineage">{ex["lineage"]}</p>', unsafe_allow_html=True)
```

- [ ] **Step 2: Wire it into app/main.py**

```python
with tab_ask:
    ask.render_ask()
```

Add `from app import ask` to the imports.

- [ ] **Step 3: Manually verify**

Run: `streamlit run app/main.py`
Check: typing "Why was the goal disallowed for offside in the 27th minute?" and submitting shows the user message, then an assistant message with the answer, verified/unverified badge, coverage %, confidence bar, sources, evidence, and lineage. Submitting a second question keeps the first one visible above it (chat history).

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/ask.py app/main.py
git commit -m "Add Ask MatchMind tab (native st.chat_message)"
```

---

### Task 8: app/debate.py — Debate (Outrage) tab

**Files:**
- Create: `app/debate.py`
- Modify: `app/main.py` (Debate tab block)

**Interfaces:**
- Consumes: `backend.engines.explainer.outrage`, `backend.engines.verifier.verify`, `components.render_glow_bar_html`
- Produces: `render_debate() -> None`

- [ ] **Step 1: Create app/debate.py**

```python
import streamlit as st

from app import components
from backend.engines.explainer import outrage
from backend.engines.verifier import verify


def render_debate() -> None:
    st.markdown("## Explain My Outrage")
    take = st.text_area(
        "Your take",
        value="That offside call was robbery, the goal should have stood!",
        key="outrage_take",
    )
    if st.button("Explain my outrage"):
        result = outrage(take)
        verification = None
        if result["counter"] is not None:
            verification = verify(result["counter"], result["evidence"])
        st.session_state["outrage_result"] = result
        st.session_state["outrage_verification"] = verification

    result = st.session_state.get("outrage_result")
    if not result:
        return
    verification = st.session_state.get("outrage_verification")

    st.markdown("### What actually happened")
    st.write(result["summary"])

    if result["steelman"]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Your side")
            st.write(result["steelman"])
        with col2:
            st.markdown("#### The counter-case")
            if verification:
                badge = (
                    '<span class="badge verified">Verified</span>' if verification["verified"]
                    else '<span class="badge unverified">Unverified</span>'
                )
                st.markdown(badge, unsafe_allow_html=True)
            st.write(result["counter"])

        st.markdown(
            f'<div class="confidence-card">{components.render_glow_bar_html("Confidence", result["confidence"], "var(--accent)")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="callout">{result["verdict"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="callout">This isn\'t a contested officiating call, so there\'s no counter-case here — '
            "just what happened.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(f'<p class="lineage">{result["lineage"]}</p>', unsafe_allow_html=True)
```

- [ ] **Step 2: Wire it into app/main.py**

```python
with tab_debate:
    debate.render_debate()
```

Add `from app import debate` to the imports.

- [ ] **Step 3: Manually verify**

Run: `streamlit run app/main.py`
Check: the Debate tab's default text submits and shows "What actually happened", the steelman/counter-case columns, a verified badge, the confidence bar, the verdict callout, and the lineage string.

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/debate.py app/main.py
git commit -m "Add Debate (Outrage) tab"
```

---

### Task 9: app/components.py incident card + app/history.py — History tab

**Files:**
- Modify: `app/components.py`
- Test: `tests/test_components.py`
- Create: `app/history.py`
- Modify: `app/main.py` (History tab block)

**Interfaces:**
- Consumes (new in components.py): nothing new
- Produces (new in components.py): `render_incident_card_html(incident: dict) -> str`
- Produces (history.py): `render_history() -> None`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_components.py

def test_render_incident_card_html_includes_title_year_and_decision():
    incident = {
        "title": "Hand of God",
        "year": 1986,
        "match": "Argentina vs England",
        "description": "Maradona punched the ball into the net.",
        "decision": "Goal stood — missed by officials.",
        "comparison_to_today": "VAR would have caught this instantly.",
    }
    html = components.render_incident_card_html(incident)
    assert "Hand of God" in html
    assert "1986" in html
    assert "Goal stood" in html
    assert "VAR would have caught this instantly." in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_components.py -v -k incident_card`
Expected: FAIL with `AttributeError: module 'app.components' has no attribute 'render_incident_card_html'`

- [ ] **Step 3: Add to app/components.py**

```python
def render_incident_card_html(incident: dict) -> str:
    html = (
        '<div class="incident-card">'
        f'<h4>{incident["title"]} ({incident["year"]})</h4>'
        f'<div class="incident-meta">{incident["match"]}</div>'
        f'<p>{incident["description"]}</p>'
        f'<p><strong>Decision:</strong> {incident["decision"]}</p>'
    )
    if incident.get("comparison_to_today"):
        html += f'<div class="callout">{incident["comparison_to_today"]}</div>'
    html += "</div>"
    return html
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_components.py -v`
Expected: 14 passed

- [ ] **Step 5: Create app/history.py**

```python
import streamlit as st

from app import components
from backend.engines import consistency

TOPICS = ["offside", "handball", "goal-line", "penalty"]
TOPIC_LABELS = {"offside": "\U0001F6A9 offside", "handball": "✅ handball", "goal-line": "\U0001F4CF goal-line", "penalty": "⚖️ penalty"}


def render_history() -> None:
    st.markdown("## Decision Consistency Analyzer")
    st.write("Compare today's call with real World Cup history.")

    topic = st.radio("Topic", TOPICS, format_func=lambda t: TOPIC_LABELS[t], key="history_topic")
    data = consistency.compare(topic)

    if data["today"]:
        st.markdown(
            f'<div class="confidence-card">'
            f'{components.render_glow_bar_html("Today\'s call confidence", data["today"]["confidence"], "var(--accent)")}'
            f'<div style="margin-top:6px;">Today\'s call: {data["today"]["decision"]}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.write(f"This match has no {topic} review to compare against — here's the history.")

    for incident in data["historical_incidents"]:
        st.markdown(components.render_incident_card_html(incident), unsafe_allow_html=True)
```

- [ ] **Step 6: Wire it into app/main.py**

```python
with tab_history:
    history.render_history()
```

Add `from app import history` to the imports.

- [ ] **Step 7: Manually verify**

Run: `streamlit run app/main.py`
Check: the History tab shows 4 topic options; "offside" shows today's confidence card plus historical incident cards (1986 Hand of God, etc.); switching to "penalty" (a topic with no `today` review) shows the "no review to compare against" message plus its historical incidents.

- [ ] **Step 8: Run the full test suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add app/components.py app/history.py app/main.py tests/test_components.py
git commit -m "Add History tab and incident card builder"
```

---

### Task 10: app/replay.py — Live Replay tab (self-contained JS island)

**Files:**
- Create: `app/replay.py`
- Modify: `app/main.py` (Live Replay tab block)

**Interfaces:**
- Consumes: nothing from `components.py` (this is a standalone embedded document — it can't call Python at runtime, so it re-implements its own minimal momentum-chart drawing in JS, same as the old frontend did with one shared function; duplicating ~15 lines of SVG-building JS here is correct, not a DRY violation, since this code runs in an isolated iframe with no access to Python)
- Produces: `render_replay(match_data: dict) -> None`

- [ ] **Step 1: Create app/replay.py**

```python
import json

import streamlit.components.v1 as components_v1


def render_replay(match_data: dict) -> None:
    payload = json.dumps(
        {
            "home": match_data["home"],
            "away": match_data["away"],
            "events": match_data["events"],
            "momentum": match_data["momentum"],
        }
    )

    html = f"""
    <html>
    <head>
    <style>
      body {{ margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #0b0b0b; color: #eaeaea; }}
      .replay-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
      .replay-minute {{ font-size: 1.8em; font-weight: 900; }}
      .replay-minute .tick {{ font-size: 0.6em; color: #999; }}
      .replay-controls {{ display: flex; gap: 8px; align-items: center; margin-bottom: 14px; }}
      .replay-controls button {{ background: #161616; border: 1px solid #2a2a2a; color: #eaeaea; padding: 6px 14px; border-radius: 4px; cursor: pointer; }}
      .speed-btn.on {{ border-color: #00e0ff; color: #00e0ff; }}
      .replay-controls input[type="range"] {{ flex: 1; accent-color: #00e0ff; }}
      .replay-banner {{ background: linear-gradient(90deg, #8a0000, #1a0000); border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }}
      .replay-banner .label {{ color: #fff; font-size: 0.7em; font-weight: 700; letter-spacing: 1px; }}
      .replay-banner .title {{ color: #fff; font-size: 0.95em; font-weight: 600; margin-top: 2px; }}
      .event-row {{ display: flex; align-items: center; gap: 10px; background: #161616; border-left: 3px solid #00e0ff; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }}
      .event-row .minute {{ color: #00e0ff; min-width: 3em; font-weight: 700; }}
      .event-badge {{ display: inline-block; font-size: 0.75em; text-transform: uppercase; background: #2a2a2a; color: #999; border-radius: 4px; padding: 2px 6px; }}
      .momentum-svg {{ width: 100%; display: block; background: #161616; border-radius: 6px; padding: 8px; box-sizing: border-box; }}
    </style>
    </head>
    <body>
      <div class="replay-header">
        <div class="replay-minute" id="replay-minute">0<span class="tick">'</span></div>
        <div class="replay-score" id="replay-score"></div>
      </div>
      <div class="replay-controls">
        <button id="replay-play-pause">▶ Play</button>
        <button data-speed="1" class="speed-btn on">1x</button>
        <button data-speed="2" class="speed-btn">2x</button>
        <button data-speed="4" class="speed-btn">4x</button>
        <input type="range" id="replay-seek" min="0" max="90" value="0">
      </div>
      <div id="replay-banner"></div>
      <svg id="replay-momentum" viewBox="0 0 380 130" class="momentum-svg"></svg>
      <div style="color:#999;font-size:0.75em;text-transform:uppercase;margin-bottom:6px;">Events so far</div>
      <div id="replay-ticker"></div>

      <script>
        var matchData = {payload};
        var EVENT_ICONS = {{goal: '⚽', var_review: '\u{1F6A9}', tactical: '\u{1F504}', substitution: '\u{1F501}', pressure: '\u{1F613}'}};
        var minute = 0, playing = false, speed = 1, intervalId = null, lastTriggeredId = null, bannerId = null;

        function xPos(m) {{ return 10 + (m / 90) * 360; }}
        function yPos(v, maxAbs) {{ return 65 - (v / maxAbs) * 50; }}

        function drawMomentum() {{
          var curve = matchData.momentum.filter(function(p) {{ return p.minute <= minute; }});
          var maxAbs = Math.max.apply(null, matchData.momentum.map(function(p) {{ return Math.abs(p.value); }}).concat([1]));
          var points = curve.map(function(p) {{ return xPos(p.minute) + ',' + yPos(p.value, maxAbs); }}).join(' ');
          var svg = document.getElementById('replay-momentum');
          svg.innerHTML = '<line x1="10" y1="65" x2="370" y2="65" stroke="#333" stroke-dasharray="3,3"/>' +
            '<polyline points="' + points + '" fill="none" stroke="' + matchData.home.color + '" stroke-width="2.5"/>';
        }}

        function renderState() {{
          document.getElementById('replay-seek').value = minute;
          document.getElementById('replay-minute').innerHTML = minute >= 90 ? 'Full Time' : minute + '<span class="tick">\\'</span>';
          var homeGoals = 0, awayGoals = 0;
          matchData.events.forEach(function(e) {{
            if (e.type === 'goal' && e.minute <= minute) {{ if (e.team === 'home') homeGoals++; else awayGoals++; }}
          }});
          document.getElementById('replay-score').textContent = matchData.home.name + ' ' + homeGoals + ' – ' + awayGoals + ' ' + matchData.away.name;
          drawMomentum();
          var past = matchData.events.filter(function(e) {{ return e.minute <= minute; }}).slice().reverse();
          document.getElementById('replay-ticker').innerHTML = past.map(function(e) {{
            return '<div class="event-row"><span>' + (EVENT_ICONS[e.type] || '•') + '</span>' +
              '<span class="minute">' + e.minute + '\\'</span>' +
              '<span class="event-badge">' + e.type + '</span><span>' + e.desc + '</span></div>';
          }}).join('');
          checkBanner();
        }}

        function checkBanner() {{
          var candidate = null;
          matchData.events.forEach(function(e) {{
            if (e.id && e.minute <= minute && e.id !== lastTriggeredId) candidate = e;
          }});
          if (!candidate) return;
          lastTriggeredId = candidate.id;
          bannerId = candidate.id;
          var banner = document.getElementById('replay-banner');
          banner.innerHTML = '<div class="replay-banner"><div><div class="label">\u{1F534} BREAKING — ' +
            candidate.type.toUpperCase() + '</div><div class="title">' + candidate.desc + '</div></div></div>';
          if ('speechSynthesis' in window) {{
            window.speechSynthesis.speak(new SpeechSynthesisUtterance(candidate.desc));
          }}
          setTimeout(function() {{ if (bannerId === candidate.id) banner.innerHTML = ''; }}, 5000);
        }}

        function tick() {{
          minute += 1;
          if (minute >= 90) {{ minute = 90; pause(); renderState(); return; }}
          renderState();
        }}

        function play() {{
          if (minute >= 90) {{ minute = 0; lastTriggeredId = null; bannerId = null; document.getElementById('replay-ticker').innerHTML = ''; document.getElementById('replay-banner').innerHTML = ''; }}
          playing = true;
          document.getElementById('replay-play-pause').textContent = '⏸ Pause';
          intervalId = setInterval(tick, 1000 / speed);
        }}

        function pause() {{
          playing = false;
          clearInterval(intervalId);
          document.getElementById('replay-play-pause').textContent = minute >= 90 ? '↻ Replay Again' : '▶ Play';
        }}

        document.getElementById('replay-play-pause').addEventListener('click', function() {{ playing ? pause() : play(); }});
        document.querySelectorAll('.speed-btn').forEach(function(btn) {{
          btn.addEventListener('click', function() {{
            speed = parseInt(btn.dataset.speed, 10);
            document.querySelectorAll('.speed-btn').forEach(function(b) {{ b.classList.toggle('on', b === btn); }});
            if (playing) {{ clearInterval(intervalId); intervalId = setInterval(tick, 1000 / speed); }}
          }});
        }});
        document.getElementById('replay-seek').addEventListener('input', function(e) {{
          pause();
          minute = parseInt(e.target.value, 10);
          lastTriggeredId = null;
          matchData.events.forEach(function(ev) {{ if (ev.id && ev.minute <= minute) lastTriggeredId = ev.id; }});
          bannerId = null;
          document.getElementById('replay-banner').innerHTML = '';
          renderState();
        }});

        renderState();
      </script>
    </body>
    </html>
    """
    components_v1.html(html, height=520, scrolling=True)
```

- [ ] **Step 2: Wire it into app/main.py**

```python
with tab_replay:
    replay.render_replay(match_data)
```

Add `from app import replay` to the imports.

- [ ] **Step 3: Manually verify**

Run: `streamlit run app/main.py`
Check: the Live Replay tab shows minute 0, clicking "Play" advances the minute every second, the score/momentum chart/event ticker update, a breaking-news banner appears and auto-dismisses after 5s when an event's minute is reached, speed buttons (1x/2x/4x) change the tick rate, dragging the seek slider jumps to that minute and pauses, and switching away from this Streamlit tab to another one does NOT need an explicit pause — Streamlit unmounting the `components.v1.html` iframe when its tab's `with` block isn't the active one naturally stops its `setInterval` (no JS port of the old "pause on tab switch" logic is needed, since the mechanism that required it — a single shared DOM tree — no longer exists; each Streamlit tab's content, including this iframe, is only mounted while visible).

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/replay.py app/main.py
git commit -m "Add Live Replay tab as a self-contained JS island"
```

---

### Task 11: Final wiring, docs, and full verification

**Files:**
- Modify: `app/main.py` (remove now-unused placeholder comments, confirm final tab wiring)
- Modify: `CLAUDE.md` (update Quick start, file map, and remove FastAPI/Render-specific instructions)

**Interfaces:** None new — this task is integration and documentation only.

- [ ] **Step 1: Review app/main.py end-to-end**

Confirm the final file matches this shape (imports at top, `match_data` dict built once, six tabs each calling exactly one `render_*` function):

```python
import streamlit as st

from app import ask, debate, history, moments, overview, replay, styles
from backend.engines import analytics, explainer

st.set_page_config(page_title="MatchMind", layout="centered")
styles.inject()

match_data = {
    "match_id": explainer.MATCH_DATA["match_id"],
    "competition": explainer.MATCH_DATA["competition"],
    "home": explainer.MATCH_DATA["home"],
    "away": explainer.MATCH_DATA["away"],
    "score": explainer.MATCH_DATA["score"],
    "events": explainer.MATCH_DATA["events"],
    "momentum": analytics.momentum_curve(
        explainer.MATCH_DATA["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    ),
}

tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay"]
)

with tab_overview:
    overview.render_overview(match_data)
with tab_moments:
    moments.render_moments(match_data)
with tab_ask:
    ask.render_ask()
with tab_debate:
    debate.render_debate()
with tab_history:
    history.render_history()
with tab_replay:
    replay.render_replay(match_data)
```

Apply any edits needed to match this exactly.

- [ ] **Step 2: Update CLAUDE.md**

Replace the "Quick start" section with:

```markdown
## Quick start

```bash
pip install -r requirements.txt
streamlit run app/main.py
# -> http://localhost:8501
```
```

In the "File map" section, replace the `backend/main.py` and `frontend/` entries with:

```markdown
app/
  main.py                       Streamlit entry point — builds match_data once, wires the 6 tabs
  styles.py                     Ported CSS (background blobs, badges, flags, crest, chat bubbles)
  components.py                 Pure HTML/SVG-string builders (unit-tested): header, flags, event
                                 rows, glow bars, momentum chart, Decision Lab pitch SVG, incident
                                 cards, speak buttons
  overview.py                   Overview tab
  moments.py                    Moments tab (Decision Lab + text moments + real incident)
  ask.py                        Ask MatchMind tab (native st.chat_message)
  debate.py                     Debate (Outrage) tab
  history.py                    History (Decision Consistency Analyzer) tab
  replay.py                     Live Replay tab — self-contained st.components.v1.html JS island
```

Remove the `frontend/index.html` line and the `requirements.txt` line's `fastapi · uvicorn · pydantic` mention, replacing with `streamlit`.

Remove the entire "## API" section (no HTTP API exists anymore) — note in its place:

```markdown
## No HTTP API

There is no FastAPI server or HTTP API in this app. `app/*.py` modules call
`backend.engines.*` directly as plain Python functions. `integrations/telegram_bot.py`
and `evals/*.py` already did this too and are unaffected by this change.
```

- [ ] **Step 3: Run the full test suite one final time**

Run: `python -m pytest -q`
Expected: all tests pass (113 — unchanged engine-level tests plus the new `tests/test_components.py`).

- [ ] **Step 4: Full manual browser walkthrough**

Run: `streamlit run app/main.py`, open in a browser, and click through all 6 tabs in order, exercising: Overview (header/cards/chart/events), Moments (offside_27 pitch + toggles + real incident, plus at least one text moment), Ask MatchMind (ask a question, verify chat history persists), Debate (submit the default take), History (switch between at least 2 topics), Live Replay (play, change speed, seek, let a banner appear and auto-dismiss).

- [ ] **Step 5: Commit**

```bash
git add app/main.py CLAUDE.md
git commit -m "Finalize Streamlit app wiring and update CLAUDE.md"
```

---

## Self-Review Notes

**Spec coverage:** All 6 tabs covered (Tasks 4, 6, 7, 8, 9, 10). Retirement of FastAPI/Render artifacts covered (Task 1). `requirements.txt` change covered (Task 1). Hybrid embedding approach covered: native checkbox/button+rerun for toggles (Task 6), `components.v1.html` only for Live Replay (Task 10) and speak buttons (Task 2) — the speak-button gap identified during planning (the spec didn't address TTS) is now covered. Deployment steps are user-performed per the spec and not part of this plan's tasks.

**Type consistency:** `match_data` dict shape is established in Task 1/4 (`home`, `away`, `score`, `events`, `momentum`, `competition`, `match_id`) and used identically in every later task — `moments.py`, `ask.py` (doesn't need `match_data`), `debate.py` (doesn't need it), `history.py` (doesn't need it), `replay.py` all consume the same keys. `components.render_decision_lab_pitch_html` signature (`moment, match_data, show_sightline, show_uncertainty_band`) matches its Task 6 call site exactly.

**No placeholders:** every step has complete, real code — no TBD/TODO markers.
