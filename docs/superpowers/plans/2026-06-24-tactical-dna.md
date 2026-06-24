# Tactical DNA Fingerprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 7th "Tactical DNA" tab showing a 4-axis radar chart comparing both teams' playing style, computed entirely from real `telemetry.json` data already used by `fatigue_index`.

**Architecture:** A new pure function `analytics.tactical_dna(home_telemetry, away_telemetry)` computes 4 min-max-scaled axis scores per team plus the real raw averages behind them. A new pure SVG-builder `components.render_tactical_dna_radar_html` draws the two-polygon radar chart. A new `app/tactical_dna.py` tab module wires both together with a raw-numbers legend table, added as a 7th tab in `app/main.py`.

**Tech Stack:** Python (`backend/engines/analytics.py`), Streamlit (`app/main.py`, new `app/tactical_dna.py`, `app/components.py`).

## Global Constraints

- Axes and inversion rules: `pressing_intensity` (PPDA, inverted), `directness` (long_pass_share, not inverted), `defensive_compactness` (line_gap_def_mid_m, inverted), `transition_speed` (sprints, not inverted — explicitly labeled a proxy, not a literal measurement).
- Each axis is min-max scaled (0-100) against the real observed range across BOTH teams' windows in `telemetry.json` for THIS match — never an external/invented benchmark.
- Zero-variance edge case (`hi == lo` for an axis): both teams get exactly `50.0`, no `ZeroDivisionError`.
- New tab placed after "Live Replay" in the tab order.
- No new feature beyond what's in the design doc — no per-window animation, no historical/league baseline.

---

### Task 1: `analytics.tactical_dna`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

