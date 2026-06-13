from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.engines import explainer
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
        "momentum": data["momentum"],
    }


@app.get("/api/moment/{moment_id}")
def moment(moment_id: str):
    moments = explainer.MATCH_DATA["moments"]
    if moment_id not in moments:
        raise HTTPException(status_code=404, detail=f"Unknown moment id: {moment_id!r}")
    return moments[moment_id]
