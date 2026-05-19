"""Per-feature SHAP contribution model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin

if TYPE_CHECKING:
    from .prediction import Prediction


class ShapValue(Base, TimestampMixin):
    """One feature's SHAP contribution to a single prediction.

    These rows are the structured explanation that flows into the LLM prompt:
    ``feature_name`` plus ``shap_value`` tells the email generator *which*
    risk factors drove the prediction and in which direction.
    """

    __tablename__ = "shap_values"
    __table_args__ = (
        UniqueConstraint("prediction_id", "feature_name"),
        {"schema": "serving"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("serving.predictions.id", ondelete="CASCADE"),
        index=True,
    )

    feature_name: Mapped[str] = mapped_column(String(128))
    # The customer's actual value for this feature at prediction time.
    feature_value: Mapped[float | None] = mapped_column(Float)
    # Signed contribution: positive pushes toward churn, negative away from it.
    shap_value: Mapped[float] = mapped_column(Float)
    # Contribution rank by absolute magnitude (1 = most influential).
    rank: Mapped[int | None] = mapped_column(Integer)

    prediction: Mapped["Prediction"] = relationship(back_populates="shap_values")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<ShapValue prediction_id={self.prediction_id} "
            f"feature={self.feature_name!r} shap={self.shap_value:+.4f}>"
        )
