"""ORM models for the RetentionFlow data layer.

Importing this package registers every model on ``Base.metadata``, which is
what Alembic's ``env.py`` relies on. Only the ``serving`` schema is modelled
here — the gold table is owned by dbt.
"""

from __future__ import annotations

from ..base import Base
from .email import GeneratedEmail
from .enums import EmailStatus, Evaluator
from .eval_score import EvalScore
from .prediction import Prediction
from .shap_value import ShapValue

__all__ = [
    "Base",
    "Prediction",
    "ShapValue",
    "GeneratedEmail",
    "EvalScore",
    "EmailStatus",
    "Evaluator",
]
