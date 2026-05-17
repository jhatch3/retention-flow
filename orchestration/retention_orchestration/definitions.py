"""Dagster definitions for the RetentionFlow pipeline.

Via the dagster-dbt integration, every dbt model becomes a Dagster asset and
every dbt test becomes an asset check. The churn model is a downstream asset
that trains on the gold table and registers itself in MLflow. A nightly
schedule materialises the whole graph: dbt build, then retrain + register.

The one-time CSV-to-`raw` migration is deliberately NOT modelled here — the
asset graph starts from the raw tables already present in Postgres. See
docs/adr/0003-dagster-for-orchestration.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dagster import (
    AssetKey,
    Definitions,
    MaterializeResult,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_DIR = REPO_ROOT / "transform"

# Make the `backend` package importable when the churn-model asset runs.
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

dbt_project = DbtProject(
    project_dir=TRANSFORM_DIR,
    profiles_dir=TRANSFORM_DIR,
)
# Generate target/manifest.json from the dbt project when running `dagster dev`.
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def retention_dbt_assets(context, dbt: DbtCliResource):
    """All dbt models as assets; all dbt tests as asset checks."""
    yield from dbt.cli(["build"], context=context).stream()


@asset(
    deps=[AssetKey("customer_features")],
    group_name="ml",
    description="XGBoost churn model — retrained on the gold table and "
    "registered in MLflow.",
)
def churn_model(context) -> MaterializeResult:
    """Retrain the churn model from the current gold table and register it.

    Runs in the same Dagster run as the dbt build. The MLflow run is tagged
    with the Dagster run id, and the Dagster asset records the MLflow run id —
    so the two systems cross-reference each other.
    """
    from backend.ml.train import train_and_log

    out = train_and_log(run_tags={"dagster_run_id": context.run_id})
    validation = out["results"]["validation"]
    return MaterializeResult(
        metadata={
            "dagster_run_id": context.run_id,
            "mlflow_run_id": out["run_id"],
            "registered_model": out["model_name"],
            "model_version": out["model_version"],
            "validation_roc_auc": round(validation["roc_auc"], 4),
            "validation_pr_auc": round(validation["pr_auc"], 4),
        }
    )


# One nightly job over the full graph: dbt build, then retrain + register.
nightly_job = define_asset_job(name="nightly_pipeline", selection="*")

nightly_schedule = ScheduleDefinition(
    name="nightly_refresh",
    job=nightly_job,
    cron_schedule="0 2 * * *",
)

defs = Definitions(
    assets=[retention_dbt_assets, churn_model],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt_project,
            profiles_dir=str(TRANSFORM_DIR),
        ),
    },
    schedules=[nightly_schedule],
)
