# Team Fatigue & Pressure Zones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 9th "Fatigue & Pressure" tab showing one zone blob per team on a pitch SVG, scrubbed across the match's 6 real time windows — blob size from real defensive-line compactness, blob color from the existing real `fatigue_index`.

**Architecture:** A new pure function `analytics.fatigue_pressure_zones` reuses the existing `fatigue_index` directly and adds a min-max-scaled "spread" score from `line_gap_def_mid_m` (same scaling pattern as `tactical_dna`). A new pure SVG-builder `components.render_fatigue_zone_pitch_html` draws two fixed-position ellipses sized/colored from those values. A new `app/fatigue_pressure.py` tab module wires both together with a window scrubber and a real-numbers table, added as a 9th tab.

**Tech Stack:** Python (`backend/engines/analytics.py`), Streamlit (`app/main.py`, new `app/fatigue_pressure.py`, `app/components.py`).

## Global Constraints

- Team-level only — no per-player data, real or fabricated. The UI must say so explicitly.
- Blob SIZE encodes `line_gap_def_mid_m` (compactness). Blob COLOR encodes `fatigue_index` (already computed). Never use `line_gap_def_mid_m` to position the blob vertically — it doesn't measure pitch height, only compactness, and positioning by it would imply a spatial claim the metric doesn't support.
- Fixed blob x-positions: home at `x=30`, away at `x=70` (mirrored, each team's own defensive/middle area).
- Zero-variance edge case for `spread` (`hi == lo` across both teams' line-gap values): both teams get exactly `50.0`, no `ZeroDivisionError` — same convention as `tactical_dna`.
- 6 time windows, same labels as `TELEMETRY_DATA["windows"]` (`"0-15"` through `"75-90"`) — reuse this list directly, don't redefine it.
- New tab placed 9th, after "What If".

---

### Task 1: `analytics.fatigue_pressure_zones`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

**Interfaces:**
- Consumes: `home_telemetry: dict`, `away_telemetry: dict` (existing shape, same as `fatigue_index`/`tactical_dna` already consume)
- Produces: `fatigue_pressure_zones(home_telemetry, away_telemetry) -> dict`, shape: `{"windows": list[str], "home": {"fatigue_index": list[float], "spread": list[float]}, "away": {"fatigue_index": list[float], "spread": list[float]}}`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_analytics.py`:

```python
def test_fatigue_pressure_zones_spread_zero_variance_gives_fifty():
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
    result = analytics.fatigue_pressure_zones(home, away)
    assert result["home"]["spread"] == [50.0] * 6
    assert result["away"]["spread"] == [50.0] * 6


def test_fatigue_pressure_zones_returns_windows_list():
    home = analytics.TELEMETRY_DATA["teams"]["home"]
    away = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_pressure_zones(home, away)
    assert result["windows"] == analytics.TELEMETRY_DATA["windows"]
    assert len(result["windows"]) == 6


def test_fatigue_pressure_zones_on_real_fixture_telemetry():
    home = analytics.TELEMETRY_DATA["teams"]["home"]
    away = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_pressure_zones(home, away)
    for team in ("home", "away"):
        assert len(result[team]["fatigue_index"]) == 6
        assert len(result[team]["spread"]) == 6
        for v in result[team]["spread"]:
            assert 0.0 <= v <= 100.0
    # Real data: away's line_gap_def_mid_m grows from 8.0 to 11.6 across the
    # match (their defensive shape stretches as fatigue sets in) -- spread
    # should rise from window 0 to window 5, not flat or reversed.
    assert result["away"]["spread"][5] > result["away"]["spread"][0]
    # Home's fatigue_index values should match calling fatigue_index directly --
    # this function must reuse it, not duplicate the math.
    assert result["home"]["fatigue_index"] == analytics.fatigue_index(home)["result"]["fatigue_index"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k fatigue_pressure_zones`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'fatigue_pressure_zones'`

- [ ] **Step 3: Implement `fatigue_pressure_zones` in `backend/engines/analytics.py`**

Add at the end of the file:

```python
def fatigue_pressure_zones(home_telemetry: dict, away_telemetry: dict) -> dict:
    """
    Per-window, per-team zone data for the Fatigue & Pressure tab: a real
    fatigue_index value (already computed, already tested) plus a
    min-max-scaled "spread" score from real line_gap_def_mid_m (bigger
    gap = more stretched/disorganized defensive shape). Team-level only --
    matchMind has no real per-player tracking data.
    """
    home_fatigue = fatigue_index(home_telemetry)["result"]["fatigue_index"]
    away_fatigue = fatigue_index(away_telemetry)["result"]["fatigue_index"]

    home_gap = home_telemetry["line_gap_def_mid_m"]
    away_gap = away_telemetry["line_gap_def_mid_m"]
    all_gaps = home_gap + away_gap
    lo, hi = min(all_gaps), max(all_gaps)

    def spread(values):
        if hi == lo:
            return [50.0] * len(values)
        return [round((v - lo) / (hi - lo) * 100, 1) for v in values]

    return {
        "windows": TELEMETRY_DATA["windows"],
        "home": {"fatigue_index": home_fatigue, "spread": spread(home_gap)},
        "away": {"fatigue_index": away_fatigue, "spread": spread(away_gap)},
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k fatigue_pressure_zones`
Expected: 3 passed

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (126 — 123 existing + 3 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "Add fatigue_pressure_zones analytics model"
```

---

### Task 2: `components.render_fatigue_zone_pitch_html`

**Files:**
- Modify: `app/components.py`
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: nothing new from Task 1 directly (takes plain `float` values, not the full `fatigue_pressure_zones` dict — the tab module in Task 3 extracts the per-window values before calling this)
- Produces: `render_fatigue_zone_pitch_html(home_name: str, away_name: str, home_color: str, away_color: str, home_fatigue: float, home_spread: float, away_fatigue: float, away_spread: float) -> str`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_components.py`:

```python
def test_render_fatigue_zone_pitch_html_contains_svg_and_team_names():
    html = components.render_fatigue_zone_pitch_html(
        "Argentina", "France", "#75AADB", "#0055A4",
        home_fatigue=-1.5, home_spread=9.8, away_fatigue=54.6, away_spread=100.0,
    )
    assert "<svg" in html
    assert "<ellipse" in html
    assert "Argentina" in html
    assert "France" in html


def test_render_fatigue_zone_pitch_html_larger_spread_gives_larger_radius():
    small_spread_html = components.render_fatigue_zone_pitch_html(
        "Argentina", "France", "#75AADB", "#0055A4",
        home_fatigue=0.0, home_spread=0.0, away_fatigue=0.0, away_spread=0.0,
    )
    large_spread_html = components.render_fatigue_zone_pitch_html(
        "Argentina", "France", "#75AADB", "#0055A4",
        home_fatigue=0.0, home_spread=100.0, away_fatigue=0.0, away_spread=100.0,
    )
    assert small_spread_html != large_spread_html


def test_render_fatigue_zone_pitch_html_high_fatigue_blends_toward_red():
    low_fatigue_html = components.render_fatigue_zone_pitch_html(
        "Argentina", "France", "#75AADB", "#0055A4",
        home_fatigue=0.0, home_spread=50.0, away_fatigue=0.0, away_spread=50.0,
    )
    high_fatigue_html = components.render_fatigue_zone_pitch_html(
        "Argentina", "France", "#75AADB", "#0055A4",
        home_fatigue=0.0, home_spread=50.0, away_fatigue=60.0, away_spread=50.0,
    )
    assert low_fatigue_html != high_fatigue_html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_components.py -v -k fatigue_zone_pitch`
Expected: FAIL with `AttributeError: module 'app.components' has no attribute 'render_fatigue_zone_pitch_html'`

- [ ] **Step 3: Implement `render_fatigue_zone_pitch_html` in `app/components.py`**

Add at the end of the file:

```python
def _blend_toward_red(hex_color: str, intensity: float) -> str:
    """intensity is expected roughly in [0, 100]; clamped so an out-of-range
    fatigue_index value (it can run slightly negative, e.g. -2.0, when a
    team is fresher than their own first-half baseline) never produces an
    invalid blend ratio."""
    ratio = max(0.0, min(1.0, intensity / 100))
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    blend = lambda c, target: round(c + (target - c) * ratio)
    return f"rgb({blend(r, 204)},{blend(g, 51)},{blend(b, 51)})"


def render_fatigue_zone_pitch_html(
    home_name: str, away_name: str, home_color: str, away_color: str,
    home_fatigue: float, home_spread: float, away_fatigue: float, away_spread: float,
) -> str:
    home_radius = 8 + home_spread / 100 * 10
    away_radius = 8 + away_spread / 100 * 10
    home_fill = _blend_toward_red(home_color, home_fatigue)
    away_fill = _blend_toward_red(away_color, away_fatigue)

    return (
        '<svg viewBox="-2 -2 104 72" class="pitch-svg">'
        '<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38"/>'
        '<g stroke="#eaf5ee" stroke-width="0.35" fill="none" opacity="0.9">'
        '<rect x="0" y="0" width="100" height="68"/>'
        '<line x1="50" y1="0" x2="50" y2="68"/>'
        '<circle cx="50" cy="34" r="8.7"/>'
        "</g>"
        f'<ellipse cx="30" cy="34" rx="{home_radius:.1f}" ry="{home_radius:.1f}" '
        f'fill="{home_fill}" fill-opacity="0.6" stroke="{home_color}" stroke-width="0.5"/>'
        f'<ellipse cx="70" cy="34" rx="{away_radius:.1f}" ry="{away_radius:.1f}" '
        f'fill="{away_fill}" fill-opacity="0.6" stroke="{away_color}" stroke-width="0.5"/>'
        f'<text x="30" y="60" fill="{home_color}" font-size="4" text-anchor="middle">{home_name}</text>'
        f'<text x="70" y="60" fill="{away_color}" font-size="4" text-anchor="middle">{away_name}</text>'
        "</svg>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v -k fatigue_zone_pitch`
Expected: 3 passed

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (129 — 126 + 3 new)

- [ ] **Step 6: Commit**

```bash
git add app/components.py tests/test_components.py
git commit -m "Add render_fatigue_zone_pitch_html to app/components.py"
```

---

### Task 3: `app/fatigue_pressure.py` tab + wire into `app/main.py`

**Files:**
- Create: `app/fatigue_pressure.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `analytics.fatigue_pressure_zones(home_telemetry, away_telemetry) -> dict` (Task 1), `components.render_fatigue_zone_pitch_html(...)` (Task 2)
- Produces: `render_fatigue_pressure(match_data: dict) -> None`

- [ ] **Step 1: Create `app/fatigue_pressure.py`**

```python
import streamlit as st

from app import components
from backend.engines import analytics


def render_fatigue_pressure(match_data: dict) -> None:
    st.markdown("## Fatigue & Pressure")
    st.write(
        "One zone per team, not per player — matchMind's data is team-level "
        "aggregate telemetry, not individual player tracking. Zone size "
        "reflects how stretched each team's defensive shape is (the real gap "
        "between their defensive line and midfield); zone color reflects "
        "their real computed fatigue index."
    )

    home_telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    away_telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    zones = analytics.fatigue_pressure_zones(home_telemetry, away_telemetry)

    window_label = st.select_slider("Match window", options=zones["windows"])
    window_index = zones["windows"].index(window_label)

    svg = components.render_fatigue_zone_pitch_html(
        match_data["home"]["name"],
        match_data["away"]["name"],
        match_data["home"]["color"],
        match_data["away"]["color"],
        zones["home"]["fatigue_index"][window_index],
        zones["home"]["spread"][window_index],
        zones["away"]["fatigue_index"][window_index],
        zones["away"]["spread"][window_index],
    )
    st.markdown(f'<div class="pitch-wrap">{svg}</div>', unsafe_allow_html=True)

    st.markdown("### Real numbers behind the zones")
    st.write(
        f"**{match_data['home']['name']}**: fatigue index "
        f"{zones['home']['fatigue_index'][window_index]}, line gap "
        f"{home_telemetry['line_gap_def_mid_m'][window_index]}m"
    )
    st.write(
        f"**{match_data['away']['name']}**: fatigue index "
        f"{zones['away']['fatigue_index'][window_index]}, line gap "
        f"{away_telemetry['line_gap_def_mid_m'][window_index]}m"
    )
```

- [ ] **Step 2: Wire into `app/main.py`**

Replace:

```python
from app import ask, debate, history, moments, overview, replay, styles, tactical_dna, what_if
```

with:

```python
from app import ask, debate, fatigue_pressure, history, moments, overview, replay, styles, tactical_dna, what_if
```

Replace:

```python
tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna, tab_what_if = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA", "What If"]
)
```

with:

```python
tab_overview, tab_moments, tab_ask, tab_debate, tab_history, tab_replay, tab_tactical_dna, tab_what_if, tab_fatigue_pressure = st.tabs(
    ["Overview", "Moments", "Ask MatchMind", "Debate", "History", "Live Replay", "Tactical DNA", "What If", "Fatigue & Pressure"]
)
```

Add at the end of the file, after the existing `with tab_what_if:` block:

```python
with tab_fatigue_pressure:
    fatigue_pressure.render_fatigue_pressure(match_data)
```

- [ ] **Step 3: Verify the app boots**

Run: `python -m streamlit run app/main.py --server.headless true --server.port 8580 &`, then `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8580 --max-time 10`
Expected: `200`. Stop the server afterward.

- [ ] **Step 4: Manually verify with a live browser check**

Using the chrome-devtools MCP tool: navigate to the app, click the "Fatigue & Pressure" tab (9th tab, after "What If"). Confirm a pitch SVG renders with two ellipses (one per team), the team-level-not-per-player callout text, and the "Real numbers behind the zones" section. Then move the window slider from "0-15" to "75-90" and confirm: the away team's ellipse visibly grows and its color visibly shifts toward red (away's spread rises from ~12 to 100 and fatigue_index rises from ~-0.6 to ~54.6 across the real fixture's windows), while home's ellipse stays comparatively small and its color stays close to its base team color. Take a screenshot of at least the "75-90" window state as evidence.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all passing (129), no regressions

- [ ] **Step 6: Commit**

```bash
git add app/fatigue_pressure.py app/main.py
git commit -m "Add Fatigue & Pressure tab"
```

---

## Self-Review Notes

**Spec coverage:** `fatigue_pressure_zones` with min-max scaling, zero-variance fallback, and `fatigue_index` reuse (Task 1); the size-not-position constraint on `line_gap_def_mid_m`, color-from-fatigue blending, fixed x=30/x=70 positions (Task 2); window scrubber, team-level-not-per-player callout, real-numbers table, 9th-tab wiring (Task 3) — all covered.

**No placeholders:** every step has complete, real code.

**Type consistency:** `fatigue_pressure_zones`'s return shape (`windows`, `home`/`away` each with `fatigue_index`/`spread` lists) is defined once in Task 1 and consumed by index (`zones["home"]["fatigue_index"][window_index]`, etc.) in Task 3 exactly matching those key names. `render_fatigue_zone_pitch_html`'s 8 positional parameters (Task 2) are passed in the same order from Task 3's call site.
