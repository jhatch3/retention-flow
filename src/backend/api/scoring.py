"""Batch scoring — score the gold table with the champion model.

`score_events` is a generator that yields a progress event per stage; the
dashboard streams it as Server-Sent Events. As well as predictions, it
computes exact TreeSHAP attributions, persists per-feature SHAP rows for the
top at-risk customers to `serving.shap_values`, and writes a global
mean-|SHAP| summary.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from mlflow.tracking import MlflowClient
from sqlalchemy import text

from ..db.session import engine
from ..ml.data import FEATURE_COLUMNS, load_gold, prepare_features
from ..ml.train import CHAMPION_ALIAS, MLFLOW_URI, REGISTERED_MODEL
from .runs import record_run

PREDICTIONS_TABLE = "serving.predictions"
SHAP_TABLE = "serving.shap_values"
TOP_SHAP_CUSTOMERS = 200
SHAP_SUMMARY = Path(__file__).resolve().parents[3] / "data" / "shap_summary.json"


def _event(stage: str, message: str, progress: float, **extra) -> dict:
    return {
        "stage": stage,
        "message": message,
        "progress": progress,
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        **extra,
    }


def _persist_shap(
    conn, gold: pd.DataFrame, X: pd.DataFrame, shap: np.ndarray, proba: np.ndarray
) -> int:
    """Persist per-feature SHAP rows for the top-N at-risk customers.

    Runs on the caller's connection so it shares the predictions delete/insert
    transaction: the idmap reads the just-inserted predictions and the SHAP
    rows commit atomically with them.
    """
    idmap = dict(
        conn.execute(
            text(f"select customer_unique_id, id from {PREDICTIONS_TABLE}")
        ).all()
    )

    top = np.argsort(-proba)[:TOP_SHAP_CUSTOMERS]
    abs_shap = np.abs(shap)
    rows: list[dict] = []
    for i in top:
        pid = idmap.get(gold["customer_unique_id"].iat[int(i)])
        if pid is None:
            continue
        ranks = (-abs_shap[i]).argsort().argsort() + 1
        for j, feat in enumerate(FEATURE_COLUMNS):
            raw = X[feat].iat[int(i)]
            value = pd.to_numeric(pd.Series([raw]), errors="coerce").iat[0]
            rows.append({
                "prediction_id": int(pid),
                "feature_name": feat,
                "feature_value": None if pd.isna(value) else float(value),
                "shap_value": float(shap[i, j]),
                "rank": int(ranks[j]),
            })
    if rows:
        pd.DataFrame(rows).to_sql(
            "shap_values", conn, schema="serving", if_exists="append", index=False
        )
    return len(rows)


def _write_shap_summary(shap: np.ndarray, base_value: float) -> None:
    """Write the global mean-|SHAP| attribution to a JSON file."""
    mean_abs = np.abs(shap).mean(axis=0)
    summary = {
        "base_value": round(base_value, 4),
        "features": sorted(
            (
                {"feature": f, "mean_abs_shap": round(float(v), 4)}
                for f, v in zip(FEATURE_COLUMNS, mean_abs)
            ),
            key=lambda d: d["mean_abs_shap"],
            reverse=True,
        ),
    }
    SHAP_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SHAP_SUMMARY.write_text(json.dumps(summary, indent=1))


def score_events() -> Iterator[dict]:
    """Run batch scoring, yielding a progress event after each stage."""
    t0 = time.perf_counter()
    yield _event("start", "Starting batch scoring run", 0.05)

    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()
    version = client.get_model_version_by_alias(REGISTERED_MODEL, CHAMPION_ALIAS)
    model = mlflow.xgboost.load_model(f"models:/{REGISTERED_MODEL}@{CHAMPION_ALIAS}")
    threshold = float(version.tags.get("decision_threshold", 0.5))
    model_version = f"{REGISTERED_MODEL}:v{version.version}"
    yield _event("model", f"Loaded champion {model_version}", 0.2)

    gold = load_gold()
    yield _event("data", f"Loaded {len(gold):,} customers from the gold table", 0.4)

    X = prepare_features(gold[FEATURE_COLUMNS])
    proba = model.predict_proba(X)[:, 1]
    labels = proba >= threshold
    churn = int(labels.sum())
    yield _event(
        "score", f"Scored {len(gold):,} customers — {churn:,} predicted to churn", 0.6
    )

    # Exact TreeSHAP from the booster (margin space; last column is the base value).
    contribs = model.get_booster().predict(
        xgb.DMatrix(X, enable_categorical=True), pred_contribs=True
    )
    shap = contribs[:, :-1]
    base_value = float(contribs[0, -1])
    yield _event("shap", f"Computed SHAP attributions for {len(gold):,} customers", 0.78)

    predictions = pd.DataFrame({
        "customer_unique_id": gold["customer_unique_id"].to_numpy(),
        "snapshot_date": gold["snapshot_date"].to_numpy(),
        "model_version": model_version,
        "churn_probability": proba,
        "threshold": threshold,
        "predicted_label": labels,
        "base_value": base_value,
    })
    # Delete + reinsert predictions and SHAP in ONE transaction so a failure
    # mid-write can't leave serving.predictions empty. Deleting predictions
    # cascades to serving.shap_values (FK ON DELETE CASCADE), clearing stale
    # rows rather than letting them accumulate/orphan across runs.
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {PREDICTIONS_TABLE}"))
        predictions.to_sql(
            "predictions", conn, schema="serving", if_exists="append", index=False
        )
        shap_rows = _persist_shap(conn, gold, X, shap, proba)
    _write_shap_summary(shap, base_value)
    yield _event(
        "write",
        f"Wrote {len(predictions):,} predictions + {shap_rows:,} SHAP rows",
        0.95,
    )

    result = {
        "scored_count": int(len(predictions)),
        "predicted_churn": churn,
        "threshold": round(threshold, 4),
        "model_version": model_version,
    }
    yield _event("done", "Batch scoring complete", 1.0, done=True, result=result)
    record_run(
        "scoring", "success", t0,
        f"{churn:,} of {len(predictions):,} customers flagged",
    )


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
            f"select p.customer_unique_id, p.churn_probability, dn.display_name "
            f"from {PREDICTIONS_TABLE} p "
            f"left join serving.customer_display_names dn "
            f"  on dn.customer_unique_id = p.customer_unique_id "
            f"order by p.churn_probability desc limit 10"
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
                "display_name": t["display_name"]
                or f"Customer {t['customer_unique_id'][:8].upper()}",
                "churn_probability": round(float(t["churn_probability"]), 4),
            }
            for t in top
        ],
    }


def shap_overview() -> dict:
    """Global SHAP summary plus per-customer breakdowns for the top at-risk."""
    if SHAP_SUMMARY.exists():
        global_summary = json.loads(SHAP_SUMMARY.read_text())
    else:
        global_summary = {"base_value": None, "features": []}

    with engine.connect() as conn:
        rows = conn.execute(text(
            f"select p.customer_unique_id, p.churn_probability, "
            f"s.feature_name, s.shap_value, s.feature_value, s.rank "
            f"from {SHAP_TABLE} s join {PREDICTIONS_TABLE} p on s.prediction_id = p.id "
            f"order by p.churn_probability desc, s.rank"
        )).mappings().all()

    customers: dict[str, dict] = {}
    for r in rows:
        cust = customers.setdefault(
            r["customer_unique_id"],
            {
                "customer_unique_id": r["customer_unique_id"],
                "churn_probability": round(float(r["churn_probability"]), 4),
                "contributions": [],
            },
        )
        cust["contributions"].append({
            "feature": r["feature_name"],
            "shap_value": round(float(r["shap_value"]), 4),
            "feature_value": (
                round(float(r["feature_value"]), 3)
                if r["feature_value"] is not None
                else None
            ),
            "rank": r["rank"],
        })

    return {
        "available": bool(global_summary["features"]),
        "global": global_summary,
        "customers": list(customers.values())[:24],
    }
