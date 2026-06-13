# Phase 2 — Analytics Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `backend/engines/analytics.py` implementing the six computed
analytics models from `CLAUDE.md` (offside probability, offside sensitivity,
counterfactual timing, handball reaction, fatigue index, momentum curve),
backed by a new `backend/data/telemetry.json` and two new dossier fields in
`sample_match.json`. Expose all six via a new `GET /api/analytics` endpoint,
switch `GET /api/match`'s `momentum` field to the computed curve, and add an
`"analytics"` key to `GET /api/moment/{id}`.

**Architecture:** `analytics.py` is a pure-Python module (only `math`) that
loads `sample_match.json` and `telemetry.json` at import time, mirroring
`explainer.py`'s existing `MATCH_DATA` pattern. Each of the six functions
returns `{"formula": str, "inputs": dict, "result": ...}`. `main.py` wires
these into one new endpoint and two modified endpoints. `POST /api/ask`,
`explainer.py`, and `verifier.py` are **not touched** — the existing 52 tests
must stay green throughout.

**Tech Stack:** Python, `math.erf`/`math.sqrt` (no numpy/scipy), FastAPI,
pytest. Spec: `docs/superpowers/specs/2026-06-13-phase2-analytics-models-design.md`.

All commands below are run from the repo root `C:\Users\aleks\matchMind`.

---

### Task 1: Add counterfactual/handball-reaction dossier fields to `sample_match.json`

**Files:**
- Modify: `backend/data/sample_match.json:55` and `:89`
- Test: `tests/test_data.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_data.py`:

```python
def test_offside_27_has_counterfactual_inputs():
    data = load_match()
    moment = data["moments"]["offside_27"]
    assert moment["attacker_speed_ms"] == 7


def test_handball_38_has_reaction_inputs():
    data = load_match()
    moment = data["moments"]["handball_38"]
    assert moment["deflection_distance_m"] == 1.06
    assert moment["ball_speed_ms"] == 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_data.py -v`
Expected: `test_offside_27_has_counterfactual_inputs` and
`test_handball_38_has_reaction_inputs` FAIL with `KeyError: 'attacker_speed_ms'`
and `KeyError: 'deflection_distance_m'`.

- [ ] **Step 3: Add the fields to `sample_match.json`**

In `backend/data/sample_match.json`, the `offside_27` moment currently reads
(around line 54-55):

```json
      "margin_cm": 11,
      "camera_frame_uncertainty_cm": 6,
```

Change to:

```json
      "margin_cm": 11,
      "camera_frame_uncertainty_cm": 6,
      "attacker_speed_ms": 7,
```

The `handball_38` moment currently reads (around line 89):

```json
      "confidence": 0.74,
```

Change to:

```json
      "confidence": 0.74,
      "deflection_distance_m": 1.06,
      "ball_speed_ms": 20,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_data.py -v`
Expected: PASS (all tests, including the two new ones).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (54 tests — 52 existing + 2 new).

- [ ] **Step 6: Commit**

```bash
git add backend/data/sample_match.json tests/test_data.py
git commit -m "feat: add counterfactual and handball-reaction dossier fields"
```

---

### Task 2: Create `backend/data/telemetry.json`

**Files:**
- Create: `backend/data/telemetry.json`
- Test: `tests/test_data.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_data.py`:

```python
TELEMETRY_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "telemetry.json"


def load_telemetry():
    with open(TELEMETRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_telemetry_schema():
    data = load_telemetry()
    assert data["windows"] == ["0-15", "15-30", "30-45", "45-60", "60-75", "75-90"]
    for team in ["home", "away"]:
        for metric in ["sprints", "line_gap_def_mid_m", "long_pass_share", "ppda"]:
            assert len(data["teams"][team][metric]) == 6
    assert data["event_weights_for_momentum"] == {
        "goal": 30,
        "var_review": 15,
        "tactical": 5,
        "substitution": 3,
        "pressure": 10,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_data.py::test_telemetry_schema -v`
Expected: FAIL with `FileNotFoundError` (no `telemetry.json` yet).

- [ ] **Step 3: Create `backend/data/telemetry.json`**

