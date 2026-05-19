"""FastAPI app for the RetentionFlow dashboard.

    uvicorn backend.api.app:app --port 8000   (with src on PYTHONPATH)

One JSON API over three sources:
- GET  /api/pipeline            dbt run + test status
- GET  /api/data                Postgres warehouse overview
- GET  /api/warehouse/tables    every table + view in the warehouse schemas
- GET  /api/warehouse/sample    first N rows of one table or view
- GET  /api/models              MLflow registered churn-model versions
- GET  /api/feature-importance  champion model feature importances
- GET  /api/predictions         summary of the latest batch scoring
- GET  /api/shap                global SHAP summary + per-customer breakdowns
- GET  /api/runs                recent rebuild + scoring runs
- GET  /api/eval/model          DistilBERT email-quality model + metrics
- POST /api/score               run batch scoring (one-shot)
- GET  /api/score/stream        run batch scoring, streaming progress (SSE)
- GET  /api/pipeline/rebuild/stream  drop analytics + dbt build, timed (SSE)
- GET  /api/pipeline/run/stream      full pipeline: dbt + train + score (SSE)
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .email_eval import eval_model_card
from .rebuild import full_pipeline_events, rebuild_events
from .runs import recent_runs
from .scoring import (
    predictions_overview,
    run_batch_scoring,
    score_events,
    shap_overview,
)
from .services import (
    dbt_status,
    feature_importance,
    model_registry,
    warehouse_overview,
    warehouse_sample,
    warehouse_tables,
)

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


@app.get("/api/warehouse/tables")
def warehouse_tables_route() -> dict:
    """Every table and view in the warehouse schemas, with columns + row counts."""
    return warehouse_tables()


@app.get("/api/warehouse/sample")
def warehouse_sample_route(schema: str, table: str, limit: int = 25) -> dict:
    """First `limit` rows of a single warehouse table or view."""
    return warehouse_sample(schema, table, limit)


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


@app.get("/api/shap")
def shap() -> dict:
    """Global SHAP attribution and per-customer 'why at-risk' breakdowns."""
    return shap_overview()


@app.get("/api/runs")
def runs() -> dict:
    """Recent pipeline rebuilds and scoring runs."""
    return recent_runs()


@app.get("/api/eval/model")
def eval_model() -> dict:
    """Registered DistilBERT email-quality model and its champion metrics."""
    return eval_model_card()


@app.post("/api/score")
def score() -> dict:
    """Run batch scoring with the champion model; replaces serving.predictions."""
    return run_batch_scoring()


def _sse(events: Iterator[dict]) -> StreamingResponse:
    """Wrap an event generator as a Server-Sent Events response."""

    def stream() -> Iterator[str]:
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/score/stream")
def score_stream() -> StreamingResponse:
    """Run batch scoring, streaming a progress event per stage."""
    return _sse(score_events())


@app.get("/api/pipeline/rebuild/stream")
def rebuild_stream() -> StreamingResponse:
    """Drop the analytics schema and re-run dbt build, streaming timed progress."""
    return _sse(rebuild_events())


@app.get("/api/pipeline/run/stream")
def pipeline_run_stream() -> StreamingResponse:
    """Run the full pipeline — dbt rebuild, training, scoring — streaming progress."""
    return _sse(full_pipeline_events())