**Interfaces:**
- Consumes: `home_telemetry: dict`, `away_telemetry: dict` (existing shape: `{"sprints": [float×6], "line_gap_def_mid_m": [float×6], "long_pass_share": [float×6], "ppda": [float×6]}`, same shape `fatigue_index` already consumes)
- Produces: `tactical_dna(home_telemetry, away_telemetry) -> dict`, shape: `{"home": {axis_name: float, ...4 axes...}, "away": {...}, "raw_inputs": {axis_name: {"home": float, "away": float, "field": str}, ...}}`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_analytics.py`:

```python
def test_tactical_dna_scales_against_observed_range():
    home = {
        "sprints": [40, 40, 40, 40, 40, 40],
        "line_gap_def_mid_m": [7.0, 7.0, 7.0, 7.0, 7.0, 7.0],
        "long_pass_share": [0.30, 0.30, 0.30, 0.30, 0.30, 0.30],
        "ppda": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
    }
    away = {
        "sprints": [20, 20, 20, 20, 20, 20],
        "line_gap_def_mid_m": [11.0, 11.0, 11.0, 11.0, 11.0, 11.0],
        "long_pass_share": [0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
        "ppda": [16.0, 16.0, 16.0, 16.0, 16.0, 16.0],
    }
    result = analytics.tactical_dna(home, away)
    # Home has lower PPDA (presses more) -> higher pressing_intensity (inverted axis)
    assert result["home"]["pressing_intensity"] == 100.0
    assert result["away"]["pressing_intensity"] == 0.0
    # Home has higher long_pass_share -> higher directness (not inverted)
    assert result["home"]["directness"] == 100.0
    assert result["away"]["directness"] == 0.0
    # Home has smaller line gap (more compact) -> higher defensive_compactness (inverted)
    assert result["home"]["defensive_compactness"] == 100.0
    assert result["away"]["defensive_compactness"] == 0.0
    # Home has more sprints -> higher transition_speed (not inverted)
    assert result["home"]["transition_speed"] == 100.0
    assert result["away"]["transition_speed"] == 0.0


def test_tactical_dna_zero_variance_axis_gives_fifty():
    home = {
        "sprints": [30, 30, 30, 30, 30, 30],
        "line_gap_def_mid_m": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
        "long_pass_share": [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        "ppda": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    }
    away = {
        "sprints": [30, 30, 30, 30, 30, 30],
        "line_gap_def_mid_m": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
        "long_pass_share": [0.20, 0.20, 0.20, 0.20, 0.20, 0.20],
        "ppda": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    }
    result = analytics.tactical_dna(home, away)
    for axis in ("pressing_intensity", "directness", "defensive_compactness", "transition_speed"):
        assert result["home"][axis] == 50.0
        assert result["away"][axis] == 50.0


def test_tactical_dna_on_real_fixture_telemetry():
    home = analytics.TELEMETRY_DATA["teams"]["home"]
    away = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.tactical_dna(home, away)
    for team in ("home", "away"):
        for axis in ("pressing_intensity", "directness", "defensive_compactness", "transition_speed"):
            assert 0.0 <= result[team][axis] <= 100.0
    # Real data: home's PPDA stays low/consistent (8.5-9.5), away's rises to 13.2 --
    # home presses harder throughout, so home's pressing_intensity score is higher.
    assert result["home"]["pressing_intensity"] > result["away"]["pressing_intensity"]
    assert result["raw_inputs"]["pressing_intensity"]["field"] == "ppda"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k tactical_dna`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'tactical_dna'`

- [ ] **Step 3: Implement `tactical_dna` in `backend/engines/analytics.py`**

Add at the end of the file:

```python
def tactical_dna(home_telemetry: dict, away_telemetry: dict) -> dict:
    """
    4-axis "fingerprint" of each team's playing style, computed entirely
    from real per-window telemetry already used by fatigue_index -- no
    new data source, no invented league-average benchmark. Each axis is
    min-max scaled (0-100) against the actual observed range across BOTH
    teams' windows in THIS match, not an external baseline.
    """
    def _scale(home_values, away_values, invert):
        all_values = home_values + away_values
        lo, hi = min(all_values), max(all_values)
        home_avg = sum(home_values) / len(home_values)
        away_avg = sum(away_values) / len(away_values)
        if hi == lo:
            return 50.0, 50.0, home_avg, away_avg

        def scaled(avg):
            pct = (avg - lo) / (hi - lo)
            return round((1 - pct) * 100, 1) if invert else round(pct * 100, 1)

        return scaled(home_avg), scaled(away_avg), round(home_avg, 2), round(away_avg, 2)

    axes = [
        ("pressing_intensity", "ppda", True),
        ("directness", "long_pass_share", False),
        ("defensive_compactness", "line_gap_def_mid_m", True),
        ("transition_speed", "sprints", False),
    ]

    home_scores, away_scores, raw_inputs = {}, {}, {}
    for axis_name, field, invert in axes:
        home_score, away_score, home_avg, away_avg = _scale(
            home_telemetry[field], away_telemetry[field], invert
        )
        home_scores[axis_name] = home_score
        away_scores[axis_name] = away_score
        raw_inputs[axis_name] = {"home": home_avg, "away": away_avg, "field": field}

    return {"home": home_scores, "away": away_scores, "raw_inputs": raw_inputs}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k tactical_dna`
Expected: 3 passed

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (120 — 117 existing + 3 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "Add tactical_dna analytics model"
```

---

### Task 2: `components.render_tactical_dna_radar_html`

**Files:**
- Modify: `app/components.py` (add `import math` if not already present — check first)
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: `home_scores: dict`, `away_scores: dict` (Task 1's per-team axis dicts, keys `pressing_intensity`/`directness`/`defensive_compactness`/`transition_speed`)
- Produces: `render_tactical_dna_radar_html(home_name: str, away_name: str, home_scores: dict, away_scores: dict, home_color: str, away_color: str) -> str`

- [ ] **Step 1: Check whether `math` is already imported**

Run: `grep -n "^import math" app/components.py`
If it prints nothing, add `import math` near the top of the file in Step 3.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_components.py`:

```python
def test_render_tactical_dna_radar_html_contains_svg_and_team_names():
    home_scores = {"pressing_intensity": 87.9, "directness": 6.7, "defensive_compactness": 95.5, "transition_speed": 77.8}
    away_scores = {"pressing_intensity": 54.6, "directness": 40.0, "defensive_compactness": 52.0, "transition_speed": 53.7}
    html = components.render_tactical_dna_radar_html(
        "Argentina", "France", home_scores, away_scores, "#75AADB", "#0055A4"
    )
    assert "<svg" in html
    assert "polygon" in html
    assert "Pressing Intensity" in html or "pressing intensity" in html.lower()
    assert "Directness" in html or "directness" in html.lower()
    assert "Defensive Compactness" in html or "defensive compactness" in html.lower()
    assert "Transition Speed" in html or "transition speed" in html.lower()


def test_render_tactical_dna_radar_html_uses_team_colors():
    home_scores = {"pressing_intensity": 50.0, "directness": 50.0, "defensive_compactness": 50.0, "transition_speed": 50.0}
    away_scores = {"pressing_intensity": 50.0, "directness": 50.0, "defensive_compactness": 50.0, "transition_speed": 50.0}
    html = components.render_tactical_dna_radar_html(
        "Argentina", "France", home_scores, away_scores, "#75AADB", "#0055A4"
    )
    assert "#75AADB" in html
    assert "#0055A4" in html
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_components.py -v -k tactical_dna_radar`
Expected: FAIL with `AttributeError: module 'app.components' has no attribute 'render_tactical_dna_radar_html'`

- [ ] **Step 4: Implement `render_tactical_dna_radar_html` in `app/components.py`**

Add at the end of the file:

```python
def render_tactical_dna_radar_html(
    home_name: str, away_name: str, home_scores: dict, away_scores: dict,
    home_color: str, away_color: str,
) -> str:
    axis_order = ["pressing_intensity", "directness", "defensive_compactness", "transition_speed"]
    axis_labels = {
        "pressing_intensity": "Pressing Intensity",
        "directness": "Directness",
        "defensive_compactness": "Defensive Compactness",
        "transition_speed": "Transition Speed",
    }
    cx, cy, radius = 110, 110, 90

    def point(i, score):
        angle = math.radians(-90 + i * 90)
        r = radius * (score / 100)
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    def polygon_points(scores):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, scores[axis]) for i, axis in enumerate(axis_order)))

    grid_circles = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{radius * pct}" fill="none" stroke="#333" stroke-width="0.5"/>'
        for pct in (0.25, 0.5, 0.75, 1.0)
    )

    labels = ""
    for i, axis in enumerate(axis_order):
        lx, ly = point(i, 118)
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#999" font-size="9" text-anchor="middle">{axis_labels[axis]}</text>'

    home_poly = polygon_points(home_scores)
    away_poly = polygon_points(away_scores)

    return (
        '<svg viewBox="0 0 220 230" class="momentum-chart-svg">'
        f"{grid_circles}"
        f'<polygon points="{home_poly}" fill="{home_color}" fill-opacity="0.3" stroke="{home_color}" stroke-width="1.5"/>'
        f'<polygon points="{away_poly}" fill="{away_color}" fill-opacity="0.3" stroke="{away_color}" stroke-width="1.5"/>'
        f"{labels}"
        f'<text x="10" y="215" fill="{home_color}" font-size="10">{home_name}</text>'
        f'<text x="120" y="215" fill="{away_color}" font-size="10">{away_name}</text>'
        "</svg>"
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v -k tactical_dna_radar`
Expected: 2 passed

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (122 — 120 + 2 new)

- [ ] **Step 7: Commit**

```bash
git add app/components.py tests/test_components.py
git commit -m "Add render_tactical_dna_radar_html to app/components.py"
```

---

### Task 3: `app/tactical_dna.py` tab + wire into `app/main.py`

**Files:**
- Create: `app/tactical_dna.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `analytics.tactical_dna(home_telemetry, away_telemetry) -> dict` (Task 1), `components.render_tactical_dna_radar_html(...)` (Task 2)
- Produces: `render_tactical_dna(match_data: dict) -> None`

- [ ] **Step 1: Create `app/tactical_dna.py`**

```python
import streamlit as st

from app import components
from backend.engines import analytics

AXIS_LABELS = {
    "pressing_intensity": "Pressing Intensity (inverse of PPDA)",
    "directness": "Directness (long-pass share)",
    "defensive_compactness": "Defensive Compactness (inverse of line gap)",
    "transition_speed": "Transition Speed (sprints — a proxy, not a literal measurement)",
}


def render_tactical_dna(match_data: dict) -> None:
    st.markdown("## Tactical DNA")
    st.write(
        "Each team's playing-style fingerprint, computed from real per-window "
        "telemetry — not a fabricated cross-match benchmark."
    )

    home_telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    away_telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    dna = analytics.tactical_dna(home_telemetry, away_telemetry)

    svg = components.render_tactical_dna_radar_html(
        match_data["home"]["name"],
        match_data["away"]["name"],
        dna["home"],
        dna["away"],
        match_data["home"]["color"],
        match_data["away"]["color"],
    )
    st.markdown(f'<div class="momentum-chart-wrap">{svg}</div>', unsafe_allow_html=True)

    st.markdown("### Real numbers behind the chart")
    for axis, raw in dna["raw_inputs"].items():
        st.write(f"**{AXIS_LABELS[axis]}**: {match_data['home']['name']} {raw['home']} vs {match_data['away']['name']} {raw['away']}")
```

- [ ] **Step 2: Wire into `app/main.py`**

Replace:

```python
from app import ask, debate, history, moments, overview, replay, styles
```

with:

```python
from app import ask, debate, history, moments, overview, replay, styles, tactical_dna
```

Replace:

```python
tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay"]
)
```

with:

```python
tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA"]
)
```

Add at the end of the file, after the existing `with tab_replay:` block:

```python
with tab_tactical_dna:
    tactical_dna.render_tactical_dna(match_data)
```

- [ ] **Step 3: Verify the app boots**

Run: `python -m streamlit run app/main.py --server.headless true --server.port 8550 &`, then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8550 --max-time 10`
Expected: `200`. Stop the server afterward.

- [ ] **Step 4: Manually verify with a live browser check**

Using the chrome-devtools MCP tool: navigate to the app, click the "Tactical DNA" tab (7th tab, after "Live Replay"), confirm a radar chart renders with two overlaid colored polygons, 4 axis labels (Pressing Intensity, Directness, Defensive Compactness, Transition Speed), team names in their colors below the chart, and a "Real numbers behind the chart" section listing both teams' real average values for each axis. Take a screenshot as evidence.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (122), no regressions

- [ ] **Step 6: Commit**

```bash
git add app/tactical_dna.py app/main.py
git commit -m "Add Tactical DNA tab"
```

---

## Self-Review Notes

**Spec coverage:** `tactical_dna` analytics with min-max scaling and zero-variance edge case (Task 1), radar SVG builder (Task 2), tab module + raw-numbers legend + wiring as 7th tab (Task 3) — all covered.

**No placeholders:** every step has complete, real code.

**Type consistency:** `tactical_dna`'s return shape (`{"home": {...4 axes...}, "away": {...}, "raw_inputs": {...}}`) is defined once in Task 1 and consumed with the exact same axis-name keys in Task 2's radar builder and Task 3's legend loop — no naming drift. `home_scores`/`away_scores` parameter names match between Task 2's function signature and Task 3's call site.
