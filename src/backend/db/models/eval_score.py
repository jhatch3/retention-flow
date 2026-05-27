"""Email evaluation score model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin
from .enums import Evaluator

if TYPE_CHECKING:
    from .email import GeneratedEmail


class EvalScore(Base, TimestampMixin):
    """A quality score for a generated email from the LLM-as-judge evaluator.

    Each email is graded once on the 1-5 ``overall_score`` scale, with a
    ``passed`` gate on the same scale. ``judge_model`` records which model
    produced the score.
    """

    __tablename__ = "eval_scores"
    __table_args__ = (
        UniqueConstraint("email_id", "evaluator"),
        {"schema": "serving"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_id: Mapped[int] = mapped_column(
        ForeignKey("serving.generated_emails.id", ondelete="CASCADE"),
        index=True,
    )

    evaluator: Mapped[Evaluator] = mapped_column(
        SAEnum(Evaluator, name="evaluator", schema="serving")
    )

    # Overall email-quality grade (1-5) and the inline pass/fail gate.
    overall_score: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)

    # The Claude model id that produced the score.
    judge_model: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[float | None] = mapped_column(Float)

    email: Mapped["GeneratedEmail"] = relationship(back_populates="eval_scores")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<EvalScore email_id={self.email_id} "
            f"evaluator={self.evaluator.value} "
            f"overall={self.overall_score:.2f} passed={self.passed}>"
        )
