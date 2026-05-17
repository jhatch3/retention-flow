"""Load the gold feature table and prepare it for the churn model.

The gold table (`analytics.customer_features`, built by dbt) is the single
feature source. This module does *not* compute features — it reads the table,
selects the explicit feature set, splits by the table's own `split` column,
and applies the small amount of model-specific preparation XGBoost needs.
"""

from __future__ import annotations

import pandas as pd

from ..db.session import engine

GOLD_TABLE = "analytics.customer_features"
TARGET = "churned"
SPLIT_COLUMN = "split"
SPLITS = ("train", "test", "validation")

# Categorical features (given the pandas `category` dtype for XGBoost).
CATEGORICAL = ["customer_state"]

# The explicit feature set the churn model trains on — the model's input
# contract. Every name is a column of the gold table. Keeping this list
# explicit (rather than "all columns except the keys") means new gold-table
# columns are never silently pulled into the model.
FEATURE_COLUMNS = [
    # geography
    "customer_state",
    # RFM
    "recency_days",
    "frequency",
    "monetary_total",
    "monetary_avg",
    # tenure / purchase cadence
    "tenure_days",
    "order_interval_mean",
    "order_interval_std",
    "order_interval_median",
    # satisfaction / experience
    "avg_review_score",
    "review_count",
    "avg_delivery_days",
    # order / basket shape
    "avg_items_per_order",
    "avg_freight_value",
    "avg_payment_types",
    "avg_installments",
    # shopping breadth
    "avg_sellers_per_order",
    "avg_categories_per_order",
]


def load_gold() -> pd.DataFrame:
    """Read the full gold table from Postgres."""
    return pd.read_sql(f"select * from {GOLD_TABLE}", engine)


def prepare_features(X: pd.DataFrame) -> pd.DataFrame:
    """Model-specific preparation — stateless, so it cannot leak across splits.

    XGBoost needs almost nothing: trees are scale-invariant and handle NULLs
    natively, so there is no scaling or imputation. The only steps are giving
    categorical columns the pandas ``category`` dtype (XGBoost's native
    categorical support then handles them) and casting numeric columns, which
    arrive from Postgres as ``Decimal``, to float.

    Because nothing here is *fitted*, applying it per split is leakage-free.
    """
    X = X.copy()
    for col in X.columns:
        if col in CATEGORICAL:
            X[col] = X[col].astype("category")
        else:
            X[col] = pd.to_numeric(X[col], errors="coerce")
    return X


def load_splits() -> tuple[dict[str, tuple[pd.DataFrame, pd.Series]], list[str]]:
    """Return ``{split: (X, y)}`` using the gold table's own ``split`` column.

    The split is assigned deterministically in dbt, so it is never recomputed
    here — train/test/validation come straight from the column.
    """
    df = load_gold()
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"gold table is missing feature columns: {missing}")

    splits: dict[str, tuple[pd.DataFrame, pd.Series]] = {}
    for split in SPLITS:
        subset = df[df[SPLIT_COLUMN] == split]
        X = prepare_features(subset[FEATURE_COLUMNS])
        y = subset[TARGET].astype(int)
        splits[split] = (X, y)
    return splits, list(FEATURE_COLUMNS)
