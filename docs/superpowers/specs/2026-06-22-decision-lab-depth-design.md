# Decision Lab Visual Depth — Design

**Goal:** Phase C (final phase) of the 3-phase visual overhaul (restyle →
momentum chart → Decision Lab depth). Push the pitch SVG's surrounding
chrome further with stadium atmosphere, team crest badges, and a
broadcast-style VAR review banner — without touching the pitch SVG's own
coordinate math (player positions, offside line, viewBox), which stays
exactly as-is.

Validated interactively via the visual-companion browser tool: of 2
mockup directions (Stadium Bowl, TV Broadcast Frame), "Stadium Bowl" was
selected.

**Architecture:** All changes are scoped to `renderDecisionLab()` (the
function that renders `offside_27`, the only moment with `.pitch` data)
and new CSS. The pitch `<svg>` itself — its viewBox, player circles,
offside line, markings — is unchanged. New elements wrap around it.

---

## 1. `.pitch-wrap` background (CSS)

```css
.pitch-wrap {
  background: radial-gradient(ellipse at center, #15351f 0%, #0a0a0a 80%);
  position: relative;
  overflow: hidden;
}
.pitch-wrap::before, .pitch-wrap::after {
  content: ''; position: absolute; top: 0; width: 70px; height: 30px;
  background: radial-gradient(ellipse, rgba(255,255,255,0.18), transparent 70%);
  pointer-events: none;
}
.pitch-wrap::before { left: 0; }
.pitch-wrap::after { right: 0; }
```
Replaces the current flat `background: #0b0b0b;` rule. Purely decorative,
`pointer-events: none` so it never interferes with the toggle buttons or
any future interactivity.

## 2. Crowd-row strips (new markup, not part of the SVG)

```css
.crowd-row {
  height: 8px; background-image: radial-gradient(circle, rgba(200,200,200,0.4) 1px, transparent 1.5px);
  background-size: 6px 6px; opacity: 0.5;
}
```
Two `<div class="crowd-row">` elements added directly inside `.pitch-wrap`,
immediately before and after the `<svg class="pitch-svg">` element. These
are siblings of the SVG, not children — the SVG's own viewBox and
internal coordinates are untouched.

## 3. Crest + VAR review banner (new markup, new CSS)

```css
.lab-banner { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 10px 0; }
.crest { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: #fff; font-weight: 800; font-size: 13px; border: 2px solid #fff; }
.lab-banner .var-label { display: flex; align-items: center; gap: 6px; color: #ddd; font-size: 0.75em;
  letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: #ff3b3b;
  box-shadow: 0 0 6px #ff3b3b; animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
```

```js
const homeCrest = '<div class="crest" style="background:' + matchData.home.color + '">' + matchData.home.name[0] + '</div>';
const awayCrest = '<div class="crest" style="background:' + matchData.away.color + '">' + matchData.away.name[0] + '</div>';
html += '<div class="lab-banner">' + homeCrest +
  '<span class="var-label"><span class="pulse-dot"></span>VAR Review</span>' +
  awayCrest + '</div>';
```
Inserted between the existing `<p class="decision">...</p>` line and the
`<div class="pitch-wrap">` opening tag in `renderDecisionLab()`. Crest
initials/colors derived from `matchData.home.name`/`away.name`/`color` —
no new data needed.

## 4. Testing

No backend changes, so no new pytest coverage. Manual verification:
screenshot the Moments tab → `offside_27` after implementation, confirm
the stadium background/floodlight glow renders behind the pitch, crowd
rows appear above/below the green pitch, crests show the correct team
colors and initials (A / F for this fixture), the VAR Review dot pulses,
and — critically — that the player circles, offside line, toggles, inset,
lower-third, and debate columns all still render and function exactly as
before (toggle buttons still re-render correctly, no console errors).

## Out of scope

- Any change to the pitch SVG's coordinate math, player positions, or
  offside-line/inset rendering logic.
- Any change to other tabs (Overview, Ask MatchMind, Debate, History).
- Real crest images — initials-in-a-circle only, consistent with the
  no-build-step, no-asset-pipeline constraint already established.
- Backend or data changes.
