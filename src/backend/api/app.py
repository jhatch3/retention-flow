"""FastAPI app for the RetentionFlow dashboard.

    uvicorn backend.api.app:app --port 8000   (with src on PYTHONPATH)

One JSON API over three sources:
- GET  /api/pipeline            dbt run + test status
- GET  /api/data                Postgres warehouse overview
- GET  /api/warehouse/tables    every table + view in the warehouse schemas
- GET  /api/warehouse/sample    first N rows of one table or view
- GET  /api/models              MLflow registered churn-model versions
- GET  /api/predictions         summary of the latest batch scoring
- GET  /api/shap                global SHAP summary + per-customer breakdowns
- GET  /api/runs                recent rebuild + scoring runs
- GET  /api/inbox/customers          at-risk customer queue (Triage Inbox)
- GET  /api/inbox/customers/{id}     one customer's triage detail
- POST /api/score               run batch scoring (one-shot)
- GET  /api/score/stream        run batch scoring, streaming progress (SSE)
- GET  /api/pipeline/rebuild/stream  drop analytics + dbt build, timed (SSE)
- GET  /api/pipeline/run/stream      dbt + (train) + score + (emails) (SSE)
- GET  /api/pipeline/run-quick/stream back-compat alias for train=0&emails=0
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .inbox import inbox_customer, inbox_customers
from .rebuild import (
    full_pipeline_events,
    pipeline_events,
    quick_pipeline_events,
    rebuild_events,
)
from .runs import recent_runs
from .scoring import (
    predictions_overview,
    run_batch_scoring,
    score_events,
    shap_overview,
)
from .services import (
    dbt_status,
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


# Only one heavy, DB-mutating job (scoring or a full pipeline run) may run at a
# time: concurrent runs race on serving.predictions, and the pipeline endpoints
# each DROP SCHEMA analytics. Non-blocking — a second caller gets 409, not a queue.
_PIPELINE_LOCK = threading.Lock()
_BUSY_DETAIL = "A scoring or pipeline run is already in progress."


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


@app.get("/api/predictions")
def predictions() -> dict:
    """Summary of the predictions currently in serving.predictions."""
    return predictions_overview()


@app.get("/api/shap")
def shap() -> dict:
    """Global SHAP attribution and per-customer 'why at-risk' breakdowns."""
    return shap_overview()


@app.get("/api/emails")
def emails(limit: int = 20) -> dict:
    """Recent retention emails from serving.generated_emails (most recent first)."""
    from .emails import recent_emails

    return recent_emails(limit=limit)


@app.get("/api/eval/insights")
def eval_insights() -> dict:
    """Aggregate the LLM-as-judge grades across all currently-scored emails."""
    from .insights import judge_insights

    return judge_insights()


@app.get("/api/eval/grades")
def eval_grades(limit: int = 50) -> dict:
    """Per-email judge output (reasoning, weaknesses, clauses, score)."""
    from .insights import judge_grades

    return judge_grades(limit=limit)


@app.get("/api/runs")
def runs() -> dict:
    """Recent pipeline rebuilds and scoring runs."""
    return recent_runs()


@app.get("/api/inbox/customers")
def inbox_customers_route(
    filter: str = "all", limit: int = 100, offset: int = 0
) -> dict:
    """At-risk customer queue — summaries sorted by risk, with tier totals."""
    return inbox_customers(risk_filter=filter, limit=limit, offset=offset)


@app.get("/api/inbox/customers/{customer_id}")
def inbox_customer_route(customer_id: str) -> dict:
    """Centre + right-pane triage detail for one at-risk customer."""
    detail = inbox_customer(customer_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"unknown customer: {customer_id}")
    return detail


@app.post("/api/score")
def score() -> dict:
    """Run batch scoring with the champion model; replaces serving.predictions."""
    if not _PIPELINE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=_BUSY_DETAIL)
    try:
        return run_batch_scoring()
    finally:
        _PIPELINE_LOCK.release()


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


def _single_flight_sse(make_events) -> StreamingResponse:
    """Stream an SSE generator under the global pipeline lock; 409 if busy.

    The lock is held for the lifetime of the stream and released when the
    generator is exhausted (or the client disconnects and the generator is
    closed), so two scoring/pipeline runs can never overlap.
    """
    if not _PIPELINE_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=_BUSY_DETAIL)

    def guarded() -> Iterator[dict]:
        try:
            yield from make_events()
        finally:
            _PIPELINE_LOCK.release()

    return _sse(guarded())


@app.get("/api/score/stream")
def score_stream() -> StreamingResponse:
    """Run batch scoring, streaming a progress event per stage."""
    return _single_flight_sse(score_events)


@app.get("/api/pipeline/rebuild/stream")
def rebuild_stream() -> StreamingResponse:
    """Drop the analytics schema and re-run dbt build, streaming timed progress."""
    return _single_flight_sse(rebuild_events)


@app.get("/api/pipeline/run/stream")
def pipeline_run_stream(
    train: bool = True,
    emails: bool = True,
    top_n: int = 50,
) -> StreamingResponse:
    """Run the pipeline with optional training and email generation, streaming
    progress events. Phases: dbt rebuild → (train) → score → (emails).

    ``top_n`` controls how many at-risk customers get a drafted email when
    ``emails=true``. Clamped to [1, 500] so a single request can't fan out
    indefinitely.
    """
    n = max(1, min(int(top_n), 500))
    return _single_flight_sse(
        lambda: pipeline_events(train=train, emails=emails, email_top_n=n)
    )


@app.get("/api/pipeline/run-quick/stream")
def pipeline_run_quick_stream() -> StreamingResponse:
    """Back-compat alias — dbt rebuild + scoring, no retrain, no emails."""
    return _single_flight_sse(quick_pipeline_events)
