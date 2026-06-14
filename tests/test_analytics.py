import pytest

from backend.engines import analytics


def test_offside_probability_for_offside_27():
    result = analytics.offside_probability(11, 6)
    assert result["result"]["z"] == pytest.approx(2.78, abs=0.01)
    assert result["result"]["probability"] == pytest.approx(0.997, abs=0.001)
    assert "formula" in result
    assert result["inputs"] == {
        "margin_cm": 11,
        "camera_frame_uncertainty_cm": 6,
        "sigma_line_cm": 2.5,
    }


def test_offside_probability_verdict_for_offside_27():
    result = analytics.offside_probability(11, 6)
    assert result["result"]["verdict"] == "near-certain offside"


def test_offside_probability_rejects_non_positive_sigma_line():
    with pytest.raises(ValueError):
        analytics.offside_probability(11, 6, sigma_line_cm=0)


def test_offside_probability_rejects_negative_frame_uncertainty():
    with pytest.raises(ValueError):
        analytics.offside_probability(11, -1)


def test_offside_sensitivity_for_offside_27():
    result = analytics.offside_sensitivity(11, 6)
    sweep = result["result"]["sweep"]
    assert len(sweep) == 6
    sigma_values = [p["sigma_line_cm"] for p in sweep]
    assert sigma_values == [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    probabilities = [p["probability"] for p in sweep]
    for p in probabilities:
        assert 0.98 < p < 1.0
    assert probabilities == sorted(probabilities, reverse=True)
    assert result["result"]["min_probability"] == pytest.approx(0.986, abs=0.001)
    assert result["result"]["max_probability"] == pytest.approx(0.999, abs=0.001)
    assert result["result"]["robust"] is True


def test_counterfactual_timing_for_offside_27():
    result = analytics.counterfactual_timing(11, 7)
    assert result["result"]["delay_needed_ms"] == pytest.approx(15.7, abs=0.05)
    assert result["inputs"] == {"margin_cm": 11, "attacker_speed_ms": 7}


def test_handball_reaction_for_handball_38():
    result = analytics.handball_reaction(1.06, 20)
    assert result["result"]["time_available_ms"] == 53.0
    assert result["result"]["deficit_ratio"] == pytest.approx(4.72, abs=0.01)
    assert result["inputs"] == {
        "deflection_distance_m": 1.06,
        "ball_speed_ms": 20,
        "reaction_benchmark_ms": 250,
    }


def test_handball_reaction_verdict_and_sensitivity_for_handball_38():
    result = analytics.handball_reaction(1.06, 20)
    assert result["result"]["verdict"] == "exceeds human reaction limits"
    sensitivity = result["result"]["benchmark_sensitivity"]
    assert [s["reaction_benchmark_ms"] for s in sensitivity] == [150, 200, 250, 300]
    assert [s["deficit_ratio"] for s in sensitivity] == pytest.approx([2.83, 3.77, 4.72, 5.66], abs=0.01)


def test_handball_reaction_rejects_non_positive_inputs():
    with pytest.raises(ValueError):
        analytics.handball_reaction(0, 20)
    with pytest.raises(ValueError):
        analytics.handball_reaction(1.06, 0)


def test_fatigue_index_away_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_index(telemetry)
    index = result["result"]["fatigue_index"]
    assert len(index) == 6
    assert index[2] == pytest.approx(12.1, abs=0.1)
    assert index[4] == pytest.approx(40.7, abs=0.1)
    assert index[5] == pytest.approx(54.6, abs=0.1)


def test_fatigue_index_home_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    result = analytics.fatigue_index(telemetry)
    index = result["result"]["fatigue_index"]
    assert len(index) == 6
    assert index[4] == pytest.approx(-2.0, abs=0.1)


def test_counterfactual_timing_frame_fields_for_offside_27():
    result = analytics.counterfactual_timing(11, 7)
    assert result["result"]["frames_at_50fps"] == pytest.approx(0.79, abs=0.01)
    assert result["result"]["frames_at_25fps"] == pytest.approx(0.39, abs=0.01)
    assert result["result"]["detectable_at_50fps"] is False


def test_counterfactual_timing_rejects_non_positive_speed():
    with pytest.raises(ValueError):
        analytics.counterfactual_timing(11, 0)


def test_fatigue_index_peak_and_trend_for_away_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_index(telemetry)
    assert result["result"]["peak_window"] == "75-90"
    assert result["result"]["trend"] == "increasing"


def test_fatigue_index_peak_and_trend_for_home_team():
    telemetry = analytics.TELEMETRY_DATA["teams"]["home"]
    result = analytics.fatigue_index(telemetry)
    assert result["result"]["peak_window"] == "15-30"
    assert result["result"]["trend"] == "stable"


def test_fatigue_index_rejects_zero_baseline():
    telemetry = {
        "sprints": [0, 0, 10, 10, 10, 10],
        "line_gap_def_mid_m": [10, 10, 10, 10, 10, 10],
        "long_pass_share": [0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
        "ppda": [10, 10, 10, 10, 10, 10],
    }
    with pytest.raises(ValueError):
        analytics.fatigue_index(telemetry)


def test_momentum_curve_shape_and_values():
    events = analytics.MATCH_DATA["events"]
    weights = analytics.TELEMETRY_DATA["event_weights_for_momentum"]
    curve = analytics.momentum_curve(events, weights)
    assert len(curve) == 19
    minutes = [p["minute"] for p in curve]
    assert minutes == list(range(0, 91, 5))
    by_minute = {p["minute"]: p["value"] for p in curve}
    assert by_minute[15] == 0
    assert by_minute[20] == pytest.approx(-29.0, abs=0.5)
    assert by_minute[65] == pytest.approx(24.6, abs=0.5)
    assert by_minute[90] == pytest.approx(41.0, abs=0.5)
    assert by_minute[65] < by_minute[90]


def test_fatigue_comparison_demo_telemetry():
    home = analytics.TELEMETRY_DATA["teams"]["home"]
    away = analytics.TELEMETRY_DATA["teams"]["away"]
    result = analytics.fatigue_comparison(home, away)
    assert result["result"]["difference"] == pytest.approx(
        [-0.2, 0.2, 12.6, 26.4, 42.7, 56.1], abs=0.1
    )
    assert result["result"]["more_fatigued_team"] == "away"
    assert result["inputs"] == {"home": home, "away": away}