```json
{
  "windows": ["0-15", "15-30", "30-45", "45-60", "60-75", "75-90"],
  "teams": {
    "home": {
      "sprints": [38, 37, 36, 36, 35, 34],
      "line_gap_def_mid_m": [7.5, 7.6, 7.6, 7.7, 7.8, 7.9],
      "long_pass_share": [0.20, 0.20, 0.19, 0.19, 0.18, 0.18],
      "ppda": [9.5, 9.4, 9.3, 9.0, 8.7, 8.5]
    },
    "away": {
      "sprints": [40, 38, 34, 30, 26, 22],
      "line_gap_def_mid_m": [8.0, 8.0, 8.8, 9.6, 10.8, 11.6],
      "long_pass_share": [0.18, 0.18, 0.21, 0.25, 0.29, 0.33],
      "ppda": [9.0, 9.0, 9.8, 10.8, 12.0, 13.2]
    }
  },
  "event_weights_for_momentum": {
    "goal": 30,
    "var_review": 15,
    "tactical": 5,
    "substitution": 3,
    "pressure": 10
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_data.py::test_telemetry_schema -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (55 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/data/telemetry.json tests/test_data.py
git commit -m "feat: add telemetry.json with per-window team data and momentum weights"
```

---

### Task 3: `analytics.py` module skeleton + `offside_probability`

**Files:**
- Create: `backend/engines/analytics.py`
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_analytics.py`:

```python
import pytest

from backend.engines import analytics


