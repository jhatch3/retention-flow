"""Score a generated retention email inline.

Loads the fine-tuned DistilBERT champion and grades an email's overall
quality (1-5). Tier 1 of the eval stack — fast and local — and the result
becomes a ``distilbert`` row in ``serving.eval_scores``. ``passed`` is the
inline quality gate: ``overall_score >= PASS_THRESHOLD``.

The champion pipeline is loaded once and cached for the process lifetime.
"""

from __future__ import annotations

import time

from .model import load_champion

# An email graded at or above this clears the inline quality bar.
PASS_THRESHOLD = 3

_pipeline = None


def _get_pipeline():
    """Lazily load and cache the champion text-classification pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = load_champion()
    return _pipeline


def score_email(email: str) -> dict:
    """Grade one email's overall quality.

    Returns ``{"overall_score": int, "passed": bool, "latency_ms": float}`` —
    the fields written to a ``distilbert`` row in ``serving.eval_scores``.
    """
    pipe = _get_pipeline()

    t0 = time.perf_counter()
    result = pipe(email, truncation=True)[0]
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # build_model() sets id2label so the pipeline label is the grade string.
    grade = int(result["label"])
    return {
        "overall_score": grade,
        "passed": grade >= PASS_THRESHOLD,
        "latency_ms": round(latency_ms, 2),
    }
