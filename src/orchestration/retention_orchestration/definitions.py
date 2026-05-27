"""Dagster definitions for the RetentionFlow pipeline.

Via the dagster-dbt integration, every dbt model becomes a Dagster asset and
every dbt test becomes an asset check. The churn model is a downstream asset
that trains on the gold table and registers itself in MLflow; ``batch_predictions``
then scores the gold table with the champion, ``retention_emails`` drafts
emails for the top-N at-risk customers via the async batch generator, and
``eval_scores`` grades every fresh email with the adversarial LLM-as-judge. A
nightly schedule materialises the whole graph: dbt build → retrain → score →
emails → judge.

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

REPO_ROOT = Path(__file__).resolve().parents[3]
TRANSFORM_DIR = REPO_ROOT / "src" / "transform"

# Make the `backend` and `ai` packages importable when the downstream assets run.
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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


@asset(
    deps=[churn_model],
    group_name="ml",
    description="Batch scoring — score the gold table with the champion model "
    "and persist predictions + SHAP attribution to serving.",
)
def batch_predictions(context) -> MaterializeResult:
    """Run batch scoring for every customer in the gold table."""
    from backend.api.scoring import run_batch_scoring

    result = run_batch_scoring()
    return MaterializeResult(metadata={k: result[k] for k in sorted(result)})


@asset(
    deps=[batch_predictions],
    group_name="ai",
    description="Async parallel email generation for the top-N at-risk customers; "
    "drafts land in serving.generated_emails.",
)
def retention_emails(context) -> MaterializeResult:
    """Generate retention emails for the top-N at-risk customers.

    Top-N + concurrency are configured at the asset level; the implementation
    in ``src/ai/batch.py`` fans out via ``AsyncAnthropic`` bounded by a
    semaphore.
    """
    from ai.batch import (
        DEFAULT_CONCURRENCY,
        DEFAULT_TOP_N,
        generate_top_n_emails,
    )

    summary = generate_top_n_emails(
        top_n=DEFAULT_TOP_N, concurrency=DEFAULT_CONCURRENCY
    )
    return MaterializeResult(metadata={k: summary[k] for k in sorted(summary)})


@asset(
    deps=[retention_emails],
    group_name="ai",
    description="Adversarial LLM-as-judge grading of every generated email "
    "that does not yet have a judge grade. Persists score, certainty, "
    "reasoning, weaknesses, and per-clause verdicts to serving.eval_scores.",
)
def eval_scores(context) -> MaterializeResult:
    """Grade every fresh retention email with the adversarial judge.

    Per-customer success criteria are synthesised from each customer's SHAP
    profile in ``ai/judge_batch.py`` — mirroring the same rules the generator
    follows. Idempotent: only emails missing from ``serving.eval_scores`` are
    graded, so re-running this asset is cheap.
    """
    from ai.judge_batch import (
        DEFAULT_CONCURRENCY,
        DEFAULT_LIMIT,
        grade_unjudged_emails,
    )

    summary = grade_unjudged_emails(
        limit=DEFAULT_LIMIT, concurrency=DEFAULT_CONCURRENCY
    )
    return MaterializeResult(metadata={k: summary[k] for k in sorted(summary)})


# One nightly job over the full graph: dbt → train → score → emails → judge.
nightly_job = define_asset_job(name="nightly_pipeline", selection="*")

nightly_schedule = ScheduleDefinition(
    name="nightly_refresh",
    job=nightly_job,
    cron_schedule="0 2 * * *",
)

defs = Definitions(
    assets=[
        retention_dbt_assets,
        churn_model,
        batch_predictions,
        retention_emails,
        eval_scores,
    ],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt_project,
            profiles_dir=str(TRANSFORM_DIR),
        ),
    },
    schedules=[nightly_schedule],
)
