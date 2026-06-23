import httpx
import pytest

from backend.engines import real_incident


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


FAKE_EVENT = {
    "id": real_incident.PASS_EVENT_ID,
    "minute": 58,
    "player": {"name": "Theo Hernandez"},
    "pass": {
        "end_location": [94.0, 26.2],
        "recipient": {"name": "Kylian Mbappe"},
    },
}


def _fake_frame(include_keeper: bool):
    freeze_frame = [
        {"teammate": True, "actor": True, "keeper": False, "location": [55.5, 5.5]},
        {"teammate": True, "actor": False, "keeper": False, "location": [93.0, 25.0]},
        {"teammate": True, "actor": False, "keeper": False, "location": [50.0, 50.0]},
        {"teammate": False, "actor": False, "keeper": False, "location": [90.0, 20.0]},
        {"teammate": False, "actor": False, "keeper": False, "location": [85.0, 30.0]},
    ]
    if include_keeper:
        freeze_frame.append({"teammate": False, "actor": False, "keeper": True, "location": [99.0, 40.0]})
    return {"event_uuid": real_incident.PASS_EVENT_ID, "freeze_frame": freeze_frame}


@pytest.fixture(autouse=True)
def _reset_cache():
    real_incident._cache = None
    yield
    real_incident._cache = None


def test_computes_mbappe_position_via_nearest_match(monkeypatch):
    call_count = {"n": 0}

    def fake_get(url, timeout):
        call_count["n"] += 1
        if "events" in url:
            return _FakeResponse([FAKE_EVENT])
        return _FakeResponse([_fake_frame(include_keeper=True)])

    monkeypatch.setattr(httpx, "get", fake_get)

    result = real_incident.get_real_incident()

    assert result["mbappe_position"] == [93.0, 25.0]
    assert result["passer"] == "Theo Hernandez"
    assert result["recipient"] == "Kylian Mbappe"
    assert result["minute"] == 58


def test_margin_computed_against_second_last_opponent(monkeypatch):
    def fake_get(url, timeout):
        if "events" in url:
            return _FakeResponse([FAKE_EVENT])
        return _FakeResponse([_fake_frame(include_keeper=True)])

    monkeypatch.setattr(httpx, "get", fake_get)
    result = real_incident.get_real_incident()

    # second-last opponent (excluding the deepest, the keeper at x=99) is at x=90.
    # margin = (93.0 - 90.0) * (105/120) = 2.625m = 262.5cm
    assert result["margin_cm"] == pytest.approx(262.5)


def test_goalkeeper_note_appears_only_when_keeper_not_visible(monkeypatch):
    def fake_get_with_keeper(url, timeout):
        if "events" in url:
            return _FakeResponse([FAKE_EVENT])
        return _FakeResponse([_fake_frame(include_keeper=True)])

    monkeypatch.setattr(httpx, "get", fake_get_with_keeper)
    result = real_incident.get_real_incident()
    assert not any("Goalkeeper" in note for note in result["approximation_notes"])

    real_incident._cache = None

    def fake_get_without_keeper(url, timeout):
        if "events" in url:
            return _FakeResponse([FAKE_EVENT])
        return _FakeResponse([_fake_frame(include_keeper=False)])

    monkeypatch.setattr(httpx, "get", fake_get_without_keeper)
    result = real_incident.get_real_incident()
    assert any("Goalkeeper" in note for note in result["approximation_notes"])


def test_result_is_cached_across_calls(monkeypatch):
    call_count = {"n": 0}

    def fake_get(url, timeout):
        call_count["n"] += 1
        if "events" in url:
            return _FakeResponse([FAKE_EVENT])
        return _FakeResponse([_fake_frame(include_keeper=True)])

    monkeypatch.setattr(httpx, "get", fake_get)

    real_incident.get_real_incident()
    real_incident.get_real_incident()
    real_incident.get_real_incident()

    assert call_count["n"] == 2  # one events fetch + one frames fetch, total, ever
