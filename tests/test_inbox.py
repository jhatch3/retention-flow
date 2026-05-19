"""Tests for backend.api.inbox — the Triage Inbox queue + detail services.

These cover the v1 fixture-backed contract (HANDOFF-triage-inbox.md §4): the
queue projection, tier bucketing, totals, filtering, and per-customer detail.
No database or model is needed — inbox.py reads static fixtures.
"""

from backend.api import inbox

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
    assert inbox.tier(0.92) == "crit"
    assert inbox.tier(0.85) == "crit"
    assert inbox.tier(0.70) == "high"
    assert inbox.tier(0.50) == "med"
    assert inbox.tier(inbox.THRESHOLD) == "med"
    assert inbox.tier(0.10) == "low"


# --- queue ---------------------------------------------------------------

def test_inbox_customers_envelope():
    out = inbox.inbox_customers()
    assert set(out) == {
        "customers", "totals", "scored_at", "model_version", "threshold"
    }
    assert out["threshold"] == inbox.THRESHOLD
    assert out["model_version"] == inbox.MODEL_VERSION


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
    detail = inbox.inbox_customer("a1b2c3d4e5f6a7b8")
    assert detail is not None
    mags = [abs(d["contrib"]) for d in detail["drivers"]]
    assert mags == sorted(mags, reverse=True)


def test_eval_pass_is_derived_from_both_tiers():
    # Camila: distilbert 4.6 + judge 4.5, threshold 4.0 -> passes.
    passing = inbox.inbox_customer("a1b2c3d4e5f6a7b8")["eval"]
    assert passing["passed"] is True
    assert passing["agreement_delta"] == 0.1
    # Thiago: judge 3.6 is below the 4.0 bar -> fails.
    failing = inbox.inbox_customer("f6a7b8c9d0e1f2a3")["eval"]
    assert failing["passed"] is False


def test_inbox_customer_unknown_id_returns_none():
    assert inbox.inbox_customer("does-not-exist") is None
