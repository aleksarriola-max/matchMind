# matchMind — Demo Video Script (~3 minutes)

**Live app:** https://mainpy-hpdupmoyakddvxo348e4yn.streamlit.app/
**Repo:** https://github.com/aleksarriola-max/matchMind

Use the live deployed URL for the recording, not localhost — it proves the
app actually runs for judges with no setup. Record in a clean browser
window, no other tabs/bookmarks bar visible, dark OS theme matches the
app's own dark UI.

---

## Before you hit record

- [ ] Open the live URL fresh (hard refresh) so the Live Replay tab starts at minute 0, not mid-playback from a previous session.
- [ ] Have your mic tested — a flat, confident pace reads better than a rushed one. This script is timed for **calm, normal speaking speed**, not sped-up reading.
- [ ] Close any popups/cookie banners before recording starts.

---

## 0:00–0:15 — Hook (Overview tab, already open)

**Say:**
> "This is matchMind — an AI explainability companion for soccer officiating, built on IBM Granite. It doesn't predict matches or replace referees. It explains *why* a decision happened, with every number traced back to something real and checkable — not an LLM guess."

**Do:** Sit on the Overview tab. Let the score bar, team cards, and Match Officiating card be visible while you say this — don't scroll yet.

---

## 0:15–0:50 — Ask MatchMind (the hallucination firewall)

**Say (while clicking the tab and typing):**
> "Let's ask it a real question."

Type: `Why was the goal disallowed for offside in the 27th minute?`

Submit, then once the answer renders:

> "Granite composes this answer grounded in retrieved evidence — but it doesn't get trusted blindly. A second Granite pass checks every claim against that evidence before it's shown. See this badge — Verified, 94% coverage. If Granite had said something the evidence didn't support, it would say Unverified instead, and list exactly what's unsupported."

**Do:** Point at (cursor hover, don't click) the Verified badge, the coverage %, and the Sources/Evidence/Lineage sections as you mention them.

---

## 0:50–1:25 — Decision Lab (computed analytics, not narration)

**Say (clicking Moments tab, offside_27 already selected by default):**
> "Every number you see is computed from a real formula, not narrated. This offside probability — 99.7% — comes from a Gaussian error-propagation model over the actual camera and tracking-line uncertainty. Toggle the uncertainty band—"

**Do:** Click the "Uncertainty band" checkbox off, then back on.

> "—and you see the real confidence interval shrink and grow with the math, live."

---

## 1:25–1:45 — Real StatsBomb data (not a fabricated incident)

**Say:**
> "And this isn't only a fictional demo fixture. This button fetches a real incident from the actual 2022 World Cup Final, live, from StatsBomb's Open Data."

**Do:** Click "🌍 Show a real incident: 2022 World Cup Final." Wait for it to load. Let the real player positions and margin render on screen.

> "Real player positions, a real measured margin, with every approximation in the math disclosed — not hidden."

---

## 1:45–2:00 — History (real historical comparison)

**Say (clicking History tab):**
> "The Decision Consistency Analyzer compares today's call against real historical World Cup incidents — not invented ones."

**Do:** Let one historical incident card (e.g. 1986 Hand of God) be visible for a beat. No need to read it aloud — the visual is enough.

---

## 2:00–2:20 — Live Replay (the win confidence meter)

**Say (clicking Live Replay tab):**
> "Live Replay plays the match minute by minute, with a live win-confidence meter — also a real computed formula, explicitly labeled as illustrative, not a prediction."

**Do:** Click Play. Let it run for ~5–8 seconds so the minute counter, score, and confidence meter visibly update. Click Pause before moving on.

---

## 2:20–2:50 — Quick tour: the newest features

**Say (clicking through Tactical DNA → What If → Fatigue & Pressure quickly, ~10 seconds each):**

> "Tactical DNA — a real per-team playing-style fingerprint from real match telemetry."

**Do:** Let the radar chart with two team polygons be visible.

> "The What-If engine toggles a real event off and recomputes the actual momentum model — not a generated story about what might have happened."

**Do:** Uncheck one event checkbox, let the second momentum chart visibly change shape.

> "And Fatigue & Pressure — team-level zones, explicitly not per-player, because that's the data matchMind actually has."

**Do:** Drag the window slider from 0-15 to 75-90, let the zone visibly grow and shift color.

---

## 2:50–3:00 — Close

**Say:**
> "matchMind: Granite-powered, every claim verified, every number computed from something real. Live now at this URL, fully open source on GitHub."

**Do:** Let the Overview tab (or wherever looks cleanest) sit on screen for the last 2–3 seconds before cutting.

---

## Timing cheat-sheet

| Segment | Time | Tab |
|---|---|---|
| Hook | 0:00–0:15 | Overview |
| Hallucination firewall | 0:15–0:50 | Ask MatchMind |
| Computed analytics | 0:50–1:25 | Moments |
| Real StatsBomb data | 1:25–1:45 | Moments (same) |
| Real historical comparison | 1:45–2:00 | History |
| Win confidence meter | 2:00–2:20 | Live Replay |
| Tactical DNA / What-If / Fatigue | 2:20–2:50 | 3 newest tabs |
| Close | 2:50–3:00 | Overview |

## If you have more time (5-minute version)

Extend the "computed analytics" and "newest features" segments — show the
sensitivity sweep, demo a second Ask MatchMind question with a different
persona (try `kid` for contrast), and let Live Replay run until a real
breaking-news banner fires instead of just a few seconds of ticking.
