"""Tests for backend.ml.data — feature selection and model-specific prep.

These exercise pure logic only: no Postgres connection is needed because
`load_gold` is monkeypatched and `prepare_features` is stateless.
"""

from decimal import Decimal

import pandas as pd
import pytest

from backend.ml import data
from backend.ml.data import CATEGORICAL, FEATURE_COLUMNS, prepare_features


def test_feature_columns_are_unique():
    """The model input contract must not list a column twice."""
    assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS))


def test_categorical_columns_are_part_of_the_feature_set():
    for col in CATEGORICAL:
        assert col in FEATURE_COLUMNS


def test_prepare_features_gives_categoricals_the_category_dtype():
    df = pd.DataFrame(
        {"customer_state": ["SP", "MG", "SP"], "recency_days": [1, 2, 3]}
    )
    out = prepare_features(df)
    assert out["customer_state"].dtype == "category"


def test_prepare_features_coerces_decimals_to_float():
    """Numeric columns arrive from Postgres as Decimal — they must become float."""
    df = pd.DataFrame({"monetary_total": [Decimal("10.5"), Decimal("20.0")]})
    out = prepare_features(df)
    assert out["monetary_total"].dtype.kind == "f"
    assert out["monetary_total"].tolist() == [10.5, 20.0]


def test_prepare_features_coerces_unparseable_values_to_nan():
    df = pd.DataFrame({"recency_days": ["12", "not-a-number"]})
    out = prepare_features(df)
    assert out["recency_days"].iloc[0] == 12
    assert pd.isna(out["recency_days"].iloc[1])


def test_prepare_features_does_not_mutate_its_input():
    """Statelessness claim: the input frame is left untouched."""
    df = pd.DataFrame({"customer_state": ["SP"], "recency_days": ["5"]})
    before = df.copy()
    prepare_features(df)
    pd.testing.assert_frame_equal(df, before)


def test_load_splits_raises_when_gold_table_misses_feature_columns(monkeypatch):
    fake_gold = pd.DataFrame({"churned": [0, 1], "split": ["train", "test"]})
    monkeypatch.setattr(data, "load_gold", lambda: fake_gold)
    with pytest.raises(ValueError, match="missing feature columns"):
        data.load_splits()


def test_load_splits_partitions_by_the_split_column(monkeypatch):
    """With a full gold table, each split yields its own rows and labels."""
    rows = {col: [0.0, 0.0, 0.0] for col in FEATURE_COLUMNS}
    rows["customer_state"] = ["SP", "MG", "RJ"]
    rows["churned"] = [1, 0, 1]
    rows["split"] = ["train", "test", "validation"]
    monkeypatch.setattr(data, "load_gold", lambda: pd.DataFrame(rows))

    splits, feature_cols = data.load_splits()

    assert feature_cols == FEATURE_COLUMNS
    assert set(splits) == {"train", "test", "validation"}
    X_train, y_train = splits["train"]
    assert len(X_train) == 1 and y_train.tolist() == [1]
    assert list(X_train.columns) == FEATURE_COLUMNS
