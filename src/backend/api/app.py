"""FastAPI app for the RetentionFlow dashboard.

    uvicorn backend.api.app:app --port 8000   (with src on PYTHONPATH)

One JSON API over three sources:
- GET  /api/pipeline            dbt run + test status
- GET  /api/data                Postgres warehouse overview
- GET  /api/models              MLflow registered churn-model versions
- GET  /api/feature-importance  champion model feature importances
- GET  /api/predictions         summary of the latest batch scoring
- POST /api/score               run batch scoring (one-shot)
- GET  /api/score/stream        run batch scoring, streaming progress (SSE)
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .scoring import predictions_overview, run_batch_scoring, score_events
from .services import dbt_status, feature_importance, model_registry, warehouse_overview

app = FastAPI(title="RetentionFlow Dashboard API", version="0.2.0")

# Allow the Vite dev server (default port 5173) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/pipeline")
def pipeline() -> dict:
    """dbt build + test status from the latest run_results.json."""
    return dbt_status()


@app.get("/api/data")
def data() -> dict:
    """Row counts, headline stats, and churn-by-segment."""
    return warehouse_overview()


@app.get("/api/models")
def models() -> dict:
    """Registered churn-model versions and the current champion."""
    return model_registry()


@app.get("/api/feature-importance")
def importance() -> dict:
    """Champion model feature importances."""
    return feature_importance()


@app.get("/api/predictions")
def predictions() -> dict:
    """Summary of the predictions currently in serving.predictions."""
    return predictions_overview()


@app.post("/api/score")
def score() -> dict:
    """Run batch scoring with the champion model; replaces serving.predictions."""
    return run_batch_scoring()


@app.get("/api/score/stream")
def score_stream() -> StreamingResponse:
    """Run batch scoring, streaming a progress event per stage (Server-Sent Events)."""

    def sse() -> Iterator[str]:
        for event in score_events():
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
