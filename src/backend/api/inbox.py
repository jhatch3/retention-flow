"""Triage Inbox API services — the at-risk customer queue + per-customer detail.

v1 serves mock data from ``inbox_fixtures.py``. The real wiring — gold-table
sourcing, LLM-drafted emails, live DistilBERT/judge eval — lands in v1.1; see
HANDOFF-triage-inbox.md §4.

The fixture records carry the full detail; this module projects the queue
summary, computes the risk tier, derives the eval pass/fail, and tallies the
tier totals, so none of that is duplicated in the fixtures.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .inbox_fixtures import INBOX_CUSTOMERS

# Decision threshold and model stamp shown in the queue header.
THRESHOLD = 0.33
MODEL_VERSION = "churn-xgboost v6"

# Raw SHAP feature name -> human-readable driver label (handoff §4.3).
DRIVER_LABELS = {
    "avg_review_score": "Review collapse",
    "avg_delivery_days": "Slow delivery streak",
    "recency_days": "Long inactivity",
    "order_count_lifetime": "Declining frequency",
    "avg_freight_cost": "Shipping cost creep",
    "category_diversity": "Single-category buyer",
}


def tier(risk: float, threshold: float = THRESHOLD) -> str:
    """Bucket a churn probability into a risk tier."""
    if risk >= 0.85:
        return "crit"
    if risk >= 0.65:
        return "high"
    if risk >= threshold:
        return "med"
    return "low"


def _top_driver_label(drivers: list[dict]) -> str:
    """Human label for the rank-1 (largest positive contribution) driver."""
    ranked = sorted(drivers, key=lambda d: d["contrib"], reverse=True)
    top = ranked[0]["feature"] if ranked else ""
    return DRIVER_LABELS.get(top, top.replace("_", " ").capitalize())


def _summary(c: dict) -> dict:
    """Project a fixture record to an ``InboxCustomerSummary``."""
    return {
        "customer_unique_id": c["customer_unique_id"],
        "display_name": c["display_name"],
        "city": c["city"],
        "ltv_brl": c["ltv_brl"],
        "risk": c["risk"],
        "tier": tier(c["risk"]),
        "recency_days": c["recency_days"],
        "reviews_avg": c["reviews_avg"],
        "delivery_avg_days": c["delivery_avg_days"],
        "orders_lifetime": c["orders_lifetime"],
        "joined_human": c["joined_human"],
        "last_order_label": c["last_order_label"],
        "top_driver": _top_driver_label(c["drivers"]),
        "status": c["status"],
        "email_sent_at": c.get("email_sent_at"),
    }


def inbox_customers(risk_filter: str = "all", limit: int = 100, offset: int = 0) -> dict:
    """The at-risk queue — summaries sorted by risk DESC, with tier totals.

    ``risk_filter`` is ``all`` | ``crit`` | ``high`` | ``med``; ``high`` means
    "high OR critical" (the queue filter behaves as "high or worse").
    """
    ranked = sorted(INBOX_CUSTOMERS, key=lambda c: c["risk"], reverse=True)
    summaries = [_summary(c) for c in ranked]

    totals = {
        "all": len(summaries),
        "crit": sum(s["tier"] == "crit" for s in summaries),
        "high": sum(s["tier"] == "high" for s in summaries),
        "med": sum(s["tier"] == "med" for s in summaries),
        "low": sum(s["tier"] == "low" for s in summaries),
        "revenue_at_risk_brl": sum(
            s["ltv_brl"] for s in summaries if s["tier"] in ("crit", "high", "med")
        ),
    }

    keep = {
        "crit": ("crit",),
        "high": ("crit", "high"),
        "med": ("med",),
    }.get(risk_filter)
    if keep is not None:
        summaries = [s for s in summaries if s["tier"] in keep]

    scored_at = (datetime.now(timezone.utc) - timedelta(minutes=14)).isoformat()
    return {
        "customers": summaries[offset : offset + limit],
        "totals": totals,
        "scored_at": scored_at,
        "model_version": MODEL_VERSION,
        "threshold": THRESHOLD,
    }


def inbox_customer(customer_id: str) -> dict | None:
    """Full centre + right-pane detail for one customer, or ``None`` if unknown."""
    c = next(
        (x for x in INBOX_CUSTOMERS if x["customer_unique_id"] == customer_id), None
    )
    if c is None:
        return None

    # Top 6 drivers by absolute contribution (the fixtures already rank them,
    # but sorting here keeps the contract robust).
    drivers = sorted(c["drivers"], key=lambda d: abs(d["contrib"]), reverse=True)[:6]

    ev = c["eval"]
    eval_block = {
        **ev,
        "passed": (
            ev["distilbert_score"] >= ev["pass_threshold"]
            and ev["judge_score"] >= ev["pass_threshold"]
        ),
        "agreement_delta": round(
            abs(ev["distilbert_score"] - ev["judge_score"]), 2
        ),
    }

    return {
        "summary": _summary(c),
        "drivers": drivers,
        "history": c["history"],
        "email": c["email"],
        "eval": eval_block,
        "plays": c["plays"],
        "cohort_label": c["cohort_label"],
        "cohort_save_rate_pct": c["cohort_save_rate_pct"],
        "cohort_n": c["cohort_n"],
    }
