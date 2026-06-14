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
