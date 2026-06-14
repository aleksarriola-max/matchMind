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


def _offside_verdict(probability: float) -> str:
    if probability >= 0.95:
        return "near-certain offside"
    if probability >= 0.6:
        return "likely offside"
    if probability >= 0.4:
        return "inconclusive"
    if probability > 0.05:
        return "likely not offside"
    return "near-certain not offside"


def offside_probability(margin_cm: float, camera_frame_uncertainty_cm: float, sigma_line_cm: float = 2.5) -> dict:
    if sigma_line_cm <= 0:
        raise ValueError(f"sigma_line_cm must be positive, got {sigma_line_cm}")
    if camera_frame_uncertainty_cm < 0:
        raise ValueError(f"camera_frame_uncertainty_cm must be non-negative, got {camera_frame_uncertainty_cm}")
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
        "result": {
            "z": round(z, 2),
            "probability": round(probability, 3),
            "verdict": _offside_verdict(probability),
        },
    }


def offside_sensitivity(margin_cm: float, camera_frame_uncertainty_cm: float) -> dict:
    sigma_line_values = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    sweep = []
    for sigma_line_cm in sigma_line_values:
        probability = offside_probability(margin_cm, camera_frame_uncertainty_cm, sigma_line_cm)["result"]["probability"]
        sweep.append({"sigma_line_cm": sigma_line_cm, "probability": probability})

    probabilities = [p["probability"] for p in sweep]
    min_probability = min(probabilities)
    max_probability = max(probabilities)

    return {
        "formula": "Sweep sigma_line_cm over [1.5, 4.0] step 0.5, recomputing P(offside) for each value",
        "inputs": {
            "margin_cm": margin_cm,
            "camera_frame_uncertainty_cm": camera_frame_uncertainty_cm,
            "sigma_line_cm_range": [1.5, 4.0],
        },
        "result": {
            "sweep": sweep,
            "min_probability": round(min_probability, 3),
            "max_probability": round(max_probability, 3),
            "robust": min_probability >= 0.95,
        },
    }


def counterfactual_timing(margin_cm: float, attacker_speed_ms: float) -> dict:
    if attacker_speed_ms <= 0:
        raise ValueError(f"attacker_speed_ms must be positive, got {attacker_speed_ms}")
    delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000
    return {
        "formula": "delay_needed_ms = (margin_cm / 100) / attacker_speed_ms * 1000",
        "inputs": {"margin_cm": margin_cm, "attacker_speed_ms": attacker_speed_ms},
        "result": {
            "delay_needed_ms": round(delay_needed_ms, 1),
            "frames_at_50fps": round(delay_needed_ms / 20, 2),
            "frames_at_25fps": round(delay_needed_ms / 40, 2),
            "detectable_at_50fps": (delay_needed_ms / 20) >= 1,
        },
    }


def handball_reaction(deflection_distance_m: float, ball_speed_ms: float, reaction_benchmark_ms: float = 250) -> dict:
    if deflection_distance_m <= 0:
        raise ValueError(f"deflection_distance_m must be positive, got {deflection_distance_m}")
    if ball_speed_ms <= 0:
        raise ValueError(f"ball_speed_ms must be positive, got {ball_speed_ms}")
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
            "verdict": "exceeds human reaction limits" if deficit_ratio > 1 else "within human reaction limits",
            "benchmark_sensitivity": [
                {"reaction_benchmark_ms": b, "deficit_ratio": round(b / time_available_ms, 2)}
                for b in [150, 200, 250, 300]
            ],
        },
    }


def fatigue_index(team_telemetry: dict) -> dict:
    sprints = team_telemetry["sprints"]
    line_gap = team_telemetry["line_gap_def_mid_m"]
    long_pass = team_telemetry["long_pass_share"]
    ppda = team_telemetry["ppda"]

    baseline_sprints = (sprints[0] + sprints[1]) / 2
    baseline_line_gap = (line_gap[0] + line_gap[1]) / 2
    baseline_long_pass = (long_pass[0] + long_pass[1]) / 2
    baseline_ppda = (ppda[0] + ppda[1]) / 2

    for name, baseline in [
        ("sprints", baseline_sprints),
        ("line_gap_def_mid_m", baseline_line_gap),
        ("long_pass_share", baseline_long_pass),
        ("ppda", baseline_ppda),
    ]:
        if baseline == 0:
            raise ValueError(f"baseline for {name} must be nonzero, got 0")

    sprint_decline = []
    line_stretch = []
    long_pass_drift = []
    pressing_decay = []
    index = []
    for i in range(len(sprints)):
        sd = (baseline_sprints - sprints[i]) / baseline_sprints
        ls = (line_gap[i] - baseline_line_gap) / baseline_line_gap
        lpd = (long_pass[i] - baseline_long_pass) / baseline_long_pass
        pd = (ppda[i] - baseline_ppda) / baseline_ppda
        sprint_decline.append(round(sd, 4))
        line_stretch.append(round(ls, 4))
        long_pass_drift.append(round(lpd, 4))
        pressing_decay.append(round(pd, 4))
        index.append(round(100 * (sd + ls + lpd + pd) / 4, 1))

    windows = TELEMETRY_DATA["windows"]
    peak_window = windows[index.index(max(index))]
    diff = index[-1] - index[2]
    if diff > 5:
        trend = "increasing"
    elif diff < -5:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "formula": (
            "fatigue_index[i] = 100 * mean(sprint_decline[i], line_stretch[i], "
            "long_pass_drift[i], pressing_decay[i]); baselines = mean(window0, window1)"
        ),
        "inputs": {
            "sprints": sprints,
            "line_gap_def_mid_m": line_gap,
            "long_pass_share": long_pass,
            "ppda": ppda,
        },
        "result": {
            "sprint_decline": sprint_decline,
            "line_stretch": line_stretch,
            "long_pass_drift": long_pass_drift,
            "pressing_decay": pressing_decay,
            "fatigue_index": index,
            "peak_window": peak_window,
            "trend": trend,
        },
    }


def fatigue_comparison(home_telemetry: dict, away_telemetry: dict) -> dict:
    home_index = fatigue_index(home_telemetry)["result"]["fatigue_index"]
    away_index = fatigue_index(away_telemetry)["result"]["fatigue_index"]
    difference = [round(a - h, 1) for h, a in zip(home_index, away_index)]
    more_fatigued_team = "away" if difference[-1] >= 0 else "home"
    return {
        "formula": "difference[i] = away_fatigue_index[i] - home_fatigue_index[i]; more_fatigued_team based on sign of difference[-1]",
        "inputs": {"home": home_telemetry, "away": away_telemetry},
        "result": {
            "home_fatigue_index": home_index,
            "away_fatigue_index": away_index,
            "difference": difference,
            "more_fatigued_team": more_fatigued_team,
        },
    }


def momentum_curve(events: list, event_weights: dict, decay: float = 0.85) -> list:
    for event in events:
        if event["type"] not in event_weights:
            raise ValueError(f"Unknown event type {event['type']!r} — not found in event_weights")
    minutes = range(0, 91, 5)
    curve = []
    for t in minutes:
        value = 0.0
        for event in events:
            if event["minute"] <= t:
                weight = event_weights[event["type"]]
                direction = 1 if event["team"] == "home" else -1
                if event["type"] == "pressure":
                    direction = -direction
                value += weight * direction * decay ** ((t - event["minute"]) / 5)
        curve.append({"minute": t, "value": round(value, 1)})
    return curve
