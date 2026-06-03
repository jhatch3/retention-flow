"""Read-side services — gather dbt, Postgres, and MLflow state for the dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient
from sqlalchemy import bindparam, text

from ..db.session import engine
from ..ml.train import CHAMPION_ALIAS, EXPERIMENT, MLFLOW_URI, REGISTERED_MODEL

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_RESULTS = REPO_ROOT / "src" / "transform" / "target" / "run_results.json"


# --------------------------------------------------------------------------
# dbt
# --------------------------------------------------------------------------
def dbt_status() -> dict:
    """Summarise the last `dbt build` from its run_results.json artifact."""
    if not RUN_RESULTS.exists():
        return {"available": False}

    payload = json.loads(RUN_RESULTS.read_text())
    results = payload.get("results", [])

    models, tests = [], {"pass": 0, "fail": 0, "warn": 0}
    for r in results:
        unique_id = r.get("unique_id", "")
        status = r.get("status", "")
        kind = unique_id.split(".")[0]  # "model" | "test" | ...
        if kind == "model":
            models.append({
                "name": unique_id.split(".")[-1],
                "status": status,
                "execution_time": round(r.get("execution_time", 0.0), 2),
            })
        elif kind == "test":
            tests[status] = tests.get(status, 0) + 1

    models.sort(key=lambda m: m["name"])
    return {
        "available": True,
        "generated_at": payload.get("metadata", {}).get("generated_at"),
        "models": models,
        "model_count": len(models),
        "models_ok": sum(m["status"] == "success" for m in models),
        "tests": tests,
        "tests_total": sum(tests.values()),
    }


# --------------------------------------------------------------------------
# Postgres warehouse
# --------------------------------------------------------------------------
def warehouse_overview() -> dict:
    """Row counts, headline stats, and churn-by-segment across the warehouse."""
    with engine.connect() as conn:
        gold = conn.execute(text(
            "select count(*) as rows, avg(churned::int) as churn_rate "
            "from analytics.customer_features"
        )).mappings().one()

        splits = conn.execute(text(
            "select split, count(*) as rows "
            "from analytics.customer_features group by split order by split"
        )).mappings().all()

        # churn rate split by repeat vs one-time customers
        segments = conn.execute(text(
            "select case when frequency >= 2 then 'repeat' else 'one-time' end as segment, "
            "count(*) as rows, avg(churned::int) as churn_rate "
            "from analytics.customer_features group by 1 order by 1"
        )).mappings().all()

        raw_orders = conn.execute(
            text("select count(*) from raw.olist_orders")
        ).scalar_one()
        synthetic_orders = conn.execute(
            text("select count(*) from synthetic.orders")
        ).scalar_one()

    return {
        "gold_rows": int(gold["rows"]),
        "gold_churn_rate": round(float(gold["churn_rate"]), 4),
        "splits": {s["split"]: int(s["rows"]) for s in splits},
        "segments": [
            {
                "segment": s["segment"],
                "rows": int(s["rows"]),
                "churn_rate": round(float(s["churn_rate"]), 4),
            }
            for s in segments
        ],
        "raw_orders": int(raw_orders),
        "synthetic_orders": int(synthetic_orders),
    }


# --------------------------------------------------------------------------
# Warehouse table explorer
# --------------------------------------------------------------------------
# Schemas exposed in the dashboard's Warehouse tab — the medallion layers,
# the synthetic augmentation, and the model-serving outputs.
WAREHOUSE_SCHEMAS = ("raw", "synthetic", "analytics", "serving")
MAX_SAMPLE_ROWS = 500


def _quote_ident(identifier: str) -> str:
    """Quote a SQL identifier, escaping any embedded double quotes."""
    return '"' + identifier.replace('"', '""') + '"'


def warehouse_tables() -> dict:
    """Every table and view in the warehouse schemas, with columns + row counts."""
    objects_stmt = text(
        "select table_schema, table_name, table_type "
        "from information_schema.tables where table_schema in :schemas "
        "order by table_schema, table_name"
    ).bindparams(bindparam("schemas", expanding=True))

    tables: list[dict] = []
    with engine.connect() as conn:
        objects = conn.execute(
            objects_stmt, {"schemas": list(WAREHOUSE_SCHEMAS)}
        ).mappings().all()

        for obj in objects:
            schema, name = obj["table_schema"], obj["table_name"]
            columns = conn.execute(text(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = :s and table_name = :t "
                "order by ordinal_position"
            ), {"s": schema, "t": name}).mappings().all()

            row_count = conn.execute(text(
                f"select count(*) from {_quote_ident(schema)}.{_quote_ident(name)}"
            )).scalar_one()

            tables.append({
                "schema": schema,
                "name": name,
                "kind": "view" if obj["table_type"] == "VIEW" else "table",
                "row_count": int(row_count),
                "columns": [
                    {"name": c["column_name"], "type": c["data_type"]}
                    for c in columns
                ],
            })

    return {"tables": tables}


def warehouse_sample(schema: str, table: str, limit: int) -> dict:
    """Return the first `limit` rows of a single warehouse table or view."""
    if schema not in WAREHOUSE_SCHEMAS:
        return {"error": f"'{schema}' is not a warehouse schema"}
    limit = max(1, min(limit, MAX_SAMPLE_ROWS))

    with engine.connect() as conn:
        # Confirm the object exists before interpolating its name into SQL.
        exists = conn.execute(text(
            "select 1 from information_schema.tables "
            "where table_schema = :s and table_name = :t"
        ), {"s": schema, "t": table}).first()
        if not exists:
            return {"error": f"table '{schema}.{table}' was not found"}

        result = conn.execute(
            text(
                f"select * from {_quote_ident(schema)}.{_quote_ident(table)} "
                f"limit :n"
            ),
            {"n": limit},
        )
        columns = list(result.keys())
        rows = [list(row) for row in result.all()]

    return {
        "schema": schema,
        "table": table,
        "columns": columns,
        "rows": rows,
        "row_limit": limit,
    }


# --------------------------------------------------------------------------
# MLflow registry
# --------------------------------------------------------------------------
def model_registry() -> dict:
    """Registered churn-model versions, their metrics, and the champion."""
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()

    try:
        champion_version = client.get_model_version_by_alias(
            REGISTERED_MODEL, CHAMPION_ALIAS
        ).version
    except Exception:
        champion_version = None

    versions, champion_metrics = [], {}
    for mv in client.search_model_versions(f"name='{REGISTERED_MODEL}'"):
        metrics = {}
        try:
            metrics = client.get_run(mv.run_id).data.metrics
        except Exception:
            pass
        is_champion = mv.version == champion_version
        if is_champion:
            champion_metrics = {
                k.removeprefix("test_"): round(v, 4)
                for k, v in metrics.items()
                if k.startswith("test_")
            }
        versions.append({
            "version": mv.version,
            "is_champion": is_champion,
            "decision_threshold": mv.tags.get("decision_threshold"),
            "roc_auc": round(metrics["test_roc_auc"], 4)
            if "test_roc_auc" in metrics else None,
            "pr_auc": round(metrics["test_pr_auc"], 4)
            if "test_pr_auc" in metrics else None,
            "created_at": datetime.fromtimestamp(
                mv.creation_timestamp / 1000, tz=timezone.utc
            ).isoformat(),
        })
    versions.sort(key=lambda v: int(v["version"]), reverse=True)

    return {
        "model_name": REGISTERED_MODEL,
        "experiment": EXPERIMENT,
        "champion_version": champion_version,
        "champion_metrics": champion_metrics,
        "versions": versions,
    }
