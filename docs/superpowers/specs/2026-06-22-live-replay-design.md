# Live Replay — Design

**Goal:** Phase 1 of a 4-phase initiative (Live Replay → Voice narration →
Telegram bot → Docling ingestion). Build the "Live second-screen mode"
README.md already describes but doesn't exist: replay the match as a
simulated live feed, with moments explained as they "happen." Pure
frontend, reusing existing data (`matchData.events`, `matchData.moments`,
`matchData.momentum`) — no backend or data changes.

Layout validated via the visual-companion browser tool before writing
this spec.

**Architecture:** A 6th tab ("Live Replay"). A `setInterval`-driven clock
advances a `replayMinute` state variable from 0 to 90; every tick
re-renders the score, momentum chart (clipped to `replayMinute`), and
events ticker, and checks whether a new event with a moment `id` was just
crossed (triggering the breaking banner). All existing render helpers
(`EVENT_ICONS`, `.event-row`, `renderGlowBar`, `momentCache`/`selectMoment`)
are reused as-is.

---

## 1. New markup

```html
<section id="tab-live-replay" class="tab-panel">
  <div class="replay-header">
    <div class="replay-minute" id="replay-minute">0'</div>
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
  <div class="momentum-chart-wrap" id="replay-momentum-chart"></div>
  <div id="replay-ticker"></div>
</section>
```
Nav gets a 6th button: `<button data-tab="live-replay">Live Replay</button>`.

## 2. State and clock

```js
let replayMinute = 0;
let replayPlaying = false;
let replaySpeed = 1;
let replayIntervalId = null;
let replayLastTriggeredEventId = null;

function replayTick() {
  replayMinute += 1;
  if (replayMinute >= 90) {
    replayMinute = 90;
    stopReplay();
    renderReplayState();
    setReplayButtonToReplayAgain();
    return;
  }
  renderReplayState();
}
```
`setInterval(replayTick, 1000 / replaySpeed)` started on Play, cleared on
Pause. Changing speed mid-playback clears and restarts the interval at
the new rate without resetting `replayMinute`.

## 3. `renderReplayState()`

Called on every tick and on manual seek:

- **Minute/score**: `replay-minute` shows `replayMinute + "'"` (or `"Full Time"`
  at 90). Score computed by counting `type === 'goal'` events with
  `minute <= replayMinute`, split by `team`.
- **Momentum chart**: `renderMomentumChart(replayMinute)` — `renderMomentumChart`
  (from Phase B) gets a new optional parameter. When provided, the curve is
  filtered to `p.minute <= replayMinute` before building the polyline (so
  the line only shows what's "happened" so far), and a pulsing white
  "now" marker is drawn at the last visible point. When called with no
  argument (the existing Overview tab call site), behavior is unchanged —
  full curve, no playhead. This is the only change to existing Phase B code.
- **Events ticker**: events with `minute <= replayMinute`, reverse-chronological
  (newest first), reusing `.event-row` markup exactly as the Overview tab does.
- **Breaking banner**: find the highest-minute event with `minute <=
  replayMinute && event.id` that hasn't already triggered
  (`event.id !== replayLastTriggeredEventId`). If found, render the banner
  (title from the moment's `decision`, reusing `.lower-third`-style
  gradient + a "View full explanation →" button) and set
  `replayLastTriggeredEventId = event.id`; auto-clear the banner via
  `setTimeout` after 5 seconds. Manual seeking (the range input) updates
  `replayLastTriggeredEventId` to match whatever the seeked-to position
  implies *without* showing a banner — seeking is jumping, not living
  through it minute-by-minute.

## 4. Breaking banner → Moments tab

The "View full explanation →" button's `onclick` pauses replay, switches
to the Moments tab (reusing the existing tab-switch logic), and calls
`selectMoment(event.id)` — identical to clicking that moment in the
Moments sidebar today, including the `momentCache` lazy-fetch.

## 5. End of match

At `replayMinute === 90`: timer stops, play button becomes "↻ Replay
Again" (resets `replayMinute = 0`, clears the ticker/banner, re-renders).

## 6. Testing

No backend changes, so no new pytest coverage. Manual verification:
play through at 4x speed and confirm the score updates correctly at each
goal, the breaking banner appears for all 7 moments (not just
`offside_27`) and links correctly to each one's Moments detail, the
momentum chart's playhead and clipped curve advance correctly, pause/seek
work, and the match reaches "Full Time" with a working "Replay Again."
Also confirm the unmodified Overview-tab momentum chart call site still
renders the full curve with no playhead (regression check on Phase B).

## Out of scope

- Phase 2 (voice narration), Phase 3 (Telegram bot), Phase 4 (Docling) —
  separate specs. (Phase 2 will likely hook into this tab's banner/ticker
  to narrate moments as they're reached, but that's Phase 2's design, not
  this one's.)
- Backend or data changes — this is purely a new way of walking through
  data the frontend already has.
- Real-time wall-clock sync (e.g. matching an actual broadcast) — this is
  a self-paced simulated replay, not synced to anything external.
