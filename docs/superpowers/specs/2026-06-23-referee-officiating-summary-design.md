# Match Officiating Summary — Design

**Goal:** Add a small "Match Officiating Summary" card to the Overview tab
showing real, computed counts of this match's own VAR reviews, penalty
appeals, and cautions — not a fabricated cross-match "referee tendency"
profile (the originally pitched "Referee Intelligence Profile" idea implied
multi-match history matchMind doesn't have and would require inventing).

**Why this scope, not the original pitch:** The demo fixture is one
fictional match with an unnamed referee — there's no real or even
consistently-fictional history of past matches to compute "how often this
referee awards penalties" from. Fabricating that history would directly
violate this project's no-hallucination ethos. Instead: name the referee
(part of the same fictional fixture as everything else in
`sample_match.json`), and compute a small, honest summary purely from this
match's own real events. Framed explicitly as a single-match summary, not a
behavioral pattern.

## 1. `backend/data/sample_match.json`

Add a top-level `referee` field:

```json
"referee": {"name": "Hugo Martínez"},
```

Add an explicit `outcome` field to the two existing `var_review` events
(no other event types change):

```json
{"minute": 27, "type": "var_review", "team": "home", "id": "offside_27", "outcome": "overturned", "desc": "Argentina's goal is disallowed after a VAR review for offside."},
{"minute": 38, "type": "var_review", "team": "away", "id": "handball_38", "outcome": "upheld", "desc": "France's penalty appeal for handball is rejected."},
```

`outcome` is explicit data, not inferred by cross-referencing moment
dossiers — keeps `referee_profile` a simple, direct read of the events list.

## 2. `backend/engines/analytics.py` — `referee_profile`

```python
def referee_profile(events: list) -> dict:
    """
    Single-match officiating summary, computed purely from this match's own
    events -- not a cross-match behavioral tendency (matchMind has no real
    multi-match referee history to compute one from).
    """
    var_reviews = [e for e in events if e["type"] == "var_review"]
    overturned = sum(1 for e in var_reviews if e.get("outcome") == "overturned")
    upheld = sum(1 for e in var_reviews if e.get("outcome") == "upheld")
    return {
        "var_reviews_triggered": len(var_reviews),
        "overturned_count": overturned,
        "upheld_count": upheld,
        "overturn_rate": round(overturned / len(var_reviews), 2) if var_reviews else None,
        "penalty_appeals": sum(1 for e in events if "penalty" in e["desc"].lower()),
        "penalties_awarded": sum(1 for e in events if e["type"] == "penalty"),
        "cautions_issued": sum(1 for e in events if e["type"] == "card"),
    }
```

`penalties_awarded` and `cautions_issued` count events by `type` exactly —
`"penalty"` and `"card"` are not among the event types this fixture
currently uses (its schema is `goal|chance|var_review|card|tactical|
substitution|pressure`), so both are honestly `0` for this match: a direct
consequence of counting real data, not a hardcoded placeholder. If a future
fixture adds a `"penalty"` or `"card"` event, this function picks it up
with no changes needed.

`overturn_rate` is `None` (not 0 or a fabricated default) when there are no
VAR reviews to compute a rate from — an honest "not applicable," not a
misleading zero.

## 3. `app/overview.py`

A new card rendered between the team cards and the momentum chart:

```
Match Officiating
Hugo Martínez
2 VAR reviews this match — 1 overturned, 1 upheld
0 penalties awarded (1 appeal reviewed and rejected)
0 cautions issued
```

New pure function `app.components.render_referee_card_html(referee_name: str, profile: dict) -> str`, following the same pattern as the existing `render_incident_card_html` — reuses the `.team-card` CSS class for its border/panel/accent-stripe styling (no new CSS needed), unit-tested in `tests/test_components.py` like every other card builder in that file. `app/overview.py` calls it once, passing `match_data["referee"]["name"]` and `analytics.referee_profile(match_data["events"])`, rendered as its own full-width block below the two-column team-cards row (not inside that row's flex container) — `.team-card`'s `flex: 1` rule has no effect outside a `.team-cards` flex parent, so this card is full-width by construction, which reads better given its longer text content than the short team-formation strings above it.

Labeled "this match" explicitly in the card's body text, not just implied —
reinforces the single-match framing decided above.

## 4. Testing

`tests/test_analytics.py` new cases for `referee_profile`:
- The real fixture's 2 VAR reviews (1 overturned, 1 upheld) produce
  `overturn_rate == 0.5`.
- Zero VAR-review events produces `overturn_rate is None`, not `0`.
- `cautions_issued` counts only `type == "card"` events (0 for this fixture,
  since it has none).

## Out of scope

- Any cross-match or historical referee data, real or fictional.
- A dedicated new tab — this is a small Overview-tab addition.
- Comparing this referee's numbers to a league/tournament average (no real
  average exists to compare against).
