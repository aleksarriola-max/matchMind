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


def test_offside_sensitivity_for_offside_27():
    result = analytics.offside_sensitivity(11, 6)
    points = result["result"]
    assert len(points) == 6
    sigma_values = [p["sigma_line_cm"] for p in points]
    assert sigma_values == [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    probabilities = [p["probability"] for p in points]
    for p in probabilities:
        assert 0.98 < p < 1.0
    assert probabilities == sorted(probabilities, reverse=True)


def test_counterfactual_timing_for_offside_27():
    result = analytics.counterfactual_timing(11, 7)
    assert result["result"]["delay_needed_ms"] == pytest.approx(15.7, abs=0.05)
    assert result["inputs"] == {"margin_cm": 11, "attacker_speed_ms": 7}
