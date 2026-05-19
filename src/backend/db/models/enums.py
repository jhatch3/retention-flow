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
    """Which tier of the two-tier eval framework produced a score."""

    distilbert = "distilbert"
    llm_judge = "llm_judge"
