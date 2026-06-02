"""Canonical churn risk-tier classification.

One definition shared by the email generator (``ai.batch``), the LLM judge
(``ai.judge_batch``), and the dashboard services (``backend.api.*``) so the
cutoffs can't drift across modules.

Two label vocabularies over the *same* cutoffs:
- ``risk_tier`` returns the full labels the LLM payload/prompt expect
  (``critical`` / ``high`` / ``medium`` / ``low``).
- ``risk_tier_short`` returns the dashboard's compact codes
  (``crit`` / ``high`` / ``med`` / ``low``).
"""

from __future__ import annotations

# Upper cutoffs are fixed; the medium/low boundary is the model's per-prediction
# decision threshold, falling back to DEFAULT_MEDIUM_CUTOFF when unknown.
CRITICAL_CUTOFF = 0.85
HIGH_CUTOFF = 0.65
DEFAULT_MEDIUM_CUTOFF = 0.33

_SHORT = {"critical": "crit", "high": "high", "medium": "med", "low": "low"}


def risk_tier(churn_probability: float | None, threshold: float | None = None) -> str:
    """Classify a churn probability into ``critical``/``high``/``medium``/``low``.

    ``threshold`` is the prediction's decision threshold (the medium/low
    boundary); when ``None`` it falls back to ``DEFAULT_MEDIUM_CUTOFF`` (0.33).
    A ``None`` probability is treated as 0.0 (→ ``low``).
    """
    p = float(churn_probability or 0.0)
    medium_cutoff = DEFAULT_MEDIUM_CUTOFF if threshold is None else float(threshold)
    if p >= CRITICAL_CUTOFF:
        return "critical"
    if p >= HIGH_CUTOFF:
        return "high"
    if p >= medium_cutoff:
        return "medium"
    return "low"


def risk_tier_short(
    churn_probability: float | None, threshold: float | None = None
) -> str:
    """Dashboard short code (``crit``/``high``/``med``/``low``) for the tier."""
    return _SHORT[risk_tier(churn_probability, threshold)]
