# Team Fatigue & Pressure Zones — Design

**Goal:** A new "Fatigue & Pressure" tab showing one zone blob per team on
a pitch SVG, scrubbed across the match's 6 time windows — blob size driven
by real defensive-line compactness, blob color driven by the existing
real `fatigue_index`. Explicitly team-level, not per-player (matchMind has
no real per-player tracking data).

**Why team-level, not per-player:** The original pitch wanted "per-player
fatigue/pressure zones." `telemetry.json` only has team-level aggregates
(`sprints`, `line_gap_def_mid_m`, `long_pass_share`, `ppda`, 6 windows per
team) — there is no per-player data anywhere in the fixture. Inventing 22
players' worth of fatigue numbers would be a much larger fabrication than
anything built this session. The UI says so explicitly.

**Why size (not position) encodes line gap:** `line_gap_def_mid_m` measures
the *gap between a team's defensive line and midfield* — compactness, not
how far up the pitch the line sits. Using it to position a zone vertically
would imply a spatial claim the metric doesn't support. Using it to size
the zone (bigger gap → bigger, more spread-out blob, signaling a more
stretched/disorganized shape) is honest to what's actually measured.

## 1. `backend/engines/analytics.py` — `fatigue_pressure_zones`

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

Reuses `fatigue_index` exactly as it already exists (no duplicated fatigue
math). The `spread` min-max scaling follows the same pattern already used
in `tactical_dna` (observed range across both teams, zero-variance
fallback to `50.0`).

## 2. `app/components.py` — `render_fatigue_zone_pitch_html`

```python
def render_fatigue_zone_pitch_html(
    home_name: str, away_name: str, home_color: str, away_color: str,
    home_fatigue: float, home_spread: float, away_fatigue: float, away_spread: float,
) -> str:
```

A simplified pitch SVG (reusing the existing pitch-markings pattern from
the Decision Lab) with two filled ellipses, fixed at `x=30` (home, their
defensive/middle area) and `x=70` (away, mirrored). Ellipse radius scales
with `spread` (e.g., `8 + spread/100 * 10`, so roughly 8-18 units). Fill
color blends from each team's real color toward red as `fatigue_index`
rises (reusing `lighten_for_fill`-style blending already in this file,
adapted to blend toward `#cc3333` instead of white).

## 3. `app/fatigue_pressure.py` — new tab

```python
def render_fatigue_pressure(match_data: dict) -> None:
```

A window selector (`st.select_slider` over the 6 window labels from
`zones["windows"]`), then the pitch SVG for the selected window's index,
then the explicit team-level-not-per-player callout, then a small table of
the real underlying numbers (fatigue index and line gap) for both teams at
the selected window — same "real numbers behind the visual" pattern as
Tactical DNA's legend.

Wired as a 9th tab, "Fatigue & Pressure," after "What If."

## 4. Testing

`tests/test_analytics.py` new cases for `fatigue_pressure_zones`:
- Real fixture's actual telemetry produces `spread`/`fatigue_index` values
  in sane ranges (0-100 for spread; fatigue_index already tested elsewhere)
  for both teams, 6 windows each.
- Zero-variance synthetic case (identical line_gap for both teams across
  all windows) → `spread` is `50.0` for both teams, no `ZeroDivisionError`.
- Real data: away's `line_gap_def_mid_m` actually grows from 8.0 to 11.6
  across the match (already known from `telemetry.json`) — confirms
  away's `spread` score rises from window 0 to window 5, not flat or
  reversed.

`tests/test_components.py` new cases for `render_fatigue_zone_pitch_html`:
structural checks (SVG present, two ellipses, team names/colors present).

## Out of scope

- Any per-player data, real or fabricated.
- Animating the zones automatically across windows (Live Replay already
  owns the "auto-playing match timeline" interaction; this tab is a
  manual scrubber, not a second auto-play feature).
- Using `ppda`/`long_pass_share` for this visualization — `fatigue_index`
  already aggregates those into one number; introducing them again here
  would just be restating the same underlying telemetry a third way.
