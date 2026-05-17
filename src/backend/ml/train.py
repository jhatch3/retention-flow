"""Train the churn XGBoost model, log the run, and register it in MLflow.

    python -m backend.ml.train

Reads the gold table, trains on the `train` split, **tunes the decision
threshold on the validation PR curve** (the highest-precision threshold that
still catches 85% of churners), evaluates on `test` and `validation`, logs
everything to a local MLflow store (`mlruns/`), then registers the model and
moves the `champion` alias to the new version.

The notebook imports ``build_model`` / ``evaluate`` / ``tune_threshold`` from
here so the notebook and the script produce an identical model and threshold.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from .data import load_splits

REPO_ROOT = Path(__file__).resolve().parents[3]
MLFLOW_URI = (REPO_ROOT / "mlruns").as_uri()
EXPERIMENT = "churn-xgboost"
REGISTERED_MODEL = "churn-xgboost"
CHAMPION_ALIAS = "champion"
RUN_NAME = "xgboost-v1"

# Decision-threshold tuning: pick the highest-precision threshold that still
# catches this fraction of churners. A plain F-beta objective is gamed here —
# churn is the ~80% majority class, so "predict everyone" maximises it.
TARGET_RECALL = 0.85

# Fixed hyperparameters for the baseline model.
PARAMS: dict = dict(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    eval_metric="aucpr",
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


def build_model(y_train: pd.Series) -> XGBClassifier:
    """Configured XGBoost classifier.

    ``scale_pos_weight`` is set from the class balance — churn is the ~80%
    majority class, so this down-weights it and keeps the model honest about
    the minority (retained) customers.
    """
    pos = int((y_train == 1).sum())
    neg = int((y_train == 0).sum())
    scale_pos_weight = neg / pos if pos else 1.0
    return XGBClassifier(scale_pos_weight=scale_pos_weight, **PARAMS)


def tune_threshold(
    model: XGBClassifier, X, y, target_recall: float = TARGET_RECALL
) -> float:
    """Pick a decision threshold from the PR curve.

    Returns the highest-precision threshold whose recall is still at least
    ``target_recall``. Call this on the **validation** split — the threshold is
    a fitted decision, so tuning it on the test split would leak.
    """
    proba = model.predict_proba(X)[:, 1]
    precision, recall, thresholds = precision_recall_curve(y, proba)
    # precision/recall carry one extra point (recall=0) with no threshold
    precision, recall = precision[:-1], recall[:-1]
    qualifying = np.flatnonzero(recall >= target_recall)
    if qualifying.size == 0:
        return float(thresholds.min())
    best = qualifying[int(np.argmax(precision[qualifying]))]
    return float(thresholds[best])


def evaluate(model: XGBClassifier, X, y, threshold: float = 0.5) -> dict[str, float]:
    """Probability- and threshold-based metrics for one split.

    ``roc_auc`` / ``pr_auc`` / ``brier`` are threshold-independent; the rest
    are measured at ``threshold``.
    """
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y, proba)),
        "pr_auc": float(average_precision_score(y, proba)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, proba)),
    }


def train_and_log(run_tags: dict[str, str] | None = None) -> dict:
    """Full run: fit, tune the threshold, evaluate, log, and register.

    ``run_tags`` are attached to the MLflow run — the Dagster asset passes its
    run id here, so the MLflow run and the Dagster run cross-reference.
    """
    splits, feature_cols = load_splits()
    X_train, y_train = splits["train"]

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT)

    with mlflow.start_run(run_name=RUN_NAME) as run:
        if run_tags:
            mlflow.set_tags(run_tags)
        model = build_model(y_train)
        model.fit(X_train, y_train)

        # Tune the decision threshold on the validation PR curve (F2).
        threshold = tune_threshold(model, *splits["validation"])

        mlflow.log_params(PARAMS)
        mlflow.log_param("scale_pos_weight", round(model.scale_pos_weight, 4))
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("n_train", len(y_train))
        mlflow.log_param("train_churn_rate", round(float(y_train.mean()), 4))
        mlflow.log_param("threshold_objective", f"recall>={TARGET_RECALL}")
        mlflow.log_param("tuned_threshold", round(threshold, 4))

        # test is held out from both training and threshold tuning.
        results: dict[str, dict] = {}
        for name in ("test", "validation"):
            X, y = splits[name]
            metrics = evaluate(model, X, y, threshold=threshold)
            results[name] = metrics
            mlflow.log_metrics({f"{name}_{k}": v for k, v in metrics.items()})

        importance = pd.Series(
            model.feature_importances_, index=feature_cols, name="importance"
        ).sort_values(ascending=False)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feature_importance.csv"
            importance.to_csv(path)
            mlflow.log_artifact(str(path))

        logged = mlflow.xgboost.log_model(model, name="model")
        run_id = run.info.run_id

    # Register the model, tag it with its operating threshold, and move the
    # champion alias to the new version.
    version = mlflow.register_model(logged.model_uri, REGISTERED_MODEL)
    client = MlflowClient()
    client.set_registered_model_alias(REGISTERED_MODEL, CHAMPION_ALIAS, version.version)
    client.set_model_version_tag(
        REGISTERED_MODEL, version.version, "decision_threshold", f"{threshold:.4f}"
    )

    return {
        "run_id": run_id,
        "model_name": REGISTERED_MODEL,
        "model_version": version.version,
        "threshold": threshold,
        "results": results,
        "importance": importance,
    }


def main() -> int:
    argparse.ArgumentParser(description="Train the churn XGBoost model.").parse_args()
    out = train_and_log()

    print(f"MLflow run: {out['run_id']}  (tracking: {MLFLOW_URI})")
    print(
        f"Registered: {out['model_name']} v{out['model_version']} "
        f"-> @{CHAMPION_ALIAS}"
    )
    print(f"Tuned threshold (recall>={TARGET_RECALL} on validation): {out['threshold']:.3f}")
    for split, metrics in out["results"].items():
        line = "  ".join(f"{k}={v:.3f}" for k, v in metrics.items())
        print(f"  {split:11} {line}")
    print("\nTop features:")
    for feat, imp in out["importance"].head(8).items():
        print(f"  {feat:26} {imp:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
