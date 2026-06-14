# Phase 3: Analytics Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add input validation and richer derived/explainability fields to all 6 models in `backend/engines/analytics.py`, plus two new comparison/summary functions (`fatigue_comparison`, `momentum_summary`), wired into `/api/analytics` and `/api/moment/fatigue_71`.

**Architecture:** Each model gets validation (raise `ValueError` on bad input) and 1-3 new keys added to its `result` dict, computed inline alongside existing logic. Two new standalone functions are added at the end of `analytics.py`. `backend/main.py` wires the two new functions into the existing `/api/analytics` endpoint and `_moment_analytics` helper. All changes are additive except `offside_sensitivity`, whose `result` changes from a list to a dict (documented schema change).

**Tech Stack:** Pure Python (`math`, stdlib only — no new dependencies), FastAPI, pytest.

**Reference spec:** `docs/superpowers/specs/2026-06-13-phase3-analytics-polish-design.md`

**Starting state:** Branch `feature/phase2-analytics-models`, 69/69 tests passing. `backend/engines/analytics.py` is 139 lines with 7 functions (`_phi`, `offside_probability`, `offside_sensitivity`, `counterfactual_timing`, `handball_reaction`, `fatigue_index`, `momentum_curve`).

---

### Task 1: `offside_probability` — validation + `verdict`

**Files:**
- Modify: `backend/engines/analytics.py` (function `offside_probability`, currently lines 19-33; add helper `_offside_verdict` above it)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_analytics.py` (after `test_offside_probability_for_offside_27`, around line 16):

```python
def test_offside_probability_verdict_for_offside_27():
    result = analytics.offside_probability(11, 6)
    assert result["result"]["verdict"] == "near-certain offside"


def test_offside_probability_rejects_non_positive_sigma_line():
    with pytest.raises(ValueError):
        analytics.offside_probability(11, 6, sigma_line_cm=0)


