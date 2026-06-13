# MatchMind Phase 2 — Analytics Models Design

## Goal

Add `backend/engines/analytics.py`, a pure-Python module implementing the six
computed analytics models documented in `CLAUDE.md`, plus the supporting data
(`backend/data/telemetry.json` and two new dossier fields in
`sample_match.json`). Expose the results via a new `GET /api/analytics`
endpoint and additive fields on `GET /api/match` and
`GET /api/moment/{id}`. `POST /api/ask`, `explainer.py`, and `verifier.py` are
**not modified** in this phase — Phase 1's 52 tests stay green untouched.

This phase delivers the "Computed analytics, not narration" principle: every
number in the eventual UI traces back to an explicit formula, explicit
inputs, and an explicit result, all returned by the API.

## Architecture

```
backend/engines/analytics.py
  offside_probability(margin_cm, camera_frame_uncertainty_cm, sigma_line_cm=2.5) -> dict
  offside_sensitivity(margin_cm, camera_frame_uncertainty_cm) -> dict
  counterfactual_timing(margin_cm, attacker_speed_ms) -> dict
  handball_reaction(deflection_distance_m, ball_speed_ms, reaction_benchmark_ms=250) -> dict
  fatigue_index(team_telemetry: dict) -> dict
  momentum_curve(events: list, event_weights: dict, decay=0.85) -> list[dict]
```

Each function:
- Takes plain Python types (no module-level singletons except reading
  `MATCH_DATA`/`TELEMETRY_DATA` at import time, mirroring `explainer.py`'s
  pattern of loading `sample_match.json`).
- Returns a dict shaped `{"formula": "<human-readable formula string>",
  "inputs": {...}, "result": ...}` so every endpoint that surfaces these
  values can show its derivation.
- Uses only `math` (for `erf`, `sqrt`) — no numpy/scipy, consistent with
  CLAUDE.md's dependency-free principle.

## The six models

### 1. Offside probability

```
sigma_frame = camera_frame_uncertainty_cm / 1.96
sigma_total = sqrt(sigma_frame^2 + sigma_line_cm^2)   # sigma_line_cm default 2.5
z = margin_cm / sigma_total
P(offside) = Phi(z)   # standard normal CDF via math.erf
```

For `offside_27` (margin_cm=11, camera_frame_uncertainty_cm=6):
`sigma_frame ≈ 3.061`, `sigma_total ≈ 3.953`, `z ≈ 2.78`, `P ≈ 0.997` (99.7%).
Matches the documented demo value exactly.

### 2. Offside sensitivity analysis

Sweeps `sigma_line_cm` over `[1.5, 2.0, 2.5, 3.0, 3.5, 4.0]` (step 0.5),
holding `margin_cm` and `camera_frame_uncertainty_cm` fixed, calling
`offside_probability` for each. For `offside_27` this produces probabilities
ranging from ≈98.5% (sigma_line=4.0) to ≈99.9% (sigma_line=1.5) — proving
`P(offside)` is stable (>98%) across plausible skeletal-tracking
implementations, as CLAUDE.md claims.

### 3. Counterfactual timing

```
delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000
```

For `offside_27` (margin_cm=11, attacker_speed_ms=7): `delay_needed_ms ≈
15.7`. Matches the documented counterfactual ("If the attacker had timed the
run about 15.7 ms later...") exactly.

**New dossier field**: `sample_match.json` → `moments.offside_27` gains
`"attacker_speed_ms": 7`.

### 4. Handball reaction

```
time_available_ms = deflection_distance_m / ball_speed_ms * 1000
deficit_ratio = reaction_benchmark_ms / time_available_ms   # reaction_benchmark_ms default 250
```

For `handball_38` (deflection_distance_m=1.06, ball_speed_ms=20):
`time_available_ms = 53.0`, `deficit_ratio ≈ 4.7`. Matches the documented
values ("approximately 53 ms", "about 4.7 times longer than the 53 ms
available") exactly.

**New dossier fields**: `sample_match.json` → `moments.handball_38` gains
`"deflection_distance_m": 1.06, "ball_speed_ms": 20`.

### 5. Fatigue index

```
baseline_x = mean(window[0].x, window[1].x)     # first 30 minutes, for each metric x
sprint_decline[i]  = (baseline_sprints - sprints[i]) / baseline_sprints
line_stretch[i]    = (line_gap[i] - baseline_line_gap) / baseline_line_gap
long_pass_drift[i] = (long_pass[i] - baseline_long_pass) / baseline_long_pass
pressing_decay[i]  = (ppda[i] - baseline_ppda) / baseline_ppda
fatigue_index[i]   = 100 * mean(sprint_decline[i], line_stretch[i], long_pass_drift[i], pressing_decay[i])
```

Computed for all 6 windows, for both teams. `fatigue_index(team_telemetry)`
returns the full 6-value series plus the per-metric intermediate values for
transparency.

**New data file**: `backend/data/telemetry.json` (see below). Tuned so that
Borealia's (`away`) fatigue index at window index 4 (60-75', containing
minute 71) is ≈+41 (a clear "sharp decline" consistent with `fatigue_71`'s
narrative), while Atlántica's (`home`) is ≈-2 (flat/slightly improving,
consistent with their 2nd-half goals and tactical reshape).

### 6. Momentum curve

