# Phase 3: Analytics Polish — Design

**Goal:** Deepen all 6 computed analytics models in `backend/engines/analytics.py` with input validation, additional derived/explainability fields, and (for fatigue and momentum) new comparison/summary functions — without adding dependencies or breaking the existing `{formula, inputs, result}` API contract (except one deliberate, documented schema change).

**Context:** Phase 1 (core pipeline) and Phase 2 (the 6 base analytics models + API wiring) are complete, merged-ready on `feature/phase2-analytics-models`, 69/69 tests passing. This phase polishes those 6 models in place.

**Constraints:**
- Pure Python only (`math`, stdlib) — no numpy/scipy, per CLAUDE.md.
- All new fields are additive within each model's existing `result` dict, EXCEPT `offside_sensitivity` (see Schema Change below).
- Validation errors raise `ValueError` with a descriptive message.

---

## Shared convention: validation

Every model that divides by a user-supplied value or takes a value that must be positive validates it up front and raises `ValueError("<param> must be positive, got <value>")` (or similarly descriptive). This applies to:
- `offside_probability`: `sigma_line_cm > 0`, `camera_frame_uncertainty_cm >= 0`
- `counterfactual_timing`: `attacker_speed_ms > 0`
- `handball_reaction`: `deflection_distance_m > 0`, `ball_speed_ms > 0`
- `fatigue_index`: each baseline (`mean(window0, window1)` per metric) must be nonzero
- `momentum_curve`: every `event["type"]` present in `events` must be a key in `event_weights`

---

## Model 1: `offside_probability` — add `verdict`

No schema change. Add a `verdict` key to `result` classifying the probability:

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

Demo (margin=11cm, frame_uncertainty=6cm): `probability=0.997` → `verdict="near-certain offside"`.

`result` becomes: `{"z": 2.78, "probability": 0.997, "verdict": "near-certain offside"}`

---

## Model 2: `offside_sensitivity` — SCHEMA CHANGE

**This is the one deliberate breaking change.** `result` changes from a bare list to a dict:

```python
{
    "sweep": [{"sigma_line_cm": 1.5, "probability": 0.999}, ...],   # same 6 entries as before
    "min_probability": 0.986,
    "max_probability": 0.999,
    "robust": True,   # min_probability >= 0.95
}
```

Demo values: sweep unchanged (sigma_line 1.5→4.0: probabilities 0.999, 0.999, 0.997, 0.995, 0.991, 0.986), `min_probability=0.986`, `max_probability=0.999`, `robust=True`.

**Impact:** The existing Phase 2 test for `offside_sensitivity` (which asserts `result` is a list) must be updated to assert `result["sweep"]` instead, plus new assertions for `min_probability`, `max_probability`, `robust`. No main.py changes needed — `/api/analytics` and `/api/moment/offside_27` already pass this dict through as-is.

---

## Model 3: `counterfactual_timing` — add frame-based fields

Add to `result`:
- `frames_at_50fps = round(delay_needed_ms / 20, 2)` (20ms = 1 frame at 50fps)
- `frames_at_25fps = round(delay_needed_ms / 40, 2)` (40ms = 1 frame at 25fps)
- `detectable_at_50fps = frames_at_50fps >= 1` (bool)

Demo (delay=15.7ms): `frames_at_50fps=0.78`, `frames_at_25fps=0.39`, `detectable_at_50fps=False` — directly supports the "less than one broadcast frame" claim with concrete numbers.

`result` becomes: `{"delay_needed_ms": 15.7, "frames_at_50fps": 0.78, "frames_at_25fps": 0.39, "detectable_at_50fps": false}`

---

## Model 4: `handball_reaction` — add `verdict` and `benchmark_sensitivity`

Add to `result`:
- `verdict`: `"exceeds human reaction limits"` if `deficit_ratio > 1` else `"within human reaction limits"`
- `benchmark_sensitivity`: sweep of `deficit_ratio` across reaction benchmarks `[150, 200, 250, 300]` ms:

```python
[
    {"reaction_benchmark_ms": 150, "deficit_ratio": 2.83},
    {"reaction_benchmark_ms": 200, "deficit_ratio": 3.77},
    {"reaction_benchmark_ms": 250, "deficit_ratio": 4.72},
    {"reaction_benchmark_ms": 300, "deficit_ratio": 5.66},
]
```

(deficit_ratio = benchmark_ms / time_available_ms; time_available_ms=53.0 for the demo)

Demo: `verdict="exceeds human reaction limits"` (4.72 > 1).

---

