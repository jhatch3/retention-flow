"""Tests for backend.api.inbox — the Triage Inbox queue + detail services.

inbox.py is now backed by the live warehouse (serving.predictions + analytics),
not static fixtures, so these are integration tests: they read real IDs from
the queue and assert the projection shape, tier bucketing, totals, filtering,
and the per-customer detail / eval contract. They skip cleanly when the DB has
no scored customers yet.
"""

import pytest

from ai.judge_batch import PASS_THRESHOLD
from backend.api import inbox


def _queue(**kw):
    """The live queue, or skip if nothing has been scored."""
    customers = inbox.inbox_customers(**kw)["customers"]
    if not customers:
        pytest.skip("no scored customers in the warehouse")
    return customers

_SUMMARY_KEYS = {
    "customer_unique_id", "display_name", "city", "ltv_brl", "risk", "tier",
    "recency_days", "reviews_avg", "delivery_avg_days", "orders_lifetime",
    "joined_human", "last_order_label", "top_driver", "status", "email_sent_at",
}
_DETAIL_KEYS = {
    "summary", "drivers", "history", "email", "eval", "plays",
    "cohort_label", "cohort_save_rate_pct", "cohort_n",
}


# --- tier bucketing ------------------------------------------------------

def test_tier_buckets_by_risk():
    # _tier(risk, threshold) is the pure projection of the canonical risk-tier
    # cutoffs into the dashboard's short codes (no DB needed).
    assert inbox._tier(0.92, 0.33) == "crit"
    assert inbox._tier(0.85, 0.33) == "crit"
    assert inbox._tier(0.70, 0.33) == "high"
    assert inbox._tier(0.50, 0.33) == "med"
    assert inbox._tier(0.33, 0.33) == "med"
    assert inbox._tier(0.10, 0.33) == "low"


# --- queue ---------------------------------------------------------------

def test_inbox_customers_envelope():
    _queue()  # skip if unscored
    out = inbox.inbox_customers()
    assert set(out) == {
        "customers", "totals", "scored_at", "model_version", "threshold"
    }
    assert isinstance(out["threshold"], float)
    assert isinstance(out["model_version"], str)


def test_queue_is_sorted_by_risk_descending():
    customers = inbox.inbox_customers()["customers"]
    risks = [c["risk"] for c in customers]
    assert risks == sorted(risks, reverse=True)


def test_every_summary_has_the_full_field_set():
    for c in inbox.inbox_customers()["customers"]:
        assert set(c) == _SUMMARY_KEYS
        assert c["tier"] in {"crit", "high", "med", "low"}
        assert isinstance(c["top_driver"], str) and c["top_driver"]


def test_totals_are_internally_consistent():
    totals = inbox.inbox_customers()["totals"]
    assert totals["all"] == totals["crit"] + totals["high"] + totals["med"] + totals["low"]
    assert totals["revenue_at_risk_brl"] > 0


def test_filter_crit_returns_only_critical():
    customers = inbox.inbox_customers(risk_filter="crit")["customers"]
    assert customers
    assert all(c["tier"] == "crit" for c in customers)


def test_filter_high_means_high_or_worse():
    customers = inbox.inbox_customers(risk_filter="high")["customers"]
    assert customers
    assert all(c["tier"] in {"crit", "high"} for c in customers)


def test_filter_does_not_change_totals():
    """Totals are queue-wide — they must not shrink when a filter is applied."""
    full = inbox.inbox_customers()["totals"]
    filtered = inbox.inbox_customers(risk_filter="crit")["totals"]
    assert filtered == full


# --- detail --------------------------------------------------------------

def test_inbox_customer_returns_full_detail():
    queue = inbox.inbox_customers()["customers"]
    detail = inbox.inbox_customer(queue[0]["customer_unique_id"])
    assert detail is not None
    assert set(detail) == _DETAIL_KEYS
    assert set(detail["summary"]) == _SUMMARY_KEYS
    assert len(detail["drivers"]) <= 6


def test_detail_drivers_sorted_by_absolute_contribution():
    cid = _queue()[0]["customer_unique_id"]
    detail = inbox.inbox_customer(cid)
    assert detail is not None
    mags = [abs(d["contrib"]) for d in detail["drivers"]]
    assert mags == sorted(mags, reverse=True)


def test_eval_pass_is_derived_from_judge_score():
    # Contract: the bar is the canonical PASS_THRESHOLD (7.0 on the 1-10 scale),
    # and ``passed`` is true iff judge_score >= that bar.
    graded = 0
    for c in _queue(limit=25):
        ev = inbox.inbox_customer(c["customer_unique_id"])["eval"]
        assert ev["pass_threshold"] == PASS_THRESHOLD
        if ev["judge_score"] > 0:  # a real grade, not the empty default
            graded += 1
            assert ev["passed"] == (ev["judge_score"] >= PASS_THRESHOLD)
    if graded == 0:
        pytest.skip("no graded emails among the sampled customers")


def test_inbox_customer_unknown_id_returns_none():
    assert inbox.inbox_customer("does-not-exist") is None
