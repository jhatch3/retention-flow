"""Read + inline-scoring services for the DistilBERT email-quality eval.

Tier 1 of the two-tier eval stack. ``eval_model_card`` reports the registered
DistilBERT model the way ``services.model_registry`` does for the churn model;
``score_email_quality`` runs the champion classifier over a single email.

MLflow is imported lazily so importing this module stays cheap.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..eval.distilbert.model import CHAMPION_ALIAS, MLFLOW_URI, REGISTERED_MODEL
from ..eval.distilbert.predict import PASS_THRESHOLD


def eval_model_card() -> dict:
    """The registered DistilBERT email-quality model and its champion metrics.

    Returns ``{"available": False}`` when the model has not been trained yet.
    """
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()

    try:
        champion = client.get_model_version_by_alias(REGISTERED_MODEL, CHAMPION_ALIAS)
    except Exception:
        return {"available": False, "model_name": REGISTERED_MODEL}

    metrics: dict = {}
    params: dict = {}
    try:
        run = client.get_run(champion.run_id)
        metrics, params = run.data.metrics, run.data.params
    except Exception:
        pass

    def _metric(key: str) -> float | None:
        return round(metrics[key], 4) if key in metrics else None

    return {
        "available": True,
        "model_name": REGISTERED_MODEL,
        "champion_version": champion.version,
        "base_model": params.get("base_model"),
        "n_train": int(params["n_train"]) if "n_train" in params else None,
        "pass_threshold": PASS_THRESHOLD,
        "metrics": {
            "test_accuracy": _metric("test_accuracy"),
            "test_f1_macro": _metric("test_f1_macro"),
            "test_mae_grades": _metric("test_mae_grades"),
            "validation_accuracy": _metric("validation_accuracy"),
        },
        "created_at": datetime.fromtimestamp(
            champion.creation_timestamp / 1000, tz=timezone.utc
        ).isoformat(),
    }
