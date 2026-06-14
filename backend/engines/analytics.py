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


def offside_sensitivity(margin_cm: float, camera_frame_uncertainty_cm: float) -> dict:
    sigma_line_values = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    result = []
    for sigma_line_cm in sigma_line_values:
        probability = offside_probability(margin_cm, camera_frame_uncertainty_cm, sigma_line_cm)["result"]["probability"]
        result.append({"sigma_line_cm": sigma_line_cm, "probability": probability})
    return {
        "formula": "Sweep sigma_line_cm over [1.5, 4.0] step 0.5, recomputing P(offside) for each value",
        "inputs": {
            "margin_cm": margin_cm,
            "camera_frame_uncertainty_cm": camera_frame_uncertainty_cm,
            "sigma_line_cm_range": [1.5, 4.0],
        },
        "result": result,
    }


def counterfactual_timing(margin_cm: float, attacker_speed_ms: float) -> dict:
    delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000
    return {
        "formula": "delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000",
        "inputs": {"margin_cm": margin_cm, "attacker_speed_ms": attacker_speed_ms},
        "result": {"delay_needed_ms": round(delay_needed_ms, 1)},
    }


def handball_reaction(deflection_distance_m: float, ball_speed_ms: float, reaction_benchmark_ms: float = 250) -> dict:
    time_available_ms = deflection_distance_m / ball_speed_ms * 1000
    deficit_ratio = reaction_benchmark_ms / time_available_ms
    return {
        "formula": "time_available_ms = deflection_distance_m / ball_speed_ms * 1000; deficit_ratio = reaction_benchmark_ms / time_available_ms",
        "inputs": {
            "deflection_distance_m": deflection_distance_m,
            "ball_speed_ms": ball_speed_ms,
            "reaction_benchmark_ms": reaction_benchmark_ms,
        },
        "result": {
            "time_available_ms": round(time_available_ms, 1),
            "deficit_ratio": round(deficit_ratio, 2),
        },
    }
