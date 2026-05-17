"""Batch scoring — score the gold table with the champion model.

`score_events` is a generator that yields a progress event after each stage;
the dashboard streams it as Server-Sent Events for a live log. `run_batch_scoring`
is the one-shot equivalent.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

import mlflow
import mlflow.xgboost
import pandas as pd
from mlflow.tracking import MlflowClient
from sqlalchemy import text

from ..db.session import engine
from ..ml.data import FEATURE_COLUMNS, load_gold, prepare_features
from ..ml.train import CHAMPION_ALIAS, MLFLOW_URI, REGISTERED_MODEL

PREDICTIONS_TABLE = "serving.predictions"


def _event(stage: str, message: str, progress: float, **extra) -> dict:
    return {
        "stage": stage,
        "message": message,
        "progress": progress,
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        **extra,
    }


def score_events() -> Iterator[dict]:
    """Run batch scoring, yielding a progress event after each stage."""
    yield _event("start", "Starting batch scoring run", 0.05)

    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()
    version = client.get_model_version_by_alias(REGISTERED_MODEL, CHAMPION_ALIAS)
    model = mlflow.xgboost.load_model(f"models:/{REGISTERED_MODEL}@{CHAMPION_ALIAS}")
    threshold = float(version.tags.get("decision_threshold", 0.5))
    model_version = f"{REGISTERED_MODEL}:v{version.version}"
    yield _event(
        "model",
        f"Loaded champion {model_version} (threshold {threshold:.3f})",
        0.25,
    )

    gold = load_gold()
    yield _event("data", f"Loaded {len(gold):,} customers from the gold table", 0.45)

    X = prepare_features(gold[FEATURE_COLUMNS])
    yield _event("features", f"Prepared {len(FEATURE_COLUMNS)} features", 0.55)

    proba = model.predict_proba(X)[:, 1]
    labels = proba >= threshold
    churn = int(labels.sum())
    yield _event(
        "score",
        f"Scored {len(gold):,} customers — {churn:,} predicted to churn",
        0.80,
    )

    predictions = pd.DataFrame({
        "customer_unique_id": gold["customer_unique_id"],
        "snapshot_date": gold["snapshot_date"],
        "model_version": model_version,
        "churn_probability": proba,
        "threshold": threshold,
        "predicted_label": labels,
    })
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {PREDICTIONS_TABLE}"))
    predictions.to_sql(
        "predictions", engine, schema="serving", if_exists="append", index=False
    )
    yield _event("write", f"Wrote {len(predictions):,} rows to {PREDICTIONS_TABLE}", 0.95)

    result = {
        "scored_count": int(len(predictions)),
        "predicted_churn": churn,
        "threshold": round(threshold, 4),
        "model_version": model_version,
    }
    yield _event("done", "Batch scoring complete", 1.0, done=True, result=result)


def run_batch_scoring() -> dict:
    """One-shot batch scoring — consume the event stream, return the result."""
    result: dict = {}
    for event in score_events():
        if event.get("done"):
            result = event["result"]
    return result


def predictions_overview() -> dict:
    """Summarise the predictions currently in `serving.predictions`."""
    with engine.connect() as conn:
        total = conn.execute(
            text(f"select count(*) from {PREDICTIONS_TABLE}")
        ).scalar_one()
        if total == 0:
            return {"scored": False}

        summary = conn.execute(text(
            f"select count(*) filter (where predicted_label) as churn, "
            f"avg(churn_probability) as avg_prob, "
            f"max(model_version) as model_version, "
            f"max(predicted_at) as scored_at from {PREDICTIONS_TABLE}"
        )).mappings().one()

        histogram = conn.execute(text(
            f"select least(width_bucket(churn_probability, 0, 1, 10), 10) as bucket, "
            f"count(*) as n from {PREDICTIONS_TABLE} group by 1 order by 1"
        )).mappings().all()

        top = conn.execute(text(
            f"select customer_unique_id, churn_probability from {PREDICTIONS_TABLE} "
            f"order by churn_probability desc limit 10"
        )).mappings().all()

    scored_at = summary["scored_at"]
    return {
        "scored": True,
        "total": int(total),
        "predicted_churn": int(summary["churn"]),
        "avg_probability": round(float(summary["avg_prob"]), 4),
        "model_version": summary["model_version"],
        "scored_at": scored_at.isoformat() if scored_at else None,
        "risk_histogram": [
            {"bucket": int(h["bucket"]), "count": int(h["n"])} for h in histogram
        ],
        "top_at_risk": [
            {
                "customer_unique_id": t["customer_unique_id"],
                "churn_probability": round(float(t["churn_probability"]), 4),
            }
            for t in top
        ],
    }
