import httpx

STATSBOMB_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
MATCH_ID = 3869685
PASS_EVENT_ID = "be78b6e9-2f19-4620-9e4b-b518bd562537"

# StatsBomb's standard pitch is 120x80 units representing a 105m x 68m pitch.
UNITS_TO_METERS_X = 105 / 120
UNITS_TO_METERS_Y = 68 / 80

_cache: dict | None = None


def get_real_incident() -> dict:
    global _cache
    if _cache is None:
        _cache = _fetch_and_compute()
    return _cache


def _dist(a: list, b: list) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _fetch_events() -> list:
    response = httpx.get(f"{STATSBOMB_BASE}/events/{MATCH_ID}.json", timeout=20)
    response.raise_for_status()
    return response.json()


def _fetch_frames() -> list:
    response = httpx.get(f"{STATSBOMB_BASE}/three-sixty/{MATCH_ID}.json", timeout=20)
    response.raise_for_status()
    return response.json()


def _fetch_and_compute() -> dict:
    events = _fetch_events()
    frames = _fetch_frames()

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

    notes = [
        f"Recipient position estimated by nearest-tracked-point matching to the "
        f"pass's recorded end location ({round(mbappe_match_distance_m, 1)}m match distance)."
    ]
    if not goalkeeper_visible:
        notes.append(
            "Goalkeeper not visible in this camera-tracked frame — margin computed "
            "among visible defenders only."
        )

    return {
        "match": {
            "home_team": "Argentina",
            "away_team": "France",
            "competition": "2022 FIFA World Cup Final",
            "date": "2022-12-18",
        },
        "minute": event["minute"],
        "passer": event["player"]["name"],
        "recipient": event["pass"]["recipient"]["name"],
        "margin_cm": margin_cm,
        "mbappe_position": mbappe["location"],
        "second_last_opponent_position": second_last_opponent["location"],
        "freeze_frame": freeze_frame,
        "approximation_notes": notes,
        "source": "StatsBomb Open Data",
        "source_url": "https://github.com/statsbomb/open-data",
    }
