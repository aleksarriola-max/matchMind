from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from backend.engines import analytics, explainer
from backend.engines.verifier import verify
from backend.llm import adapter
from backend.rag.retriever import get_retriever

FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

app = FastAPI(title="MatchMind")


@app.get("/")
def root():
    return FileResponse(FRONTEND_PATH)


@app.get("/api/health")
def health():
    info = adapter.health_info()
    return {
        "provider": info["provider"],
        "model": info["model"],
        "chunk_count": len(get_retriever().chunks),
    }


@app.get("/api/match")
def match():
    data = explainer.MATCH_DATA
    return {
        "match_id": data["match_id"],
        "competition": data["competition"],
        "home": data["home"],
        "away": data["away"],
        "score": data["score"],
        "events": data["events"],
        "momentum": analytics.momentum_curve(data["events"], analytics.TELEMETRY_DATA["event_weights_for_momentum"]),
    }


def _moment_analytics(moment_id: str, moment: dict) -> dict | None:
    if moment_id == "offside_27":
        return {
            "offside_probability": analytics.offside_probability(
                moment["margin_cm"], moment["camera_frame_uncertainty_cm"]
            ),
            "offside_sensitivity": analytics.offside_sensitivity(
                moment["margin_cm"], moment["camera_frame_uncertainty_cm"]
            ),
            "counterfactual_timing": analytics.counterfactual_timing(
                moment["margin_cm"], moment["attacker_speed_ms"]
            ),
        }
    if moment_id == "handball_38":
        return {
            "handball_reaction": analytics.handball_reaction(
                moment["deflection_distance_m"], moment["ball_speed_ms"]
            ),
        }
    if moment_id == "fatigue_71":
        telemetry = analytics.TELEMETRY_DATA
        return {
            "fatigue_index": {
                "home": analytics.fatigue_index(telemetry["teams"]["home"])["result"],
                "away": analytics.fatigue_index(telemetry["teams"]["away"])["result"],
            },
            "fatigue_comparison": analytics.fatigue_comparison(
                telemetry["teams"]["home"], telemetry["teams"]["away"]
            )["result"],
        }
    return None


@app.get("/api/moment/{moment_id}")
def moment(moment_id: str):
    moments = explainer.MATCH_DATA["moments"]
    if moment_id not in moments:
        raise HTTPException(status_code=404, detail=f"Unknown moment id: {moment_id!r}")
    result = dict(moments[moment_id])
    result["analytics"] = _moment_analytics(moment_id, moments[moment_id])
    return result


@app.get("/api/analytics")
def analytics_endpoint():
    offside = explainer.MATCH_DATA["moments"]["offside_27"]
    handball = explainer.MATCH_DATA["moments"]["handball_38"]
    telemetry = analytics.TELEMETRY_DATA
    home_fatigue = analytics.fatigue_index(telemetry["teams"]["home"])
    away_fatigue = analytics.fatigue_index(telemetry["teams"]["away"])
    momentum = analytics.momentum_curve(
        explainer.MATCH_DATA["events"], telemetry["event_weights_for_momentum"]
    )
    return {
        "offside_probability": analytics.offside_probability(
            offside["margin_cm"], offside["camera_frame_uncertainty_cm"]
        ),
        "offside_sensitivity": analytics.offside_sensitivity(
            offside["margin_cm"], offside["camera_frame_uncertainty_cm"]
        ),
        "counterfactual_timing": analytics.counterfactual_timing(
            offside["margin_cm"], offside["attacker_speed_ms"]
        ),
        "handball_reaction": analytics.handball_reaction(
            handball["deflection_distance_m"], handball["ball_speed_ms"]
        ),
        "fatigue_index": {
            "formula": home_fatigue["formula"],
            "inputs": {"windows": telemetry["windows"]},
            "result": {"home": home_fatigue["result"], "away": away_fatigue["result"]},
        },
        "momentum_curve": {
            "formula": (
                "momentum(t) = sum over events e where e.minute <= t of "
                "weight(e.type) * direction(e) * decay^((t - e.minute) / 5)"
            ),
            "inputs": {"decay": 0.85, "event_weights": telemetry["event_weights_for_momentum"]},
            "result": momentum,
            "summary": analytics.momentum_summary(momentum),
        },
        "fatigue_comparison": analytics.fatigue_comparison(
            telemetry["teams"]["home"], telemetry["teams"]["away"]
        ),
    }


VALID_PERSONAS = {"beginner", "analyst", "kid", "journalist", "coach"}


class AskRequest(BaseModel):
    question: str
    persona: str = "analyst"
    language: str = "English"

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, value: str) -> str:
        if value not in VALID_PERSONAS:
            raise ValueError(f"persona must be one of {sorted(VALID_PERSONAS)}")
        return value


@app.post("/api/ask")
def ask(request: AskRequest):
    moment_id = explainer.route(request.question)
    grounded = explainer.ground(request.question, moment_id)
    answer = explainer.compose_demo(request.persona, grounded["moment"], grounded["retrieved"])
    if grounded["moment"] is not None:
        evidence_texts = grounded["moment"]["evidence"]
    else:
        evidence_texts = [r["text"] for r in grounded["retrieved"]]
    verification = verify(answer, evidence_texts)
    explainability = explainer.explain(moment_id, grounded["moment"], grounded["retrieved"], verification)
    return {
        "answer": answer,
        "persona": request.persona,
        "language": "English",
        "moment_id": moment_id,
        "verification": verification,
        "explainability": explainability,
        "llm": adapter.health_info(),
    }


class OutrageRequest(BaseModel):
    take: str
    language: str = "English"


@app.post("/api/outrage")
def outrage(request: OutrageRequest):
    result = explainer.outrage(request.take)
    verification = None
    if result["counter"] is not None:
        verification = verify(result["counter"], result["evidence"])
    return {
        "take": request.take,
        "language": "English",
        "moment_id": result["moment_id"],
        "summary": result["summary"],
        "steelman": result["steelman"],
        "counter": result["counter"],
        "verdict": result["verdict"],
        "confidence": result["confidence"],
        "verification": verification,
        "lineage": result["lineage"],
    }
