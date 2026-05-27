"""One-shot script: pick real customers across all risk tiers, compute SHAP
locally for each, and emit a Python module body for test_dataset.py.

Run with:  python -m src.ai.test.build_real_test_cases

The output is printed to stdout so you can pipe / paste it into
src/ai/prompts/test_dataset.py once you're happy with the picks.
"""

from __future__ import annotations

import json

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from mlflow.tracking import MlflowClient

from src.backend.ml.data import FEATURE_COLUMNS, load_gold, prepare_features
from src.backend.ml.train import CHAMPION_ALIAS, MLFLOW_URI, REGISTERED_MODEL


def _risk_tier(prob: float) -> str:
    if prob < 0.35:
        return "low"
    if prob < 0.65:
        return "medium"
    if prob < 0.90:
        return "high"
    return "critical"


def _top_shap_factors(
    shap_row: np.ndarray,
    feature_row: pd.Series,
    feature_names: list[str],
    k: int = 5,
) -> list[dict]:
    """Top-k absolute-magnitude SHAP factors as (feature_name, feature_value, shap_value)."""
    order = np.argsort(-np.abs(shap_row))[:k]
    out = []
    for i in order:
        raw = feature_row.iloc[int(i)]
        value = pd.to_numeric(pd.Series([raw]), errors="coerce").iat[0]
        out.append({
            "feature_name": feature_names[int(i)],
            "feature_value": None if pd.isna(value) else round(float(value), 2),
            "shap_value": round(float(shap_row[int(i)]), 3),
        })
    return out


def _pick_one(
    gold: pd.DataFrame,
    proba: np.ndarray,
    *,
    prob_lo: float,
    prob_hi: float,
    must_have_positive: list[str] | None = None,
    frequency_min: int | None = None,
    frequency_max: int | None = None,
    tenure_max: int | None = None,
    shap_full: np.ndarray,
    feature_names: list[str],
    exclude_ids: set[str],
) -> int | None:
    """Find a row index whose proba is in [lo, hi] and matches optional filters.
    Returns None if no candidate found."""
    mask = (proba >= prob_lo) & (proba < prob_hi)
    if frequency_min is not None:
        mask &= gold["frequency"] >= frequency_min
    if frequency_max is not None:
        mask &= gold["frequency"] <= frequency_max
    if tenure_max is not None:
        mask &= gold["tenure_days"] <= tenure_max
    if must_have_positive:
        for feat in must_have_positive:
            col_idx = feature_names.index(feat)
            mask &= shap_full[:, col_idx] > 0
    if exclude_ids:
        mask &= ~gold["customer_unique_id"].isin(exclude_ids)

    idxs = np.where(mask)[0]
    if len(idxs) == 0:
        return None
    # Prefer the candidate closest to the middle of the probability range — keeps
    # us away from boundary cases where the risk tier feels borderline.
    target_prob = (prob_lo + prob_hi) / 2
    return int(idxs[np.argmin(np.abs(proba[idxs] - target_prob))])


def main() -> None:
    print("# Loading model + gold data...", flush=True)
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()
    version = client.get_model_version_by_alias(REGISTERED_MODEL, CHAMPION_ALIAS)
    model = mlflow.xgboost.load_model(f"models:/{REGISTERED_MODEL}@{CHAMPION_ALIAS}")
    model_version = f"{REGISTERED_MODEL}:v{version.version}"

    gold = load_gold()
    X = prepare_features(gold[FEATURE_COLUMNS])
    proba = model.predict_proba(X)[:, 1]

    print(f"# Loaded {len(gold):,} customers, computing SHAP...", flush=True)
    contribs = model.get_booster().predict(
        xgb.DMatrix(X, enable_categorical=True), pred_contribs=True
    )
    shap_full = contribs[:, :-1]
    base_value = float(contribs[0, -1])
    print(f"# Done — base_value = {base_value:.3f}", flush=True)

    # Pick one customer per profile.
    profiles = [
        {
            "name": "service_failure_critical",
            "filters": {"prob_lo": 0.95, "prob_hi": 1.0,
                        "must_have_positive": ["avg_review_score", "avg_delivery_days"]},
        },
        {
            "name": "price_sensitive_high",
            "filters": {"prob_lo": 0.75, "prob_hi": 0.90,
                        "must_have_positive": ["recency_days"]},
        },
        {
            "name": "ambiguous_medium",
            "filters": {"prob_lo": 0.45, "prob_hi": 0.60},
        },
        {
            "name": "low_risk_soft_engagement",
            "filters": {"prob_lo": 0.15, "prob_hi": 0.30, "frequency_max": 1},
        },
        {
            "name": "loyal_with_delivery_issue_high",
            "filters": {"prob_lo": 0.70, "prob_hi": 0.90,
                        "frequency_min": 3,
                        "must_have_positive": ["avg_delivery_days"]},
        },
        {
            "name": "weak_signal_new_customer_medium",
            "filters": {"prob_lo": 0.40, "prob_hi": 0.55,
                        "frequency_max": 1, "tenure_max": 60},
        },
    ]

    picks: list[dict] = []
    used_ids: set[str] = set()

    for profile in profiles:
        idx = _pick_one(
            gold, proba,
            shap_full=shap_full, feature_names=list(FEATURE_COLUMNS),
            exclude_ids=used_ids,
            **profile["filters"],
        )
        if idx is None:
            print(f"# WARNING: no candidate for {profile['name']} with filters {profile['filters']}")
            continue

        row = gold.iloc[idx]
        used_ids.add(row["customer_unique_id"])
        prob = float(proba[idx])
        tier = _risk_tier(prob)
        top_shaps = _top_shap_factors(
            shap_full[idx], X.iloc[idx], list(FEATURE_COLUMNS), k=5
        )

        # The gold table doesn't carry the customer's first name; we don't have
        # a per-customer name in the Olist dataset at all. Leave first_name out
        # of customer_context so the email generator falls back to a generic
        # greeting (and we don't fabricate).
        pick = {
            "name": profile["name"],
            "customer_unique_id": row["customer_unique_id"],
            "churn_probability": round(prob, 4),
            "risk_tier": tier,
            "shap_factors": top_shaps,
            "customer_context": {
                "order_count": int(row["frequency"]) if pd.notna(row["frequency"]) else None,
                "tenure_days": int(row["tenure_days"]) if pd.notna(row["tenure_days"]) else None,
                "monetary_total": round(float(row["monetary_total"]), 2) if pd.notna(row["monetary_total"]) else None,
                "monetary_avg": round(float(row["monetary_avg"]), 2) if pd.notna(row["monetary_avg"]) else None,
                "avg_review_score": round(float(row["avg_review_score"]), 2) if pd.notna(row["avg_review_score"]) else None,
                "avg_delivery_days": round(float(row["avg_delivery_days"]), 2) if pd.notna(row["avg_delivery_days"]) else None,
                "customer_state": str(row["customer_state"]) if pd.notna(row["customer_state"]) else None,
            },
        }
        picks.append(pick)

    print()
    print(f"# Picked {len(picks)} customers — model_version={model_version}")
    print(f"# base_value = {base_value:.4f}")
    print()
    print("PICKS = ")
    print(json.dumps(picks, indent=2, default=str))


if __name__ == "__main__":
    main()
