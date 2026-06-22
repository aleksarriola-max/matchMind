# Momentum Chart — Design

**Goal:** Phase B of the 3-phase visual overhaul (restyle → momentum chart →
Decision Lab depth). Render the momentum curve `/api/match` already
computes (`analytics.momentum_curve()`) but the frontend currently
discards entirely — a genuinely new visualization, not just restyling.

Validated interactively via the visual-companion browser tool: of 3
mockup styles (filled area, minimal gradient line, discrete bars) built
from this fixture's real momentum data, "minimal gradient line" was
selected.

**Architecture:** Pure frontend change. `matchData.momentum` (already
present in the `/api/match` response, untouched) is rendered by a new
`renderMomentumChart()` function and inserted into the Overview tab
between the team cards and the match-events timeline. No backend, no new
endpoints, no data file changes.

---

## 1. New markup

```html
<div class="momentum-chart-wrap" id="momentum-chart"></div>
```
Inserted into `#tab-overview` between `#team-cards` and the `<h2>Match
events</h2>` heading.

## 2. `renderMomentumChart()`

- Maps `matchData.momentum` (array of `{minute, value}`, minute 0–90 step
  5) to SVG coordinates: x = minute scaled to viewBox width, y = value
  scaled and inverted around a vertical-center zero line.
- Dashed zero-baseline across the full width.
- Path stroke uses a `<linearGradient>` from `matchData.home.color` to
  `matchData.away.color` (left to right, matching the score bar's
  gradient direction from Phase A), with a `drop-shadow` glow filter.
- Goal markers: for each event in `matchData.events` where `type ===
  'goal'`, plot a small white circle at that event's `(minute, value)`
  position (value looked up from the momentum array at/near that minute).
- Axis labels: just `0'` and `90'` text at the bottom corners — no Y-axis
  scale, consistent with the chosen minimal style.
- Draw-in animation: the path's `stroke-dasharray` is set to its own
  length and `stroke-dashoffset` animates from that length to 0 over
  ~0.8s on render (CSS transition triggered the same way `renderGlowBar`
  triggers its width transition — via a `requestAnimationFrame` pair
  after insertion).
- Hover tooltips: each data point gets an invisible larger-radius `<circle>`
  with a `title` attribute (native browser tooltip — no custom JS tooltip
  component needed) reading e.g. `"65' — Argentina ahead (+24.6)"` /
  `"27' — even (0.0)"` computed client-side from the sign of `value`.

## 3. Call site

`renderMomentumChart()` is called once from `renderOverview()` (the
function that already builds team cards and the event list), right
after building the team cards, so it participates in the same render
pass and data dependency (`matchData`) as the rest of the Overview tab.

## 4. Testing

No backend changes, so no new pytest coverage. Manual verification:
screenshot the Overview tab after implementation, confirm the chart
renders with correct shape (dips after the 19' away goal, recovers after
the 63'/84' home goals — same shape already proven correct by Phase 1's
`run_evals.py` momentum sanity checks), confirm goal markers land in the
right places, confirm hover tooltips show sensible text, and confirm no
console errors.

## Out of scope

- Phase C (Decision Lab depth) — separate spec.
- Any backend change — `momentum_summary()` stays unexposed; peak/
  dominant-team framing was explicitly deferred per the scope decision
  for this phase.
- Y-axis value scale/gridlines — deliberately omitted per the chosen
  minimal style.
