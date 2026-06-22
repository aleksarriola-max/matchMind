# Global Broadcast Graphics Restyle — Design

**Goal:** Phase A of a 3-phase visual overhaul (restyle → momentum chart →
Decision Lab depth). Apply a consistent "Broadcast Graphics" visual
language across all 5 existing tabs (Overview, Moments/Decision Lab, Ask
MatchMind, Debate, History) — gradient score bars, glowing accents, dark
cards with colored left-border accents, emoji event icons, and a
horizontal glow bar for every confidence display. CSS/markup/small-JS
only: no new data, no new endpoints, frontend stays a single file with no
build step.

Validated interactively via the visual-companion browser tool before
writing this spec — direction and the two open detail choices (icon
style, confidence display style) were picked from live mockups, not
described abstractly.

**Architecture:** All changes live in `frontend/index.html`'s `<style>`
block and the HTML-building JS functions (`renderHeader`, `renderOverview`,
`buildMomentsSidebar`, `renderTextMoment`, `renderDecisionLab`'s lower-third
(confidence line only), the Ask MatchMind submit handler, the outrage
submit handler, and `selectHistoryTopic`). No new functions are needed —
existing render functions get their template strings and CSS classes
updated in place.

---

## 1. New shared building blocks

**CSS additions** (`:root` and new classes):
```css
--glow: 0 0 10px;  /* used as box-shadow blur amount with accent color */
.event-row { display:flex; align-items:center; gap:10px; background:var(--panel);
  border-radius:6px; padding:10px; margin-bottom:8px; border-left:3px solid var(--accent); }
.event-row .icon { font-size:18px; }
.glow-bar { background:#1c1c24; border-radius:6px; height:10px; overflow:hidden; }
.glow-bar .fill { height:100%; border-radius:6px; transition: width 0.6s ease-out;
  box-shadow: 0 0 10px currentColor; }
.glow-bar-label { display:flex; justify-content:space-between; color:var(--muted);
  font-size:11px; margin-bottom:6px; }
.score-bar { display:flex; align-items:center; justify-content:space-between;
  border-radius:6px; padding:10px 14px; box-shadow: 0 0 20px rgba(0,224,255,0.15); }
.card-hover { transition: transform 0.15s ease-out, box-shadow 0.15s ease-out; }
.card-hover:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.4); }
.tab-panel.active { animation: fade-in 0.25s ease-out; }
@keyframes fade-in { from { opacity:0; transform: translateY(4px); } to { opacity:1; transform: translateY(0); } }
```

**`EVENT_ICONS` JS map** (reused by Overview timeline and Moments sidebar):
```js
const EVENT_ICONS = { goal: '⚽', var_review: '🚩', tactical: '🔄', substitution: '🔁', pressure: '😓' };
```

**A `renderGlowBar(label, pct, colorVar)` helper** replacing every place a
bare percentage is currently shown:
```js
function renderGlowBar(label, pct, color) {
  return '<div class="glow-bar-label"><span>' + label + '</span><span style="color:' + color + ';font-weight:700;">' +
    (pct * 100).toFixed(1) + '%</span></div>' +
    '<div class="glow-bar"><div class="fill" style="background:' + color + ';color:' + color + ';width:' + (pct * 100) + '%"></div></div>';
}
```
(Width starts at 0 and is set via a `requestAnimationFrame` follow-up, or
simply rely on the CSS `transition` firing on the attribute change after
insertion — exact animation trigger mechanism is an implementation detail,
not a design decision.)

## 2. Per-tab changes

**Overview** (`renderHeader`, `renderOverview`):
- Header score line becomes a `.score-bar` with a `linear-gradient(90deg, var(--home), color-mix/darker)` background.
- Team cards (`.team-card`) get `card-hover` + a colored left border using each team's color.
- Event list rows become `.event-row` divs (replacing the current `<ul><li>` markup) with `EVENT_ICONS[e.type]` prefixed.

**Moments/Decision Lab** (`buildMomentsSidebar`, `renderTextMoment`):
- Sidebar buttons get `EVENT_ICONS[type]` prefix — requires deriving each moment's event type by cross-referencing `matchData.events` (matched by `id`).
- `.confidence-line` text replaced with `renderGlowBar('Confidence', moment.confidence, 'var(--accent)')` in `renderTextMoment`. `renderDecisionLab`'s separate confidence display (the inset's "Confidence: X% (z=Y)") is left untouched — that's a precision-measurement readout, not a generic confidence badge, and is in Phase C's scope (Decision Lab depth) rather than this pass.
- Law badge gets `box-shadow: var(--glow) var(--accent)` on hover only (subtle, not always-on).

**Ask MatchMind** (submit handler):
- `.confidence-card`'s percentage line replaced with `renderGlowBar('Confidence', ex.confidence, 'var(--accent)')`.
- Verified/unverified badges get a matching glow: `.badge.verified { box-shadow: 0 0 8px #6fd98e88; }` / `.badge.unverified { box-shadow: 0 0 8px #f0a86888; }`.
- Sources/evidence `<ul><li>` rows become `.event-row`-style cards (reusing the same class, no icon needed — `.event-row` already supports an icon-less variant since the icon span is optional markup).

**Debate** (outrage submit handler):
- Steelman/counter `.debate-cols` divs get `card-hover`.
- Verdict callout gets an inline `renderGlowBar` for the cited confidence, placed above the verdict text rather than parsed out of it.

**History** (`initHistoryTab`, `selectHistoryTopic`):
- Topic buttons get an icon map: `{offside:'🚩', handball:'✋', 'goal-line':'📏', penalty:'⚖️'}` prefixed to the button label.
- `.incident-card` gets `card-hover`.
- The "today" `.confidence-card` becomes a `renderGlowBar`.

## 3. Testing

No backend changes, so no new pytest coverage. Verification is manual:
take a screenshot of each of the 5 tabs after the restyle and visually
confirm against this spec's description, plus confirm no console errors
and that the existing functional behavior (tab switching, form
submissions, moment selection, topic selection) all still work — i.e. this
is a pure visual diff, not a behavior change.

## Out of scope

- Phase B (momentum chart) and Phase C (Decision Lab stadium/crowd/crest
  depth) — separate specs.
- Any change to backend, API responses, or data files.
- Real image assets (crests, stadium photos) — emoji and CSS
  gradients/shadows only, consistent with the no-build-step, no-asset-
  pipeline constraint.
