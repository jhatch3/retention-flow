"""Tests for backend.ml.train — model construction, threshold tuning, metrics.

`tune_threshold` and `evaluate` only call ``model.predict_proba``, so a tiny
stub model stands in for a fitted XGBoost classifier and keeps the tests fast
and deterministic.
"""

import numpy as np
import pandas as pd
import pytest

from backend.ml.train import build_model, evaluate, tune_threshold


class StubModel:
    """Minimal stand-in: returns fixed churn probabilities, ignores X."""

    def __init__(self, churn_proba):
        self._proba = np.asarray(churn_proba, dtype=float)

    def predict_proba(self, X):  # noqa: ARG002 - X is intentionally ignored
        return np.column_stack([1.0 - self._proba, self._proba])


# --- build_model ----------------------------------------------------------

def test_build_model_sets_scale_pos_weight_from_class_balance():
    y = pd.Series([1, 1, 1, 0])  # 3 positives, 1 negative
    model = build_model(y)
    assert model.scale_pos_weight == pytest.approx(1 / 3)


def test_build_model_handles_a_split_with_no_positives():
    model = build_model(pd.Series([0, 0, 0]))
    assert model.scale_pos_weight == 1.0


def test_build_model_applies_the_fixed_hyperparameters():
    model = build_model(pd.Series([0, 1]))
    assert model.max_depth == 5
    assert model.n_estimators == 300
    assert model.enable_categorical is True


# --- tune_threshold -------------------------------------------------------

def test_tune_threshold_picks_a_high_precision_cutoff():
    """With perfectly separable scores, the cutoff catches every churner
    and admits no false positives."""
    y = pd.Series([0, 0, 1, 1, 1])
    proba = [0.1, 0.2, 0.7, 0.8, 0.9]
    threshold = tune_threshold(StubModel(proba), X=None, y=y, target_recall=0.85)

    predictions = (np.array(proba) >= threshold).astype(int)
    assert predictions.tolist() == [0, 0, 1, 1, 1]


def test_tune_threshold_falls_back_when_the_recall_target_is_unreachable():
    """A target above 1.0 can never be met — the guard returns the lowest
    candidate threshold rather than raising."""
    y = pd.Series([0, 1, 1])
    threshold = tune_threshold(
        StubModel([0.2, 0.6, 0.8]), X=None, y=y, target_recall=1.5
    )
    assert threshold == pytest.approx(0.2)


# --- evaluate -------------------------------------------------------------

def test_evaluate_returns_every_metric_as_a_float():
    y = pd.Series([0, 1, 0, 1])
    metrics = evaluate(StubModel([0.3, 0.6, 0.4, 0.7]), None, y)
    assert set(metrics) == {"roc_auc", "pr_auc", "precision", "recall", "f1", "brier"}
    assert all(isinstance(v, float) for v in metrics.values())


def test_evaluate_scores_a_perfect_model_perfectly():
    y = pd.Series([0, 0, 1, 1])
    metrics = evaluate(StubModel([0.05, 0.1, 0.9, 0.95]), None, y, threshold=0.5)
    assert metrics["roc_auc"] == 1.0
    assert metrics["pr_auc"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["brier"] < 0.02


def test_evaluate_recall_falls_as_the_threshold_rises():
    y = pd.Series([0, 0, 1, 1])
    model = StubModel([0.2, 0.45, 0.55, 0.9])
    lenient = evaluate(model, None, y, threshold=0.3)
    strict = evaluate(model, None, y, threshold=0.8)
    assert lenient["recall"] >= strict["recall"]