def test_offside_probability_for_offside_27():
    result = analytics.offside_probability(11, 6)
    assert result["result"]["z"] == pytest.approx(2.78, abs=0.01)
    assert result["result"]["probability"] == pytest.approx(0.997, abs=0.001)
    assert "formula" in result
    assert result["inputs"] == {
        "margin_cm": 11,
        "camera_frame_uncertainty_cm": 6,
        "sigma_line_cm": 2.5,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.engines.analytics'`.

- [ ] **Step 3: Create `backend/engines/analytics.py`**

```python
import json
import math
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_match.json"
TELEMETRY_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"

with open(DATA_PATH, encoding="utf-8") as _f:
    MATCH_DATA = json.load(_f)

with open(TELEMETRY_PATH, encoding="utf-8") as _f:
    TELEMETRY_DATA = json.load(_f)


def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def offside_probability(margin_cm: float, camera_frame_uncertainty_cm: float, sigma_line_cm: float = 2.5) -> dict:
    sigma_frame = camera_frame_uncertainty_cm / 1.96
    sigma_total = math.sqrt(sigma_frame ** 2 + sigma_line_cm ** 2)
    z = margin_cm / sigma_total
    probability = _phi(z)
    return {
        "formula": "P(offside) = Phi(margin_cm / sqrt((camera_frame_uncertainty_cm / 1.96)^2 + sigma_line_cm^2))",
        "inputs": {
            "margin_cm": margin_cm,
            "camera_frame_uncertainty_cm": camera_frame_uncertainty_cm,
            "sigma_line_cm": sigma_line_cm,
        },
        "result": {"z": round(z, 2), "probability": round(probability, 3)},
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (56 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add analytics module with offside probability model"
```

---

### Task 4: `offside_sensitivity`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_analytics.py`:

```python
def test_offside_sensitivity_for_offside_27():
    result = analytics.offside_sensitivity(11, 6)
    points = result["result"]
    assert len(points) == 6
    sigma_values = [p["sigma_line_cm"] for p in points]
    assert sigma_values == [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    probabilities = [p["probability"] for p in points]
    for p in probabilities:
        assert 0.98 < p < 1.0
    assert probabilities == sorted(probabilities, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py::test_offside_sensitivity_for_offside_27 -v`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'offside_sensitivity'`.

- [ ] **Step 3: Add `offside_sensitivity` to `backend/engines/analytics.py`**

Append to the file:

```python
def offside_sensitivity(margin_cm: float, camera_frame_uncertainty_cm: float) -> dict:
    sigma_line_values = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    result = []
    for sigma_line_cm in sigma_line_values:
        probability = offside_probability(margin_cm, camera_frame_uncertainty_cm, sigma_line_cm)["result"]["probability"]
        result.append({"sigma_line_cm": sigma_line_cm, "probability": probability})
    return {
        "formula": "Sweep sigma_line_cm over [1.5, 4.0] step 0.5, recomputing P(offside) for each value",
        "inputs": {
            "margin_cm": margin_cm,
            "camera_frame_uncertainty_cm": camera_frame_uncertainty_cm,
            "sigma_line_cm_range": [1.5, 4.0],
        },
        "result": result,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (57 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add offside sensitivity sweep model"
```

---

### Task 5: `counterfactual_timing`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_analytics.py`:

```python
def test_counterfactual_timing_for_offside_27():
    result = analytics.counterfactual_timing(11, 7)
    assert result["result"]["delay_needed_ms"] == pytest.approx(15.7, abs=0.05)
    assert result["inputs"] == {"margin_cm": 11, "attacker_speed_ms": 7}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py::test_counterfactual_timing_for_offside_27 -v`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'counterfactual_timing'`.

- [ ] **Step 3: Add `counterfactual_timing` to `backend/engines/analytics.py`**

Append to the file:

```python
def counterfactual_timing(margin_cm: float, attacker_speed_ms: float) -> dict:
    delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000
    return {
        "formula": "delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000",
        "inputs": {"margin_cm": margin_cm, "attacker_speed_ms": attacker_speed_ms},
        "result": {"delay_needed_ms": round(delay_needed_ms, 1)},
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (58 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add counterfactual timing model"
```

---

### Task 6: `handball_reaction`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_analytics.py`:

```python
def test_handball_reaction_for_handball_38():
    result = analytics.handball_reaction(1.06, 20)
    assert result["result"]["time_available_ms"] == 53.0
    assert result["result"]["deficit_ratio"] == pytest.approx(4.72, abs=0.01)
    assert result["inputs"] == {
        "deflection_distance_m": 1.06,
        "ball_speed_ms": 20,
        "reaction_benchmark_ms": 250,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py::test_handball_reaction_for_handball_38 -v`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'handball_reaction'`.

- [ ] **Step 3: Add `handball_reaction` to `backend/engines/analytics.py`**

Append to the file:

```python
def handball_reaction(deflection_distance_m: float, ball_speed_ms: float, reaction_benchmark_ms: float = 250) -> dict:
    time_available_ms = deflection_distance_m / ball_speed_ms * 1000
    deficit_ratio = reaction_benchmark_ms / time_available_ms
    return {
        "formula": "time_available_ms = deflection_distance_m / ball_speed_ms * 1000; deficit_ratio = reaction_benchmark_ms / time_available_ms",
        "inputs": {
            "deflection_distance_m": deflection_distance_m,
            "ball_speed_ms": ball_speed_ms,
            "reaction_benchmark_ms": reaction_benchmark_ms,
        },
        "result": {
            "time_available_ms": round(time_available_ms, 1),
            "deficit_ratio": round(deficit_ratio, 2),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (59 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add handball reaction model"
```

---

### Task 7: `fatigue_index`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_analytics.py`:

```python
def test_fatigue_index_away_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_index(telemetry)
    index = result["result"]["fatigue_index"]
    assert len(index) == 6
    assert index[2] == pytest.approx(12.1, abs=0.1)
    assert index[4] == pytest.approx(40.7, abs=0.1)
    assert index[5] == pytest.approx(54.6, abs=0.1)


def test_fatigue_index_home_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    result = analytics.fatigue_index(telemetry)
    index = result["result"]["fatigue_index"]
    assert len(index) == 6
    assert index[4] == pytest.approx(-2.0, abs=0.1)
```

Note: the away team's fatigue index rises through all 6 windows
(`[-0.6, 0.6, 12.1, 25.5, 40.7, 54.6]`) — window 5 is the largest, not window 4.
Window 4 (≈+41, covering minute 71) is still a sharp decline relative to the
baseline, which is what `fatigue_71`'s narrative describes; the test above
checks the specific window-4 and window-5 values rather than claiming window 4
is the maximum.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -k fatigue -v`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'fatigue_index'`.

- [ ] **Step 3: Add `fatigue_index` to `backend/engines/analytics.py`**

Append to the file:

```python
def fatigue_index(team_telemetry: dict) -> dict:
    sprints = team_telemetry["sprints"]
    line_gap = team_telemetry["line_gap_def_mid_m"]
    long_pass = team_telemetry["long_pass_share"]
    ppda = team_telemetry["ppda"]

    baseline_sprints = (sprints[0] + sprints[1]) / 2
    baseline_line_gap = (line_gap[0] + line_gap[1]) / 2
    baseline_long_pass = (long_pass[0] + long_pass[1]) / 2
    baseline_ppda = (ppda[0] + ppda[1]) / 2

    sprint_decline = []
    line_stretch = []
    long_pass_drift = []
    pressing_decay = []
    index = []
    for i in range(len(sprints)):
        sd = (baseline_sprints - sprints[i]) / baseline_sprints
        ls = (line_gap[i] - baseline_line_gap) / baseline_line_gap
        lpd = (long_pass[i] - baseline_long_pass) / baseline_long_pass
        pd = (ppda[i] - baseline_ppda) / baseline_ppda
        sprint_decline.append(round(sd, 4))
        line_stretch.append(round(ls, 4))
        long_pass_drift.append(round(lpd, 4))
        pressing_decay.append(round(pd, 4))
        index.append(round(100 * (sd + ls + lpd + pd) / 4, 1))

    return {
        "formula": (
            "fatigue_index[i] = 100 * mean(sprint_decline[i], line_stretch[i], "
            "long_pass_drift[i], pressing_decay[i]); baselines = mean(window0, window1)"
        ),
        "inputs": {
            "sprints": sprints,
            "line_gap_def_mid_m": line_gap,
            "long_pass_share": long_pass,
            "ppda": ppda,
        },
        "result": {
            "sprint_decline": sprint_decline,
            "line_stretch": line_stretch,
            "long_pass_drift": long_pass_drift,
            "pressing_decay": pressing_decay,
            "fatigue_index": index,
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (61 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add fatigue index model"
```

---

### Task 8: `momentum_curve`

**Files:**
- Modify: `backend/engines/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_analytics.py`:

```python
def test_momentum_curve_shape_and_values():
    events = analytics.MATCH_DATA["events"]
    weights = analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    curve = analytics.momentum_curve(events, weights)
    assert len(curve) == 19
    minutes = [p["minute"] for p in curve]
    assert minutes == list(range(0, 91, 5))
    by_minute = {p["minute"]: p["value"] for p in curve}
    assert by_minute[15] == 0
    assert by_minute[20] == pytest.approx(-29.0, abs=0.5)
    assert by_minute[65] == pytest.approx(24.6, abs=0.5)
    assert by_minute[90] == pytest.approx(41.0, abs=0.5)
    assert by_minute[65] < by_minute[90]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py::test_momentum_curve_shape_and_values -v`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'momentum_curve'`.

- [ ] **Step 3: Add `momentum_curve` to `backend/engines/analytics.py`**

Append to the file:

```python
def momentum_curve(events: list, event_weights: dict, decay: float = 0.85) -> list:
    minutes = range(0, 91, 5)
    curve = []
    for t in minutes:
        value = 0.0
        for event in events:
            if event["minute"] <= t:
                weight = event_weights[event["type"]]
                direction = 1 if event["team"] == "home" else -1
                if event["type"] == "pressure":
                    direction = -direction
                value += weight * direction * decay ** ((t - event["minute"]) / 5)
        curve.append({"minute": t, "value": round(value, 1)})
    return curve
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v`
Expected: PASS (8 tests in this file).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (62 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add momentum curve model"
```

---

### Task 9: `GET /api/analytics` endpoint

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_api.py`:

```python
def test_analytics_endpoint_has_all_six_models():
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    for key in [
        "offside_probability",
        "offside_sensitivity",
        "counterfactual_timing",
        "handball_reaction",
        "fatigue_index",
        "momentum_curve",
    ]:
        assert key in data, key
        for subkey in ["formula", "inputs", "result"]:
            assert subkey in data[key], (key, subkey)
    assert data["offside_probability"]["result"]["probability"] == pytest.approx(0.997, abs=0.001)
    assert data["counterfactual_timing"]["result"]["delay_needed_ms"] == pytest.approx(15.7, abs=0.05)
    assert data["handball_reaction"]["result"]["time_available_ms"] == 53.0
    assert "home" in data["fatigue_index"]["result"]
    assert "away" in data["fatigue_index"]["result"]
    assert len(data["momentum_curve"]["result"]) == 19
```

This test needs `pytest` imported in `tests/test_api.py`. Check the top of
`tests/test_api.py` — if `import pytest` is not already there, add it as the
first line.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api.py::test_analytics_endpoint_has_all_six_models -v`
Expected: FAIL with `404 Not Found` (status code assertion fails — route doesn't exist).

- [ ] **Step 3: Add the `/api/analytics` endpoint to `backend/main.py`**

Add the import near the top of `backend/main.py` (alongside the existing
`backend.engines` imports):

```python
from backend.engines import analytics, explainer
```

This replaces the existing line `from backend.engines import explainer`.

Add the new route after the `/api/moment/{moment_id}` route (after line 51,
before the `VALID_PERSONAS` definition):

```python
@app.get("/api/analytics")
def analytics_endpoint():
    offside = explainer.MATCH_DATA["moments"]["offside_27"]
    handball = explainer.MATCH_DATA["moments"]["handball_38"]
    telemetry = analytics.TELEMETRY_DATA
    home_fatigue = analytics.fatigue_index(telemetry["teams"]["home"])
    away_fatigue = analytics.fatigue_index(telemetry["teams"]["away"])
    return {
        "offside_probability": analytics.offside_probability(
            offside["margin_cm"], offside["camera_frame_uncertainty_cm"]
        ),
        "offside_sensitivity": analytics.offside_sensitivity(
            offside["margin_cm"], offside["camera_frame_uncertainty_cm"]
        ),
        "counterfactual_timing": analytics.counterfactual_timing(
            offside["margin_cm"], offside["attacker_speed_ms"]
        ),
        "handball_reaction": analytics.handball_reaction(
            handball["deflection_distance_m"], handball["ball_speed_ms"]
        ),
        "fatigue_index": {
            "formula": home_fatigue["formula"],
            "inputs": {"windows": telemetry["windows"]},
            "result": {"home": home_fatigue["result"], "away": away_fatigue["result"]},
        },
        "momentum_curve": {
            "formula": (
                "momentum(t) = sum over events e where e.minute <= t of "
                "weight(e.type) * direction(e) * decay^((t - e.minute) / 5)"
            ),
            "inputs": {"decay": 0.85, "event_weights": telemetry["event_weights_for_momentum"]},
            "result": analytics.momentum_curve(
                explainer.MATCH_DATA["events"], telemetry["event_weights_for_momentum"]
            ),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py -v`
Expected: PASS (all tests, including the new one).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (63 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: add GET /api/analytics endpoint"
```

---

### Task 10: `/api/match` momentum becomes computed

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_api.py`:

```python
def test_match_momentum_is_computed_curve():
    response = client.get("/api/match")
    assert response.status_code == 200
    data = response.json()
    momentum = data["momentum"]
    assert len(momentum) == 19
    for point in momentum:
        assert "minute" in point and "value" in point
    minutes = [p["minute"] for p in momentum]
    assert minutes == list(range(0, 91, 5))
```

- [ ] **Step 2: Add a value-based assertion, then run the test to verify it fails**

The static `momentum` array in `sample_match.json` also has 19 entries at
minutes 0-90 step 5, so a shape-only test would pass before the source is
switched. Add one more assertion to `test_match_momentum_is_computed_curve`
that distinguishes the static array from the computed curve:

```python
    by_minute = {p["minute"]: p["value"] for p in momentum}
    assert by_minute[20] == pytest.approx(-29.0, abs=0.5)
```

The static array has `{"minute": 20, "value": -25}`, while the computed curve
gives `≈-29.0` at minute 20 — so this assertion fails until `/api/match` is
switched to `analytics.momentum_curve(...)`.

Run: `python -m pytest tests/test_api.py::test_match_momentum_is_computed_curve -v`
Expected: FAIL — `assert -25 == approx(-29.0 ± 5.0e-01)`.

- [ ] **Step 3: Switch `/api/match`'s momentum field to the computed curve**

In `backend/main.py`, the `/api/match` route currently reads:

```python
@app.get("/api/match")
def match():
    data = explainer.MATCH_DATA
    return {
        "match_id": data["match_id"],
        "competition": data["competition"],
        "home": data["home"],
        "away": data["away"],
        "score": data["score"],
        "events": data["events"],
        "momentum": data["momentum"],
    }
```

Change the `"momentum"` line to:

```python
        "momentum": analytics.momentum_curve(data["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (64 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: compute /api/match momentum from momentum_curve"
```

---

### Task 11: `/api/moment/{id}` gains `"analytics"` key

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api.py`:

```python
def test_moment_offside_27_has_analytics():
    response = client.get("/api/moment/offside_27")
    assert response.status_code == 200
    data = response.json()
    analytics_data = data["analytics"]
    for key in ["offside_probability", "offside_sensitivity", "counterfactual_timing"]:
        assert key in analytics_data, key
    assert analytics_data["offside_probability"]["result"]["probability"] == pytest.approx(0.997, abs=0.001)


def test_moment_handball_38_has_analytics():
    response = client.get("/api/moment/handball_38")
    assert response.status_code == 200
    data = response.json()
    assert "handball_reaction" in data["analytics"]
    assert data["analytics"]["handball_reaction"]["result"]["time_available_ms"] == 53.0


def test_moment_fatigue_71_has_analytics():
    response = client.get("/api/moment/fatigue_71")
    assert response.status_code == 200
    data = response.json()
    fatigue = data["analytics"]["fatigue_index"]
    assert "home" in fatigue and "away" in fatigue
    assert fatigue["away"]["fatigue_index"][4] == pytest.approx(40.7, abs=0.1)


def test_moment_halftime_shift_has_null_analytics():
    response = client.get("/api/moment/halftime_shift")
    assert response.status_code == 200
    assert response.json()["analytics"] is None


def test_moment_sub_58_has_null_analytics():
    response = client.get("/api/moment/sub_58")
    assert response.status_code == 200
    assert response.json()["analytics"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api.py -k "analytics and moment" -v`
Expected: FAIL with `KeyError: 'analytics'`.

- [ ] **Step 3: Add the analytics wiring to `backend/main.py`**

Add a helper function before the `/api/moment/{moment_id}` route:

```python
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
        }
    return None
```

Then change the `/api/moment/{moment_id}` route from:

```python
@app.get("/api/moment/{moment_id}")
def moment(moment_id: str):
    moments = explainer.MATCH_DATA["moments"]
    if moment_id not in moments:
        raise HTTPException(status_code=404, detail=f"Unknown moment id: {moment_id!r}")
    return moments[moment_id]
```

to:

```python
@app.get("/api/moment/{moment_id}")
def moment(moment_id: str):
    moments = explainer.MATCH_DATA["moments"]
    if moment_id not in moments:
        raise HTTPException(status_code=404, detail=f"Unknown moment id: {moment_id!r}")
    result = dict(moments[moment_id])
    result["analytics"] = _moment_analytics(moment_id, moments[moment_id])
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_api.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python -m pytest -v`
Expected: PASS (69 tests — 64 + 5 new).

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: add analytics key to /api/moment/{id}"
```

---

## Final check

After Task 11, run the full suite one more time:

```bash
python -m pytest -v
```

Expected: all 69 tests pass. `POST /api/ask`, `explainer.py`, and
`verifier.py` were never touched, so the original 52 Phase 1 tests (12 in
`test_api.py` not counting new ones, plus `test_data.py`, `test_explainer.py`,
`test_verifier.py`, etc.) remain green.
