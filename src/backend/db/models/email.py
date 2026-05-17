"""Generated retention email model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin
from .enums import EmailStatus

if TYPE_CHECKING:
    from .eval_score import EvalScore
    from .prediction import Prediction


class GeneratedEmail(Base, TimestampMixin):
    """An LLM-generated retention email grounded in a prediction's SHAP output.

    Token counts and ``cost_usd`` form the audit trail for the cost-tracking
    metrics; ``cached_tokens`` captures prompt-caching savings on the system
    prompt.
    """

    __tablename__ = "generated_emails"
    __table_args__ = {"schema": "serving"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("serving.predictions.id", ondelete="CASCADE"),
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64))
    status: Mapped[EmailStatus] = mapped_column(
        SAEnum(EmailStatus, name="email_status", schema="serving"),
        default=EmailStatus.draft,
        server_default=EmailStatus.draft.value,
        index=True,
    )

    # --- Cost / usage audit trail ----------------------------------------
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cached_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    latency_ms: Mapped[float | None] = mapped_column(Float)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    prediction: Mapped["Prediction"] = relationship(back_populates="emails")
    eval_scores: Mapped[list["EvalScore"]] = relationship(
        back_populates="email",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<GeneratedEmail id={self.id} "
            f"prediction_id={self.prediction_id} status={self.status.value}>"
        )