## Model 5: `fatigue_index` — add `peak_window` and `trend`, plus new `fatigue_comparison`

### 5a. Additions to `fatigue_index(team_telemetry)` result

- `peak_window`: the window label (from `["0-15","15-30","30-45","45-60","60-75","75-90"]`) at the index where `fatigue_index` list is maximum
- `trend`: compare `fatigue_index[-1]` to `fatigue_index[2]` (first post-baseline window):
  - `diff = fatigue_index[-1] - fatigue_index[2]`
  - `"increasing"` if `diff > 5`, `"decreasing"` if `diff < -5`, else `"stable"`

Demo values:
- Home: `index=[-0.4, 0.4, -0.5, -0.9, -2.0, -1.5]` → `peak_window="15-30"` (value 0.4), `trend="stable"` (diff=-1.0)
- Away: `index=[-0.6, 0.6, 12.1, 25.5, 40.7, 54.6]` → `peak_window="75-90"` (value 54.6), `trend="increasing"` (diff=42.5)

### 5b. New function `fatigue_comparison(home_telemetry, away_telemetry)`

Returns `{formula, inputs, result}` where:

```python
result = {
    "home_fatigue_index": [...],   # home's fatigue_index list
    "away_fatigue_index": [...],   # away's fatigue_index list
    "difference": [...],           # away[i] - home[i] for each window
    "more_fatigued_team": "home" | "away",  # "away" if difference[-1] >= 0, else "home"
}
```

Demo: `difference = [-0.2, 0.2, 12.6, 26.4, 42.7, 56.1]`, `more_fatigued_team="away"` (difference[-1]=56.1 >= 0).

`inputs = {"home": home_telemetry, "away": away_telemetry}` (the 4 raw series per team, same shape as `fatigue_index`'s inputs).

---

## Model 6: `momentum_curve` — add validation, new `momentum_summary` function

### 6a. Validation

Before computing, check every `event["type"]` in `events` has a corresponding key in `event_weights`; raise `ValueError(f"Unknown event type {event['type']!r} — not found in event_weights")` if not. `momentum_curve`'s return shape (`list[dict]`) is unchanged.

### 6b. New function `momentum_summary(curve: list) -> dict`

Not wrapped in `{formula, inputs, result}` — it's a small pure transform of an existing curve, called by `/api/analytics` to augment the momentum section.

```python
def momentum_summary(curve: list) -> dict:
    values = [p["value"] for p in curve]
    peak = max(curve, key=lambda p: abs(p["value"]))
    final_value = curve[-1]["value"]
    return {
        "peak_minute": peak["minute"],
        "peak_value": peak["value"],
        "final_value": final_value,
        "swing": round(max(values) - min(values), 1),
        "dominant_team": "home" if final_value > 0 else ("away" if final_value < 0 else "even"),
    }
```

Demo: `{"peak_minute": 85, "peak_value": 48.2, "final_value": 41.0, "swing": 77.2, "dominant_team": "home"}`

---

## API wiring (`backend/main.py`)

- `offside_probability`, `counterfactual_timing`, `handball_reaction`, `fatigue_index` (per-team): new `result` fields flow through automatically wherever these are returned (`/api/analytics`, `/api/moment/offside_27`, `/api/moment/handball_38`, `/api/moment/fatigue_71`). No main.py changes needed for these.
- `offside_sensitivity`: schema change flows through automatically (same reason). No main.py changes needed.
- `/api/analytics`'s `fatigue_index` section: add a new top-level key `"fatigue_comparison": analytics.fatigue_comparison(telemetry["teams"]["home"], telemetry["teams"]["away"])`.
- `/api/analytics`'s `momentum_curve` section: add a new key `"summary": analytics.momentum_summary(result)` alongside the existing `"result"` key.
- `/api/moment/fatigue_71`: add `fatigue_comparison` result alongside the existing per-team `fatigue_index` results (in `_moment_analytics`).

---

## Testing

For each of the 6 models:
- One new test per validation rule (asserts `pytest.raises(ValueError)`)
- One new test (or extended existing test) asserting the new derived field(s) match the demo values computed above
- `fatigue_comparison`: new test asserting `difference` and `more_fatigued_team` for the demo telemetry
- `momentum_summary`: new test asserting summary fields for the demo curve
- Update the existing `offside_sensitivity` test for the new `result` shape
- `/api/analytics` and `/api/moment/{id}` tests updated/extended to check the new fields are present in responses

Expected final test count: 69 (Phase 2 baseline) + ~14 new/updated tests ≈ 83 tests, all passing.
