# Real StatsBomb Incident — Design

**Goal:** Close the "no real match data" gap identified in competitive analysis by
reconstructing one genuine, verifiable offside incident from the real 2022 World
Cup Final (Argentina vs France, StatsBomb match 3869685) using StatsBomb's
free Open Data, rendered in the Decision Lab alongside (not replacing) the
existing fictional demo fixture.

**Research findings that shaped this design** (see conversation): the
competitor-analysis claim of "Mbappé offside at 17', 2.8cm margin" does not
exist in the real data and is not used. The real incident used is **Theo
Hernandez → Mbappé, minute 58, StatsBomb's own `pass.outcome = "Pass Offside"`
tag** — chosen over the dedicated "Offside" event (Messi, 29') because that
one is a scrappy broken-play sequence (pass → opponent clearance → block →
offside flag four seconds later) with no single unambiguous "moment the ball
was played," whereas the Mbappé event is a single clean pass with an
unambiguous timestamp.

**Known, disclosed limitations** (shown in the UI, not hidden):
1. The freeze-frame data tags the passer (Hernandez) but not the recipient.
   Mbappé's position is approximated as the French (non-actor teammate)
   freeze-frame point nearest the pass's recorded `end_location` (~6.4
   StatsBomb units away in this case).
2. Argentina's goalkeeper is not present in this particular freeze frame
   (outside the broadcast camera's tracked area for this moment), so the
   "second-last opponent" calculation is computed among the **visible**
   Argentina defenders only, not literally all 11.
3. The ±cm uncertainty band reuses the existing demo's methodology
   (camera-frame + limb-tracking error propagation), but StatsBomb does not
   publish real camera-uncertainty parameters — so the band is explicitly
   captioned as an illustration of the *method*, not an official measurement.

**License compliance:** StatsBomb's Open Data User Agreement permits this use
(research/analysis, non-commercial) but prohibits redistributing their data
to third parties and requires attribution with their brand identity. So:
- The app **fetches the specific match/event/360 data live from StatsBomb's
  public GitHub repo at request time** (cached in memory for the server's
  lifetime) rather than committing a copy of their data into this repo.
- A visible, clearly-styled "StatsBomb — Data Champions." text credit
  (their real tagline, their brand colors) links to their open-data repo.
  (Their actual logo file requires downloading from their Media Pack
  manually — not done here since I won't hotlink an unverified image URL;
  swap in the real logo asset later if desired.)

---

## 1. `backend/engines/real_incident.py`

```python
import httpx

STATSBOMB_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
MATCH_ID = 3869685
PASS_EVENT_ID = "be78b6e9-2f19-4620-9e4b-b518bd562537"

# StatsBomb's standard pitch is 120x80 units representing a 105m x 68m pitch.
UNITS_TO_METERS_X = 105 / 120
UNITS_TO_METERS_Y = 68 / 80

_cache = None

def get_real_incident() -> dict:
    global _cache
    if _cache is None:
        _cache = _fetch_and_compute()
    return _cache

def _fetch_and_compute() -> dict:
    events = httpx.get(f"{STATSBOMB_BASE}/events/{MATCH_ID}.json", timeout=20).json()
    frames = httpx.get(f"{STATSBOMB_BASE}/three-sixty/{MATCH_ID}.json", timeout=20).json()

    event = next(e for e in events if e["id"] == PASS_EVENT_ID)
    frame = next(f for f in frames if f["event_uuid"] == PASS_EVENT_ID)
    freeze_frame = frame["freeze_frame"]

    end_location = event["pass"]["end_location"]
    candidates = [p for p in freeze_frame if p["teammate"] and not p["actor"]]
    mbappe = min(candidates, key=lambda p: _dist(p["location"], end_location))
    mbappe_match_distance_m = _dist(mbappe["location"], end_location) * UNITS_TO_METERS_X

    opponents = [p for p in freeze_frame if not p["teammate"]]
    goalkeeper_visible = any(p.get("keeper") for p in opponents)
    opponents_sorted = sorted(opponents, key=lambda p: -p["location"][0])
    second_last_opponent = opponents_sorted[1] if len(opponents_sorted) > 1 else opponents_sorted[0]

    margin_m = (mbappe["location"][0] - second_last_opponent["location"][0]) * UNITS_TO_METERS_X
    margin_cm = round(margin_m * 100, 1)

    return {
        "match": {"home_team": "Argentina", "away_team": "France", "competition": "2022 FIFA World Cup Final", "date": "2022-12-18"},
        "minute": event["minute"],
        "passer": event["player"]["name"],
        "recipient": event["pass"]["recipient"]["name"],
        "margin_cm": margin_cm,
        "mbappe_position": mbappe["location"],
        "second_last_opponent_position": second_last_opponent["location"],
        "freeze_frame": freeze_frame,
        "approximation_notes": [
            f"Recipient position estimated by nearest-tracked-point matching to the pass's recorded end location ({round(mbappe_match_distance_m, 1)}m match distance).",
            "Goalkeeper not visible in this camera-tracked frame — margin computed among visible defenders only." if not goalkeeper_visible else None,
        ],
        "source": "StatsBomb Open Data",
        "source_url": "https://github.com/statsbomb/open-data",
    }

def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
```

`approximation_notes` filters out `None` before returning (goalkeeper note
only appears when actually relevant). No persistence — `_cache` resets on
server restart, re-fetching live from StatsBomb each time, consistent with
not redistributing their data ourselves.

## 2. `backend/main.py`

```python
@app.get("/api/real-incident")
def real_incident():
    try:
        return real_incident_engine.get_real_incident()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch StatsBomb data: {exc}")
```

A 502 (not a crash) if StatsBomb's repo is briefly unreachable — this feature
depends on a live external fetch, unlike the rest of the app.

## 3. Frontend — Decision Lab addition

A new collapsed-by-default section appended to `renderDecisionLab()`'s output
for `offside_27`: a button "🌍 Show a real incident: 2022 World Cup Final."
Clicking it lazy-fetches `/api/real-incident` (not automatic, so the primary
demo never depends on network access to GitHub) and renders:
- A small pitch SVG (reusing `playerCircle()`, StatsBomb's 120×80 coordinates
  scaled to the existing 100×68 viewBox) showing the real freeze-frame
  positions, Mbappé and the second-last defender highlighted.
- The real computed margin in cm.
- The same uncertainty-band visualization, captioned: *"Illustrative — applies
  our uncertainty model to real position data. StatsBomb does not publish
  camera/tracking error margins, so this is not an official measurement."*
- The `approximation_notes` list, displayed plainly, not buried.
- The StatsBomb text credit, linked to their open-data repo.

## 4. Testing

`tests/test_real_incident.py` mocks `httpx.get` (same pattern as
`test_adapter.py`) with fixed fake event/frame JSON, so no real network call
happens in the fast test suite. Tests cover: the nearest-point matching logic,
the margin computation, the goalkeeper-visibility note appearing only when
the goalkeeper is absent from the mocked frame, and the in-memory cache only
fetching once across repeated calls.

## Out of scope

- Any other real incident (Messi 29', or the other Pass Offside events) —
  one incident is the scope of this pass.
- Replacing the fictional offside_27 demo — this is additive.
- Bundling StatsBomb's actual logo image file — text credit only, per the
  no-guessed-URLs constraint; swap in the real asset later if desired.
- Persisting fetched StatsBomb data to disk or committing it to the repo.
