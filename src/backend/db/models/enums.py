"""Enumerations shared across the ORM models."""

from __future__ import annotations

import enum


class EmailStatus(str, enum.Enum):
    """Lifecycle state of a generated retention email."""

    draft = "draft"
    approved = "approved"
    sent = "sent"
    rejected = "rejected"


class Evaluator(str, enum.Enum):
    """Which evaluator produced an email-quality score."""

    llm_judge = "llm_judge"
