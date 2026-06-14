import json
import math
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_match.json"
TELEMETRY_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"

with open(DATA_PATH, encoding="utf-8") as _f:
    MATCH_DATA = json.load(_f)

with open(TELEMETRY_PATH, encoding="utf-8") as _f:
    TELEMETRY_DATA = json.load(_f)


def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def offside_probability(margin_cm: float, camera_frame_uncertainty_cm: float, sigma_line_cm: float = 2.5) -> dict:
    sigma_frame = camera_frame_uncertainty_cm / 1.96
    sigma_total = math.sqrt(sigma_frame ** 2 + sigma_line_cm ** 2)
    z = margin_cm / sigma_total
    probability = _phi(z)
    return {
        "formula": "P(offside) = Phi(margin_cm / sqrt((camera_frame_uncertainty_cm / 1.96)^2 + sigma_line_cm^2))",
        "inputs": {
            "margin_cm": margin_cm,
            "camera_frame_uncertainty_cm": camera_frame_uncertainty_cm,
            "sigma_line_cm": sigma_line_cm,
        },
        "result": {"z": round(z, 2), "probability": round(probability, 3)},
    }