def test_offside_probability_rejects_negative_frame_uncertainty():
    with pytest.raises(ValueError):
        analytics.offside_probability(11, -1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k offside_probability`
Expected: the 3 new tests FAIL (`KeyError: 'verdict'` and tests expecting `ValueError` don't raise)

- [ ] **Step 3: Implement validation and verdict**

In `backend/engines/analytics.py`, add a helper function immediately after `_phi` (currently lines 15-16):

```python
def _offside_verdict(probability: float) -> str:
    if probability >= 0.95:
        return "near-certain offside"
    if probability >= 0.6:
        return "likely offside"
    if probability >= 0.4:
        return "inconclusive"
    if probability > 0.05:
        return "likely not offside"
    return "near-certain not offside"
```

Replace the `offside_probability` function with:

```python
def offside_probability(margin_cm: float, camera_frame_uncertainty_cm: float, sigma_line_cm: float = 2.5) -> dict:
    if sigma_line_cm <= 0:
        raise ValueError(f"sigma_line_cm must be positive, got {sigma_line_cm}")
    if camera_frame_uncertainty_cm < 0:
        raise ValueError(f"camera_frame_uncertainty_cm must be non-negative, got {camera_frame_uncertainty_cm}")
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
        "result": {
            "z": round(z, 2),
            "probability": round(probability, 3),
            "verdict": _offside_verdict(probability),
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k offside_probability`
Expected: all PASS (4 tests: original + 3 new)

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 72 passed (69 + 3 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add validation and verdict to offside_probability"
```

---

### Task 2: `offside_sensitivity` — schema change (result becomes a dict)

**Files:**
- Modify: `backend/engines/analytics.py` (function `offside_sensitivity`, currently lines 35-50)
- Test: `tests/test_analytics.py` (update existing `test_offside_sensitivity_for_offside_27`, currently lines 18-27)

- [ ] **Step 1: Update the existing test for the new result shape**

Replace `test_offside_sensitivity_for_offside_27` in `tests/test_analytics.py` with:

```python
def test_offside_sensitivity_for_offside_27():
    result = analytics.offside_sensitivity(11, 6)
    sweep = result["result"]["sweep"]
    assert len(sweep) == 6
    sigma_values = [p["sigma_line_cm"] for p in sweep]
    assert sigma_values == [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    probabilities = [p["probability"] for p in sweep]
    for p in probabilities:
        assert 0.98 < p < 1.0
    assert probabilities == sorted(probabilities, reverse=True)
    assert result["result"]["min_probability"] == pytest.approx(0.986, abs=0.001)
    assert result["result"]["max_probability"] == pytest.approx(0.999, abs=0.001)
    assert result["result"]["robust"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py -v -k offside_sensitivity`
Expected: FAIL (`TypeError: list indices must be integers` or `KeyError: 'sweep'`)

- [ ] **Step 3: Implement the schema change**

Replace the `offside_sensitivity` function in `backend/engines/analytics.py` with:

```python
def offside_sensitivity(margin_cm: float, camera_frame_uncertainty_cm: float) -> dict:
    sigma_line_values = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    sweep = []
    for sigma_line_cm in sigma_line_values:
        probability = offside_probability(margin_cm, camera_frame_uncertainty_cm, sigma_line_cm)["result"]["probability"]
        sweep.append({"sigma_line_cm": sigma_line_cm, "probability": probability})
    probabilities = [p["probability"] for p in sweep]
    min_probability = min(probabilities)
    max_probability = max(probabilities)
    return {
        "formula": "Sweep sigma_line_cm over [1.5, 4.0] step 0.5, recomputing P(offside) for each value",
        "inputs": {
            "margin_cm": margin_cm,
            "camera_frame_uncertainty_cm": camera_frame_uncertainty_cm,
            "sigma_line_cm_range": [1.5, 4.0],
        },
        "result": {
            "sweep": sweep,
            "min_probability": min_probability,
            "max_probability": max_probability,
            "robust": min_probability >= 0.95,
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v -k offside_sensitivity`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 72 passed (no new tests added in this task, but verify nothing else broke — `/api/analytics` and `/api/moment/offside_27` only check for key presence, not shape, so they remain green)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: restructure offside_sensitivity result with min/max/robust summary"
```

---

### Task 3: `counterfactual_timing` — validation + frame-based fields

**Files:**
- Modify: `backend/engines/analytics.py` (function `counterfactual_timing`, currently lines 52-59)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_analytics.py` (after `test_counterfactual_timing_for_offside_27`):

```python
def test_counterfactual_timing_frame_fields_for_offside_27():
    result = analytics.counterfactual_timing(11, 7)
    assert result["result"]["frames_at_50fps"] == pytest.approx(0.78, abs=0.01)
    assert result["result"]["frames_at_25fps"] == pytest.approx(0.39, abs=0.01)
    assert result["result"]["detectable_at_50fps"] is False


def test_counterfactual_timing_rejects_non_positive_speed():
    with pytest.raises(ValueError):
        analytics.counterfactual_timing(11, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k counterfactual`
Expected: 2 new tests FAIL (`KeyError: 'frames_at_50fps'`, no `ValueError` raised)

- [ ] **Step 3: Implement validation and frame fields**

Replace the `counterfactual_timing` function in `backend/engines/analytics.py` with:

```python
def counterfactual_timing(margin_cm: float, attacker_speed_ms: float) -> dict:
    if attacker_speed_ms <= 0:
        raise ValueError(f"attacker_speed_ms must be positive, got {attacker_speed_ms}")
    delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000
    frames_at_50fps = round(delay_needed_ms / 20, 2)
    frames_at_25fps = round(delay_needed_ms / 40, 2)
    return {
        "formula": "delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000",
        "inputs": {"margin_cm": margin_cm, "attacker_speed_ms": attacker_speed_ms},
        "result": {
            "delay_needed_ms": round(delay_needed_ms, 1),
            "frames_at_50fps": frames_at_50fps,
            "frames_at_25fps": frames_at_25fps,
            "detectable_at_50fps": frames_at_50fps >= 1,
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k counterfactual`
Expected: all PASS (3 tests: original + 2 new)

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 74 passed (72 + 2 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add validation and broadcast-frame fields to counterfactual_timing"
```

---

### Task 4: `handball_reaction` — validation + `verdict` + `benchmark_sensitivity`

**Files:**
- Modify: `backend/engines/analytics.py` (function `handball_reaction`, currently lines 61-76)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_analytics.py` (after `test_handball_reaction_for_handball_38`):

```python
def test_handball_reaction_verdict_and_sensitivity_for_handball_38():
    result = analytics.handball_reaction(1.06, 20)
    assert result["result"]["verdict"] == "exceeds human reaction limits"
    sensitivity = result["result"]["benchmark_sensitivity"]
    assert [s["reaction_benchmark_ms"] for s in sensitivity] == [150, 200, 250, 300]
    assert [s["deficit_ratio"] for s in sensitivity] == [
        pytest.approx(2.83, abs=0.01),
        pytest.approx(3.77, abs=0.01),
        pytest.approx(4.72, abs=0.01),
        pytest.approx(5.66, abs=0.01),
    ]


def test_handball_reaction_rejects_non_positive_inputs():
    with pytest.raises(ValueError):
        analytics.handball_reaction(0, 20)
    with pytest.raises(ValueError):
        analytics.handball_reaction(1.06, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k handball`
Expected: 2 new tests FAIL (`KeyError: 'verdict'`, no `ValueError` raised)

- [ ] **Step 3: Implement validation, verdict, and benchmark sensitivity**

Replace the `handball_reaction` function in `backend/engines/analytics.py` with:

```python
def handball_reaction(deflection_distance_m: float, ball_speed_ms: float, reaction_benchmark_ms: float = 250) -> dict:
    if deflection_distance_m <= 0:
        raise ValueError(f"deflection_distance_m must be positive, got {deflection_distance_m}")
    if ball_speed_ms <= 0:
        raise ValueError(f"ball_speed_ms must be positive, got {ball_speed_ms}")
    time_available_ms = deflection_distance_m / ball_speed_ms * 1000
    deficit_ratio = reaction_benchmark_ms / time_available_ms
    benchmark_sensitivity = [
        {"reaction_benchmark_ms": benchmark_ms, "deficit_ratio": round(benchmark_ms / time_available_ms, 2)}
        for benchmark_ms in [150, 200, 250, 300]
    ]
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
            "verdict": "exceeds human reaction limits" if deficit_ratio > 1 else "within human reaction limits",
            "benchmark_sensitivity": benchmark_sensitivity,
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k handball`
Expected: all PASS (3 tests: original + 2 new)

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 76 passed (74 + 2 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add validation, verdict, and benchmark sensitivity to handball_reaction"
```

---

### Task 5: `fatigue_index` — validation + `peak_window` + `trend`

**Files:**
- Modify: `backend/engines/analytics.py` (function `fatigue_index`, currently lines 78-124)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_analytics.py` (after `test_fatigue_index_home_team`):

```python
def test_fatigue_index_peak_and_trend_for_away_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_index(telemetry)
    assert result["result"]["peak_window"] == "75-90"
    assert result["result"]["trend"] == "increasing"


def test_fatigue_index_peak_and_trend_for_home_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    result = analytics.fatigue_index(telemetry)
    assert result["result"]["peak_window"] == "15-30"
    assert result["result"]["trend"] == "stable"


def test_fatigue_index_rejects_zero_baseline():
    telemetry = {
        "sprints": [0, 0, 10, 10, 10, 10],
        "line_gap_def_mid_m": [7.5, 7.6, 7.6, 7.7, 7.8, 7.9],
        "long_pass_share": [0.20, 0.20, 0.19, 0.19, 0.18, 0.18],
        "ppda": [9.5, 9.4, 9.3, 9.0, 8.7, 8.5],
    }
    with pytest.raises(ValueError):
        analytics.fatigue_index(telemetry)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analytics.py -v -k fatigue_index`
Expected: 3 new tests FAIL (`KeyError: 'peak_window'`, no `ValueError` raised for zero baseline — instead `ZeroDivisionError`)

- [ ] **Step 3: Implement validation, peak_window, and trend**

Replace the `fatigue_index` function in `backend/engines/analytics.py` with:

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

    for name, baseline in [
        ("sprints", baseline_sprints),
        ("line_gap_def_mid_m", baseline_line_gap),
        ("long_pass_share", baseline_long_pass),
        ("ppda", baseline_ppda),
    ]:
        if baseline == 0:
            raise ValueError(f"baseline value for '{name}' is zero — cannot compute fatigue index")

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

    windows = TELEMETRY_DATA["windows"]
    peak_window = windows[index.index(max(index))]
    trend_diff = index[-1] - index[2]
    if trend_diff > 5:
        trend = "increasing"
    elif trend_diff < -5:
        trend = "decreasing"
    else:
        trend = "stable"

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
            "peak_window": peak_window,
            "trend": trend,
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analytics.py -v -k fatigue_index`
Expected: all PASS (5 tests: 2 original + 3 new)

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 79 passed (76 + 3 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add validation, peak_window, and trend to fatigue_index"
```

---

### Task 6: New function `fatigue_comparison`

**Files:**
- Modify: `backend/engines/analytics.py` (add new function after `fatigue_index`)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_analytics.py` (after the fatigue_index tests):

```python
def test_fatigue_comparison_demo_telemetry():
    teams = analytics.TELEMETRY_DATA["teams"]
    result = analytics.fatigue_comparison(teams["home"], teams["away"])
    difference = result["result"]["difference"]
    assert len(difference) == 6
    assert difference[-1] == pytest.approx(56.1, abs=0.1)
    assert result["result"]["more_fatigued_team"] == "away"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py -v -k fatigue_comparison`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'fatigue_comparison'`

- [ ] **Step 3: Implement `fatigue_comparison`**

Add this function to `backend/engines/analytics.py` immediately after `fatigue_index`:

```python
def fatigue_comparison(home_telemetry: dict, away_telemetry: dict) -> dict:
    home_index = fatigue_index(home_telemetry)["result"]["fatigue_index"]
    away_index = fatigue_index(away_telemetry)["result"]["fatigue_index"]
    difference = [round(away_index[i] - home_index[i], 1) for i in range(len(home_index))]
    more_fatigued_team = "away" if difference[-1] >= 0 else "home"
    return {
        "formula": "difference[i] = away_fatigue_index[i] - home_fatigue_index[i]; more_fatigued_team based on sign of difference[-1]",
        "inputs": {"home": home_telemetry, "away": away_telemetry},
        "result": {
            "home_fatigue_index": home_index,
            "away_fatigue_index": away_index,
            "difference": difference,
            "more_fatigued_team": more_fatigued_team,
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v -k fatigue_comparison`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 80 passed (79 + 1 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add fatigue_comparison function"
```

---

### Task 7: `momentum_curve` — validate event types against `event_weights`

**Files:**
- Modify: `backend/engines/analytics.py` (function `momentum_curve`, currently lines 126-139)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_analytics.py` (after `test_momentum_curve_shape_and_values`):

```python
def test_momentum_curve_rejects_unknown_event_type():
    events = [{"minute": 10, "type": "unknown_event", "team": "home"}]
    weights = analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    with pytest.raises(ValueError):
        analytics.momentum_curve(events, weights)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py -v -k momentum_curve`
Expected: FAIL — currently raises `KeyError` instead of `ValueError`

- [ ] **Step 3: Add validation**

Replace the `momentum_curve` function in `backend/engines/analytics.py` with:

```python
def momentum_curve(events: list, event_weights: dict, decay: float = 0.85) -> list:
    for event in events:
        if event["type"] not in event_weights:
            raise ValueError(f"Unknown event type {event['type']!r} — not found in event_weights")
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

Run: `python -m pytest tests/test_analytics.py -v -k momentum_curve`
Expected: all PASS (2 tests: original + 1 new)

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 81 passed (80 + 1 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: validate event types in momentum_curve"
```

---

### Task 8: New function `momentum_summary`

**Files:**
- Modify: `backend/engines/analytics.py` (add new function after `momentum_curve`, at end of file)
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_analytics.py` (after the momentum_curve tests):

```python
def test_momentum_summary_for_demo_curve():
    events = analytics.MATCH_DATA["events"]
    weights = analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    curve = analytics.momentum_curve(events, weights)
    summary = analytics.momentum_summary(curve)
    assert summary["peak_minute"] == 85
    assert summary["peak_value"] == pytest.approx(48.2, abs=0.1)
    assert summary["final_value"] == pytest.approx(41.0, abs=0.1)
    assert summary["swing"] == pytest.approx(77.2, abs=0.1)
    assert summary["dominant_team"] == "home"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analytics.py -v -k momentum_summary`
Expected: FAIL with `AttributeError: module 'backend.engines.analytics' has no attribute 'momentum_summary'`

- [ ] **Step 3: Implement `momentum_summary`**

Add this function to the end of `backend/engines/analytics.py`:

```python
def momentum_summary(curve: list) -> dict:
    values = [p["value"] for p in curve]
    peak = max(curve, key=lambda p: abs(p["value"]))
    final_value = curve[-1]["value"]
    if final_value > 0:
        dominant_team = "home"
    elif final_value < 0:
        dominant_team = "away"
    else:
        dominant_team = "even"
    return {
        "peak_minute": peak["minute"],
        "peak_value": peak["value"],
        "final_value": final_value,
        "swing": round(max(values) - min(values), 1),
        "dominant_team": dominant_team,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analytics.py -v -k momentum_summary`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: 82 passed (81 + 1 new)

- [ ] **Step 6: Commit**

```bash
git add backend/engines/analytics.py tests/test_analytics.py
git commit -m "feat: add momentum_summary function"
```

---

### Task 9: Wire `fatigue_comparison` and `momentum_summary` into the API

**Files:**
- Modify: `backend/main.py` (function `analytics_endpoint`, currently lines 86-121; function `_moment_analytics`, currently lines 46-73)
- Test: `tests/test_api.py` (update `test_analytics_endpoint_has_all_six_models` at line 130, and `test_moment_fatigue_71_has_analytics` at line 185)

- [ ] **Step 1: Update the failing tests**

In `tests/test_api.py`, replace `test_analytics_endpoint_has_all_six_models` with:

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
    assert "fatigue_comparison" in data
    assert data["fatigue_comparison"]["result"]["more_fatigued_team"] == "away"
    assert "summary" in data["momentum_curve"]
    assert data["momentum_curve"]["summary"]["dominant_team"] == "home"
```

Replace `test_moment_fatigue_71_has_analytics` with:

```python
def test_moment_fatigue_71_has_analytics():
    response = client.get("/api/moment/fatigue_71")
    assert response.status_code == 200
    data = response.json()
    fatigue = data["analytics"]["fatigue_index"]
    assert "home" in fatigue and "away" in fatigue
    assert fatigue["away"]["fatigue_index"][4] == pytest.approx(40.7, abs=0.1)
    comparison = data["analytics"]["fatigue_comparison"]
    assert comparison["more_fatigued_team"] == "away"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api.py -v -k "analytics_endpoint or fatigue_71"`
Expected: FAIL — `KeyError: 'fatigue_comparison'` / `KeyError: 'summary'`

- [ ] **Step 3: Wire the new functions into `/api/analytics`**

Replace the `analytics_endpoint` function in `backend/main.py` with:

```python
@app.get("/api/analytics")
def analytics_endpoint():
    offside = explainer.MATCH_DATA["moments"]["offside_27"]
    handball = explainer.MATCH_DATA["moments"]["handball_38"]
    telemetry = analytics.TELEMETRY_DATA
    home_fatigue = analytics.fatigue_index(telemetry["teams"]["home"])
    away_fatigue = analytics.fatigue_index(telemetry["teams"]["away"])
    momentum = analytics.momentum_curve(
        explainer.MATCH_DATA["events"], telemetry["event_weights_for_momentum"]
    )
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
        "fatigue_comparison": analytics.fatigue_comparison(
            telemetry["teams"]["home"], telemetry["teams"]["away"]
        ),
        "momentum_curve": {
            "formula": (
                "momentum(t) = sum over events e where e.minute <= t of "
                "weight(e.type) * direction(e) * decay^((t - e.minute) / 5)"
            ),
            "inputs": {"decay": 0.85, "event_weights": telemetry["event_weights_for_momentum"]},
            "result": momentum,
            "summary": analytics.momentum_summary(momentum),
        },
    }
```

- [ ] **Step 4: Wire `fatigue_comparison` into `/api/moment/fatigue_71`**

In `backend/main.py`, replace the `fatigue_71` branch of `_moment_analytics`:

```python
    if moment_id == "fatigue_71":
        telemetry = analytics.TELEMETRY_DATA
        return {
            "fatigue_index": {
                "home": analytics.fatigue_index(telemetry["teams"]["home"])["result"],
                "away": analytics.fatigue_index(telemetry["teams"]["away"])["result"],
            },
        }
```

with:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_api.py -v -k "analytics_endpoint or fatigue_71"`
Expected: all PASS

- [ ] **Step 6: Run full suite**

Run: `python -m pytest -q`
Expected: 82 passed (no new tests added, 2 existing tests updated)

- [ ] **Step 7: Commit**

```bash
git add backend/main.py tests/test_api.py
git commit -m "feat: wire fatigue_comparison and momentum_summary into API"
```

---

## Final check

After Task 9, run the full suite once more:

```bash
python -m pytest -q
```

Expected: **82 passed** (69 baseline + 13 new tests across Tasks 1, 3, 4, 5, 6, 7, 8).
