# Match Overview + Decision Lab — Design

**Goal:** Replace the placeholder `frontend/index.html` (currently just an "Ask MatchMind" form) with a tabbed UI — **Overview**, **Moments** (master-detail event browser with a broadcast-style Decision Lab pitch visualizer for the 27' offside review), and an improved **Ask MatchMind** tab.

**Context:** The backend is fully built (Phases 1-3): `/api/match`, `/api/moment/{id}`, `/api/analytics`, `/api/ask` all work and return rich data, including pitch geometry for the 27' offside moment and computed analytics (offside probability, handball reaction, fatigue index, momentum). The frontend has not kept pace — it's an 82-line single form. This phase is **pure frontend**: no backend or API changes. A later sub-project ("Analytics dashboards") will add momentum/fatigue/handball charts; this phase deliberately keeps non-pitch moments text-only.

**Constraints:**
- Single `frontend/index.html` file — vanilla JS, inline `<style>` and `<script>`, no build step, no new dependencies (per CLAUDE.md "Single-file UI — no build step"). No charting libraries; the pitch view is hand-built SVG.
- No backend changes. All data comes from the existing `/api/match`, `/api/moment/{id}`, `/api/ask` responses.
- "Do not display unverified numbers": the uncertainty band on the Decision Lab inset is computed client-side from values already present in `analytics.offside_probability.inputs` (`margin_cm`, `camera_frame_uncertainty_cm`, `sigma_line_cm`), using the exact same formula as `backend/engines/analytics.py`'s `offside_probability` (`sigma_total = sqrt((camera_frame_uncertainty_cm/1.96)^2 + sigma_line_cm^2)`).
- Dark theme throughout (not just the pitch), based on the approved broadcast palette: background `#0b0b0b`/`#121212`, grass green `#1a6e38`/`#1c7a3e`, cyan accent `#00e0ff` (offside line, highlights), yellow `#ffe14d` (assistant referee, sightlines), team colors pulled from `match.home.color` / `match.away.color` (`#0B5FA5` / `#C8102E` in the demo data).

---

## Navigation shell

A top nav bar with three tab buttons: **Overview**, **Moments**, **Ask MatchMind**. Exactly one tab's content `<div>` is visible at a time (toggle a `.hidden` class / `display:none`). On page load:

1. `fetch('/api/match')` once; cache the parsed JSON in a module-level `matchData` variable.
2. Render the Overview tab immediately from `matchData`.
3. Build the Moments sidebar from `matchData.events` (see below) but don't fetch any moment detail yet.
4. Ask MatchMind tab starts empty (just the form) until submitted.

If the initial `/api/match` fetch fails, show a full-page error message in place of the tab content ("Could not load match data — is the backend running?") and don't attempt to render tabs.

---

## Tab 1: Overview

Rendered entirely from the cached `/api/match` response (`{match_id, competition, home, away, score, events, momentum}`):

- **Header**: `competition` as a subtitle; `"{home.name} {score.home} – {score.away} {away.name}"` as the main heading, with each team name colored using `home.color` / `away.color`.
- **Team cards** (one per side): team name, a small color swatch (`background: home.color`), and `"{formation_start} → {formation_end}"`.
- **Event list**: an ordered list of all 8 entries in `events`, each rendered as `"{minute}' — [{type}] {desc}"`. The `type` is shown as a small badge (text label, no special styling beyond a background tint). This list is **read-only** — no click handlers here (clicking lives in the Moments tab).

`momentum` is fetched but not rendered in this phase (reserved for the Analytics dashboards sub-project).

---

## Tab 2: Moments (master-detail)

### Sidebar

Built from `matchData.events`, filtered to the 7 entries that have an `id` field (every event except the minute-19 goal, which has no corresponding entry in `/api/moment/{id}`):

```
27' Offside (VAR)        -> id "offside_27"
38' Handball (VAR)        -> id "handball_38"
46' Tactical shift        -> id "halftime_shift"
58' Substitution          -> id "sub_58"
63' Goal                  -> id "goal_home_1"
71' Pressing collapse     -> id "fatigue_71"
84' Goal                  -> id "goal_home_2"
```

(Label text = minute + a short human label derived from `type`/`desc` — e.g. `"{minute}' — {desc}"` truncated, or a `{type: label}` lookup table; exact wording is an implementation detail as long as each entry is distinguishable and shows its minute.)

Each sidebar entry is a clickable button. Clicking:
1. Highlights the selected entry (active state).
2. If `/api/moment/{id}` hasn't been fetched yet for this id, `fetch('/api/moment/{id}')` and cache the result in a `momentCache` object keyed by id.
3. Renders the detail panel from the cached response.

**Default on first visit to the Moments tab**: auto-select and fetch `offside_27` so the Decision Lab is visible immediately.

If a `/api/moment/{id}` fetch fails, render an inline error in the detail panel ("Could not load this moment.") without affecting the sidebar.

### Detail panel — `offside_27`: Decision Lab

The response shape for `offside_27` is:

```jsonc
{
  "title": "...", "law": "Law 11 — Offside Offence", "decision": "Goal disallowed for offside",
  "confidence": 0.997, "margin_cm": 11, "camera_frame_uncertainty_cm": 6, "attacker_speed_ms": 7,
  "summary": "...", "counterfactual": "...", "referee_view": "...",
  "debate": {"stands": "...", "overturn": "..."},
  "evidence": ["...", ...],
  "pitch": {
    "offside_line_x": 72.0,
    "ball": {"x": 60.0, "y": 34.0},
    "passer": {"x": 58.0, "y": 30.0, "label": "Atlántica #8"},
    "attacker": {"x": 72.11, "y": 36.0, "label": "Atlántica #9", "offside": true},
    "second_last_defender": {"x": 72.0, "y": 35.5, "label": "Borealia #4"},
    "keeper": {"x": 100.0, "y": 34.0, "label": "Borealia #1"},
    "others": [{"x": 65.0, "y": 20.0, "team": "home"}, {"x": 68.0, "y": 50.0, "team": "away"}, {"x": 55.0, "y": 40.0, "team": "away"}],
    "assistant_referee": {"x": 72.0, "y": 0.0, "label": "AR1"}
  },
  "analytics": {
    "offside_probability": {"inputs": {"margin_cm": 11, "camera_frame_uncertainty_cm": 6, "sigma_line_cm": 2.5}, "result": {"z": 2.78, "probability": 0.997, "verdict": "near-certain offside"}},
    "offside_sensitivity": {...},
    "counterfactual_timing": {"result": {"delay_needed_ms": 15.7, "frames_at_50fps": 0.79, "frames_at_25fps": 0.39, "detectable_at_50fps": false}}
  }
}
```

#### Full pitch SVG

`viewBox="-2 -2 104 72"`, rendered inside a dark container (`#0b0b0b`).

- **Grass**: a base `<rect x="-2" y="-2" width="104" height="72" fill="#1a6e38">`, plus 6 vertical stripe `<rect>`s at `x = -2, 18, 38, 58, 78, 98`, each `width="10"`, `fill="#ffffff"`, `opacity="0.18"`.
- **Pitch markings** (stroke `#eaf5ee`, `stroke-width="0.35"`, `fill="none"`, group `opacity="0.9"`):
  - Outline `<rect x="0" y="0" width="100" height="68">`
  - Center line `x1="50" y1="0" x2="50" y2="68"`
  - Center circle `cx="50" cy="34" r="8.7"` + center spot (filled circle `r="0.5"`)
  - Right penalty area `<rect x="84.3" y="13.8" width="15.7" height="40.3">`, right goal area `<rect x="94.8" y="24.8" width="5.2" height="18.3">`, penalty spot `cx="89.5" cy="34" r="0.5"` (filled), penalty arc `<path d="M 84.3 26.7 A 8.7 8.7 0 0 1 84.3 41.3">`
  - Goal frame `<rect x="100" y="30.3" width="1.6" height="7.3" fill="#eaf5ee" opacity="0.5">`
  - Left penalty area `<rect x="0" y="13.8" width="15.7" height="40.3">`, left goal area `<rect x="0" y="24.8" width="5.2" height="18.3">`
  - Four corner arcs (radius 1, one `<path>` per corner as in the approved mockup)
- **Offside line**: drawn at `x = pitch.offside_line_x` (72 for this moment) as two overlaid vertical lines spanning `y=-2` to `y=70`: one `stroke="#00e0ff" stroke-width="0.5"`, one `stroke="#00e0ff" stroke-width="1.6" opacity="0.25"` (glow effect).
- **Players** (drawn after markings so they're on top):
  - `pitch.ball` → white circle, `r="0.9"`, `stroke="#333" stroke-width="0.15"`
  - `pitch.passer` → circle `r="1.6"`, `fill=home.color`, `stroke="#fff" stroke-width="0.25"`, with the jersey number (text after `#` in `label`) centered inside in white, `font-size="1.8"`
  - `pitch.attacker` → same as passer but `stroke="#ff4d4d" stroke-width="0.4"` (red highlight ring marking the offside player) — fill is still `home.color`
  - `pitch.second_last_defender` → circle `r="1.6"`, `fill=away.color`, `stroke="#fff" stroke-width="0.25"`, jersey number from `label`
  - `pitch.keeper` → same styling as second_last_defender
  - `pitch.others[]` → for each, circle `r="1.5"`, `fill = team === 'home' ? home.color : away.color`, `stroke="#fff" stroke-width="0.2"`, `opacity="0.65"`, no number/text
  - `pitch.assistant_referee` → circle `r="1"`, `fill="#ffe14d"`, with its `label` ("AR1") as text above it in `#ffe14d`, `font-size="2"`

  *(home.color/away.color come from the cached `matchData.home.color` / `matchData.away.color`.)*

- **Referee sightline (toggle, default OFF)**: when enabled, draw two dashed lines from `pitch.assistant_referee` to `pitch.attacker` and from `pitch.assistant_referee` to `pitch.second_last_defender`, both `stroke="#ffe14d" stroke-width="0.25" stroke-dasharray="0.8,0.6"`, the attacker line at `opacity="0.85"` and the defender line at `opacity="0.5"`. Toggled via a button; toggling adds/removes these two `<line>` elements (or flips a CSS class that sets `display`).

#### Broadcast lower-third banner

A `<div>` below the SVG, gradient background `linear-gradient(90deg, #00e0ff, home.color)`, white text, flex layout with two ends:
- Left: `"OFFSIDE — " + pitch.attacker.label.toUpperCase()` (e.g. "OFFSIDE — ATLÁNTICA #9")
- Right: `"Margin: {margin_cm}.0 cm  |  Confidence: {(analytics.offside_probability.result.probability * 100).toFixed(1)}%"`

#### Zoomed measurement inset (toggle band, default ON)

A second SVG, `viewBox="0 0 220 60"`, dark green background `#0e2a1a`.

Let `margin = margin_cm` (11), and compute client-side:
```js
const sigmaLine = analytics.offside_probability.inputs.sigma_line_cm;       // 2.5
const sigmaFrame = analytics.offside_probability.inputs.camera_frame_uncertainty_cm / 1.96;
const sigmaTotal = Math.sqrt(sigmaFrame ** 2 + sigmaLine ** 2);              // ≈ 3.95
const ciHalfWidth = 1.96 * sigmaTotal;                                       // ≈ 7.75
```

- **Offside line**: vertical line at `x=110`, `stroke="#00e0ff" stroke-width="1"`, labeled "offside line" above it.
- **Uncertainty band** (toggle, default ON): `<rect x="{110 - ciHalfWidth}" y="6" width="{2 * ciHalfWidth}" height="48" fill="#00e0ff" opacity="0.18">`, with a label below the band: `"±{ciHalfWidth.toFixed(1)}cm (95% CI)"`.
- **Defender line**: horizontal line `y="40"` from `x="40"` to `x="110"`, `stroke=away.color stroke-width="1"`, circle marker `r="2.5"` at `x="40"` filled `away.color`, label = defender's jersey number (e.g. "#4").
- **Attacker line**: horizontal line `y="20"` from `x="40"` to `x="{110 + margin}"`, `stroke=home.color stroke-width="1"`, circle marker `r="2.5"` at `x="{110 + margin}"` filled `home.color` with `stroke="#ff4d4d" stroke-width="0.8"`, label = attacker's jersey number + margin (e.g. "#9 (+11cm)").
- **Margin bracket**: horizontal line `y="30"` from `x="110"` to `x="{110 + margin}"`, `stroke="#fff" stroke-width="0.6"`, label `"{margin}cm"` centered above it.

#### Text block below both SVGs

In order:
- Law citation (`law`) and decision (`decision`)
- `"Confidence: {(confidence*100).toFixed(1)}% (z = {analytics.offside_probability.result.z})"`
- Counterfactual callout: `counterfactual` text in a highlighted box, optionally noting `analytics.counterfactual_timing.result.frames_at_50fps` (e.g. "(0.79 frames at 50fps — not detectable on broadcast)")
- Debate: two side-by-side columns headed "Stands" / "Overturn" showing `debate.stands` / `debate.overturn`

### Detail panel — all other moments (text-only)

For `handball_38`, `fatigue_71`, `halftime_shift`, `sub_58`, `goal_home_1`, `goal_home_2`, render:

1. `title` as heading
2. `law` as a badge if non-null (omit entirely if `null`)
3. `decision`
4. `"Confidence: {(confidence*100).toFixed(0)}%"`
5. `summary` as a paragraph
6. `evidence` as a bullet list

Then, if `analytics` is not `null`, append a small "Computed analytics" definition list:

- **`handball_38`** — from `analytics.handball_reaction`:
  `"Ball reaches the point of contact in {result.time_available_ms}ms — {result.deficit_ratio}x faster than the {inputs.reaction_benchmark_ms}ms human reaction benchmark ({result.verdict})."`

- **`fatigue_71`** — from `analytics.fatigue_index.home` / `.away` and `analytics.fatigue_comparison` (these are already unwrapped `result` dicts server-side — no further `.result` nesting):
  A small table with one row per team: `Team | Trend | Peak window` (values: `home.name`/`away.name`, `analytics.fatigue_index.<side>.trend`, `analytics.fatigue_index.<side>.peak_window`), followed by: `"More fatigued by full-time: {analytics.fatigue_comparison.more_fatigued_team} (diff {analytics.fatigue_comparison.difference[5]} pts)"`.

- `halftime_shift`, `sub_58`, `goal_home_1`, `goal_home_2` have `analytics: null` — no extra block.

---

## Tab 3: Ask MatchMind

Keep the existing form (question input, persona select, language select, submit button) and the `POST /api/ask` call — only the **rendering of the response** changes. Response shape:

```jsonc
{
  "answer": "...", "persona": "...", "language": "English", "moment_id": "offside_27",
  "verification": {"verified": true, "coverage": 1.0, "checked_sentences": 2, "unsupported": [], "method": "lexical"},
  "explainability": {
    "confidence": 0.997, "confidence_basis": "...", "confidence_components": {...},
    "sources": [{"title": "...", "source": "...", "score": 0.3777}, ...],
    "evidence": ["...", ...],
    "counterfactual": "..." ,           // optional
    "debate": {"stands": "...", "overturn": "..."},  // optional
    "uncertainty": "...", "lineage": "..."
  },
  "llm": {...}
}
```

Render, in order, replacing the current `<pre>` dump:

1. **Answer** — as a heading/paragraph.
2. **Verification badge** — "Verified" (green) if `verification.verified` else "Unverified" (amber), with `"coverage: {(verification.coverage*100).toFixed(0)}%"`. If `verification.unsupported` is non-empty, list those sentences.
3. **Confidence card** — `"{(confidence*100).toFixed(1)}%"` plus `confidence_basis` as a caption.
4. **Sources** — bullet list: `"{title} ({source}, score {score.toFixed(2)})"`.
5. **Evidence** — bullet list of `evidence` strings.
6. **Counterfactual** — highlighted callout box, only if `explainability.counterfactual` is present.
7. **Debate** — two side-by-side columns "Stands" / "Overturn", only if `explainability.debate` is present.
8. **Lineage** — small monospace caption showing `explainability.lineage` (matches the "full lineage on every response" claim in the README).

Reuse the same card/badge/color-coding visual language as the Decision Lab (dark theme, cyan accents, team-agnostic here).

---

## Error handling

- `/api/match` fetch failure on page load → full-page error message, no tabs rendered.
- `/api/moment/{id}` fetch failure → inline error message in the Moments detail panel only.
- `/api/ask` fetch failure → inline error message in the Ask MatchMind result area, form remains usable for retry.

## Testing

No backend changes, so the existing 82 pytest tests are unaffected and are not expected to change. Verification is manual:

1. `uvicorn backend.main:app --reload`, open `http://localhost:8000`.
2. **Overview tab**: confirm score, team names/colors, formations, and all 8 events render.
3. **Moments tab**: confirm sidebar shows 7 entries, `offside_27` is auto-selected with the full Decision Lab (pitch, both toggles, lower-third, inset, debate). Click through the other 6 entries and confirm text-only rendering, including the computed-analytics blocks for `handball_38` and `fatigue_71`.
4. **Ask MatchMind tab**: submit the default offside question, confirm styled rendering of answer/verification/confidence/sources/evidence/counterfactual/debate/lineage. Try a question with no counterfactual/debate (e.g. a tactical moment) and confirm those sections are omitted cleanly.
5. Resize the browser window to confirm the layout doesn't break badly at narrower widths (no specific breakpoint requirements — just avoid obvious overflow/clipping).
