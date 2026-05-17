"""Churn prediction model."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin

if TYPE_CHECKING:
    from .email import GeneratedEmail
    from .shap_value import ShapValue


class Prediction(Base, TimestampMixin):
    """A single churn-probability prediction produced by the ML service.

    It references its feature snapshot in the dbt-managed gold table
    (`analytics.customer_features`) by **natural key** — `customer_unique_id`
    plus `snapshot_date` — not a foreign key, because dbt drops and recreates
    the gold table on every run.

    ``base_value`` is the SHAP explainer's expected value; the per-feature
    contributions that sum from it to ``churn_probability`` live in
    :class:`ShapValue`.
    """

    __tablename__ = "predictions"
    __table_args__ = (
        Index(
            "ix_predictions_customer_snapshot",
            "customer_unique_id",
            "snapshot_date",
        ),
        {"schema": "serving"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Natural-key reference to the gold table (no FK — dbt rebuilds it).
    customer_unique_id: Mapped[str] = mapped_column(String(64))
    snapshot_date: Mapped[date] = mapped_column(Date)

    model_version: Mapped[str] = mapped_column(String(64), index=True)
    churn_probability: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float, default=0.5, server_default="0.5")
    predicted_label: Mapped[bool] = mapped_column(Boolean)

    # SHAP explainer expected value (base value for this prediction).
    base_value: Mapped[float | None] = mapped_column(Float)

    inference_latency_ms: Mapped[float | None] = mapped_column(Float)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    shap_values: Mapped[list["ShapValue"]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
    )
    emails: Mapped[list["GeneratedEmail"]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Prediction id={self.id} "
            f"customer={self.customer_unique_id!r} "
            f"p={self.churn_probability:.3f} label={self.predicted_label}>"
        )
