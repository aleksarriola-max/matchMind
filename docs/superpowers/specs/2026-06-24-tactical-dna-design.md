# Tactical DNA Fingerprint — Design

**Goal:** A 4-axis radar chart comparing both teams' playing style, computed
entirely from real `telemetry.json` data already used by `fatigue_index` —
no new data source, no invented metrics.

## 1. `backend/engines/analytics.py` — `tactical_dna`

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

Axis semantics: `pressing_intensity` inverts PPDA (lower PPDA = more
passes-per-defensive-action = more pressing = higher score). `directness`
uses long-pass share directly (higher share = more direct buildup).
`defensive_compactness` inverts the defensive-line-to-midfield gap (smaller
gap = more compact = higher score). `transition_speed` uses sprint counts
directly, labeled as a proxy (there's no literal transition-speed metric in
the telemetry) — both in code comments and in the UI's axis label/tooltip.

Verified against the real fixture's actual `telemetry.json` values: home's
PPDA stays in the 8.5–9.5 range (i.e., consistently presses harder) while
away's PPDA rises to 13.2 by the final window (their press fades) — this
produces a real, meaningfully different fingerprint shape for the two
teams, not two near-identical near-50 blobs.

## 2. `app/components.py` — `render_tactical_dna_radar_html`

```python
def render_tactical_dna_radar_html(
    home_name: str, away_name: str, home_scores: dict, away_scores: dict,
    home_color: str, away_color: str,
) -> str:
```

4 axes at 90° apart starting from the top (pressing_intensity at 12 o'clock,
directness at 3 o'clock, defensive_compactness at 6 o'clock, transition_speed
at 9 o'clock), standard polar-to-cartesian: for axis `i` of 4,
`angle = -90 + i * 90` degrees, `x = cx + r * (score/100) * cos(angle)`,
`y = cy + r * (score/100) * sin(angle)`. Two semi-transparent filled
polygons (one per team's color), axis labels at the outer radius, plus
four background concentric gridline circles (25/50/75/100%) for scale
reference.

## 3. `app/tactical_dna.py` — new tab

```python
def render_tactical_dna(match_data: dict) -> None:
```

Renders the radar chart via `components.render_tactical_dna_radar_html`,
then a small two-column table below it showing each axis's real underlying
average for both teams (e.g. "PPDA: 9.2 vs 11.8") — pulled from
`tactical_dna(...)["raw_inputs"]` — so every position on the chart traces
back to a displayed real number, not just an abstract shape.

Wired into `app/main.py` as a 7th tab, "Tactical DNA," after "Live Replay."

## 4. Testing

`tests/test_analytics.py` new cases for `tactical_dna`:
- Synthetic telemetry with known min/max produces the expected scaled
  scores (hand-computed) for both inverted and non-inverted axes.
- Zero-variance synthetic input (identical home/away values for one field)
  produces `50.0` for that axis on both teams, no `ZeroDivisionError`.
- The real fixture's actual telemetry produces scores in `[0, 100]` for
  all 4 axes, both teams, with no `NaN`/error — and home's
  `pressing_intensity` score is higher than away's (matching the real
  PPDA data: home stays low/consistent, away rises sharply).

## Out of scope

- Any per-match-window breakdown of the radar (e.g. animating it across
  the match) — this is one fingerprint per team for the whole match,
  not a live-updating chart like the win-confidence meter.
- A league-average or historical-baseline comparison — no real benchmark
  data exists for that.