```
momentum(t) = sum over events e where e.minute <= t of:
    weight(e.type) * direction(e) * decay ^ ((t - e.minute) / 5)

direction(e) = +1 if e.team == "home" else -1
               (INVERTED for e.type == "pressure": a team's press
                collapsing shifts momentum to the OTHER team)

decay = 0.85, t in [0, 5, 10, ..., 90]
```

`weight(e.type)` comes from `telemetry.json -> event_weights_for_momentum`.
Output: `[{"minute": int, "value": float}, ...]` — same shape as the existing
static `momentum` array in `sample_match.json` (which becomes a fallback/
reference value, no longer served by the API).

This is a genuinely different computation from the hand-authored static
array, so exact values won't match — tests assert shape/sign properties
(e.g., momentum rises sharply after `goal_home_1`/`goal_home_2`, dips after
the away goal at minute 19) rather than exact equality with the static array.

## New data file: `backend/data/telemetry.json`

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

## API changes

### `GET /api/analytics` (new)

Returns all six models, each as `{"formula": ..., "inputs": ..., "result":
...}`:

```json
{
  "offside_probability": {"formula": "...", "inputs": {"margin_cm": 11, "camera_frame_uncertainty_cm": 6, "sigma_line_cm": 2.5}, "result": {"z": 2.78, "probability": 0.997}},
  "offside_sensitivity": {"formula": "...", "inputs": {"margin_cm": 11, "camera_frame_uncertainty_cm": 6, "sigma_line_cm_range": [1.5, 4.0]}, "result": [{"sigma_line_cm": 1.5, "probability": 0.999}, ...]},
  "counterfactual_timing": {"formula": "...", "inputs": {"margin_cm": 11, "attacker_speed_ms": 7}, "result": {"delay_needed_ms": 15.7}},
  "handball_reaction": {"formula": "...", "inputs": {"deflection_distance_m": 1.06, "ball_speed_ms": 20, "reaction_benchmark_ms": 250}, "result": {"time_available_ms": 53.0, "deficit_ratio": 4.72}},
  "fatigue_index": {"formula": "...", "inputs": {"windows": [...]}, "result": {"home": [...6 values...], "away": [...6 values...]}},
  "momentum_curve": {"formula": "...", "inputs": {"decay": 0.85, "event_weights": {...}}, "result": [{"minute": 0, "value": ...}, ...]}
}
```

`offside_probability`, `offside_sensitivity`, and `counterfactual_timing` use
`offside_27`'s dossier fields as inputs; `handball_reaction` uses
`handball_38`'s.

### `GET /api/match`

The `momentum` field is now `analytics.momentum_curve(...)` output instead of
the static `MATCH_DATA["momentum"]` array. Same shape
(`[{"minute": int, "value": float}]`), so no frontend contract change.

### `GET /api/moment/{id}`

Gains an `"analytics"` key:

| Moment | `analytics` value |
|---|---|
| `offside_27` | `{"offside_probability": {...}, "offside_sensitivity": {...}, "counterfactual_timing": {...}}` |
| `handball_38` | `{"handball_reaction": {...}}` |
| `fatigue_71` | `{"fatigue_index": {"home": [...], "away": [...]}}` |
| `halftime_shift`, `sub_58`, `goal_home_1`, `goal_home_2` | `null` |

## Testing strategy

- `tests/test_analytics.py` — unit tests for each of the 6 functions against
  the documented demo values:
  - `offside_probability(11, 6)` → `z ≈ 2.78`, `probability ≈ 0.997`
  - `offside_sensitivity(11, 6)` → 6 points, all probabilities in
    `(0.98, 1.0)`, monotonically decreasing as `sigma_line_cm` increases
  - `counterfactual_timing(11, 7)` → `delay_needed_ms ≈ 15.7`
  - `handball_reaction(1.06, 20)` → `time_available_ms == 53.0`,
    `deficit_ratio ≈ 4.7`
  - `fatigue_index(telemetry["teams"]["away"])` → window-4 value `≈ 41`,
    positive and largest of the 6 windows
  - `fatigue_index(telemetry["teams"]["home"])` → window-4 value `≈ -2`
  - `momentum_curve(...)` → 19 points (minutes 0-90 step 5), value after
    minute 65 > value after minute 15 (home dominance after `goal_home_1`)
- `tests/test_api.py` additions:
  - `GET /api/analytics` returns 200 with all 6 top-level keys, each with
    `formula`/`inputs`/`result`
  - `GET /api/match` momentum is a list of 19 `{"minute", "value"}` dicts
    (shape check, not exact-value check)
  - `GET /api/moment/offside_27|handball_38|fatigue_71` each have a non-null
    `"analytics"` key with the expected sub-keys
  - `GET /api/moment/halftime_shift` (and the other 3 non-analytics moments)
    have `"analytics": null`
- Full existing suite (52 tests) continues to pass unmodified.

## Out of scope / deferred

- Modifying `POST /api/ask`, `explainer.py`, `verifier.py`, or their tests.
- `historical_incidents.json` and the Decision Consistency Analyzer
  (`consistency.py`) — later phase.
- Real frontend rendering of these analytics (Decision Lab, momentum chart,
  sensitivity sliders) — later phase. This phase is API-only.
- Docling ingestion, real Granite providers, evals, Telegram bot — later
  phases, unchanged from Phase 1's "Build status" note in `CLAUDE.md`.
