"""RetentionFlow database package: ORM models, engine, and session helpers."""

from __future__ import annotations

from .base import Base, TimestampMixin
from .config import DatabaseSettings, get_settings
from .models import (
    EmailStatus,
    Evaluator,
    EvalScore,
    GeneratedEmail,
    Prediction,
    ShapValue,
)
from .session import SessionLocal, engine, get_db, session_scope

__all__ = [
    "Base",
    "TimestampMixin",
    "DatabaseSettings",
    "get_settings",
    "engine",
    "SessionLocal",
    "get_db",
    "session_scope",
    "Prediction",
    "ShapValue",
    "GeneratedEmail",
    "EvalScore",
    "EmailStatus",
    "Evaluator",
]
