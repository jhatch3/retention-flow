"""Triage Inbox API services — at-risk customer queue + per-customer detail.

Backed by real warehouse data:

  Queue + summary
    - ``serving.predictions``          (churn probability, threshold, snapshot)
    - ``analytics.customer_features``  (gold features per snapshot)
    - ``analytics.stg_customers``      (city / state)
    - ``analytics.int_customer_orders``(most recent order)

  Per-customer detail
    - ``serving.shap_values``          (top SHAP drivers — top-200 only)
    - ``serving.generated_emails``     (latest LLM draft, if any)
    - ``serving.eval_scores``          (judge grade for that draft, if any)

  Plays / cohort
    - No production source yet — a small heuristic mapping derives a "suggested
      play" and a placeholder cohort label from the dominant SHAP driver. When
      the playbook table lands these will source from there.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import text

from ..db.session import engine

# Queue is bounded by SHAP coverage — SHAP is only persisted for the top-200
# at-risk customers in this snapshot, so the queue can show at most that many.
MAX_QUEUE = 200

# Raw SHAP feature name -> human-readable driver label (handoff §4.3).
DRIVER_LABELS = {
    "avg_review_score": "Review collapse",
    "avg_delivery_days": "Slow delivery streak",
    "recency_days": "Long inactivity",
    "frequency": "Declining frequency",
    "monetary_total": "Spend slowdown",
    "monetary_avg": "Small-ticket shift",
    "avg_freight_value": "Shipping cost creep",
    "avg_categories_per_order": "Single-category buyer",
    "avg_items_per_order": "Smaller baskets",
    "avg_installments": "Payment behaviour shift",
    "tenure_days": "New account",
    "customer_state": "Regional pattern",
    "order_interval_mean": "Order-cadence drift",
    "order_interval_median": "Order-cadence drift",
}

# Why-line for each driver — appears in the right-rail per-driver card.
DRIVER_WHY = {
    "avg_review_score": "Recent reviews fell well below the cohort median.",
    "avg_delivery_days": "Deliveries are running longer than this customer's baseline.",
    "recency_days": "No order in a long time — past their usual cadence.",
    "frequency": "Order frequency has slowed materially.",
    "monetary_total": "Lifetime spend is below the at-risk cohort baseline.",
    "monetary_avg": "Average order value has been drifting down.",
    "avg_freight_value": "Freight cost has crept up over recent orders.",
    "avg_categories_per_order": "Shopping in a single category — easy to churn out of.",
    "avg_items_per_order": "Basket size has been shrinking.",
    "avg_installments": "Payment-installment pattern looks different.",
    "tenure_days": "New account — no loyalty buffer yet.",
    "customer_state": "Regional pattern flagged the model.",
    "order_interval_mean": "Gap between orders is widening.",
    "order_interval_median": "Gap between orders is widening.",
}

# Suggested-play heuristics, keyed by the rank-1 (largest positive) SHAP driver.
PLAY_BY_DRIVER: dict[str, list[dict]] = {
    "avg_review_score": [
        {"id": "apology-credit", "name": "Apology + R$ 40 credit",
         "save_rate_pct": 31, "sample_n": 240},
        {"id": "personal-checkin", "name": "Personal check-in call",
         "save_rate_pct": 19, "sample_n": 95},
    ],
    "avg_delivery_days": [
        {"id": "express-freight-waiver", "name": "Express network + freight waiver",
         "save_rate_pct": 28, "sample_n": 165},
        {"id": "priority-shipping", "name": "Free priority shipping, next order",
         "save_rate_pct": 24, "sample_n": 180},
    ],
    "recency_days": [
        {"id": "reengage-discount", "name": "15% win-back discount",
         "save_rate_pct": 22, "sample_n": 310},
        {"id": "restock-alert", "name": "Favourite-brand restock alert",
         "save_rate_pct": 18, "sample_n": 205},
    ],
    "frequency": [
        {"id": "loyalty-thanks", "name": "Loyalty thank-you + free shipping",
         "save_rate_pct": 26, "sample_n": 198},
        {"id": "reengage-discount", "name": "15% win-back discount",
         "save_rate_pct": 21, "sample_n": 310},
    ],
    "monetary_total": [
        {"id": "bundle-offer", "name": "Bundle discount", "save_rate_pct": 14,
         "sample_n": 160},
        {"id": "loyalty-thanks", "name": "Loyalty thank-you + free shipping",
         "save_rate_pct": 26, "sample_n": 198},
    ],
    "avg_freight_value": [
        {"id": "free-shipping", "name": "Free shipping, next order",
         "save_rate_pct": 20, "sample_n": 275},
        {"id": "bundle-offer", "name": "Bundle discount", "save_rate_pct": 14,
         "sample_n": 160},
    ],
    "avg_categories_per_order": [
        {"id": "cross-category", "name": "Cross-category discovery + 10% off",
         "save_rate_pct": 16, "sample_n": 420},
    ],
}

DEFAULT_PLAYS = [
    {"id": "reengage-discount", "name": "15% win-back discount",
     "save_rate_pct": 21, "sample_n": 310},
    {"id": "personal-checkin", "name": "Personal check-in call",
     "save_rate_pct": 15, "sample_n": 95},
]


def _tier(risk: float, threshold: float) -> str:
    if risk >= 0.85:
        return "crit"
    if risk >= 0.65:
        return "high"
    if risk >= threshold:
        return "med"
    return "low"


def _display_name(customer_unique_id: str, name_from_db: str | None = None) -> str:
    """A stable, non-PII handle for the customer in the UI.

    Olist's anonymised customer ids are 32-char hex hashes — no real name
    exists. ``serving.customer_display_names`` holds a deterministic synthetic
    label per customer; we prefer that. If a row is missing (fresh insert,
    seed not yet run), fall back to the leading 8 hex chars so the customer
    is still recognisable.
    """
    if name_from_db:
        return name_from_db
    return f"Customer {customer_unique_id[:8].upper()}"


def _humanize_city(city: str | None, state: str | None) -> str:
    if not city:
        return state or ""
    pretty = " ".join(w.capitalize() for w in city.split())
    return f"{pretty}, {state}" if state else pretty


def _months_since(d: datetime | None, anchor: datetime) -> str:
    if d is None:
        return ""
    months = (anchor.year - d.year) * 12 + (anchor.month - d.month)
    if months < 1:
        return "this mo"
    if months < 12:
        return f"{months} mo"
    years = months // 12
    return f"{years} yr"


def _last_order_label(payment_value, item_count, freight_value) -> str:
    if payment_value is None:
        return "—"
    val = f"R$ {float(payment_value):.0f}"
    if item_count is not None and int(item_count) > 1:
        return f"{int(item_count)} items · {val}"
    return val


def _top_driver_label(feature_name: str | None) -> str:
    if not feature_name:
        return ""
    return DRIVER_LABELS.get(feature_name, feature_name.replace("_", " ").capitalize())


def _format_value(feature_name: str, value: float | None) -> str:
    if value is None:
        return "—"
    if feature_name == "avg_review_score":
        return f"{value:.1f}"
    if feature_name == "avg_delivery_days":
        return f"{value:.1f}d"
    if feature_name == "recency_days" or feature_name == "tenure_days":
        return f"{int(round(value))}d"
    if feature_name == "frequency" or feature_name == "avg_items_per_order":
        return f"{value:.0f}" if value == int(value) else f"{value:.1f}"
    if feature_name in ("monetary_total", "monetary_avg", "avg_freight_value"):
        return f"R$ {float(value):.0f}"
    return f"{value:.2f}"


# ---------------------------------------------------------------------------

def _queue_rows(threshold: float, limit: int) -> list[dict]:
    """Top-N at-risk customers with the metadata the queue + detail need."""
    sql = text(
        """
        WITH top_pred AS (
            SELECT id AS prediction_id,
                   customer_unique_id,
                   snapshot_date,
                   churn_probability,
                   threshold,
                   model_version,
                   predicted_at
              FROM serving.predictions
             ORDER BY churn_probability DESC
             LIMIT :limit
        ),
        cust_loc AS (
            SELECT DISTINCT ON (customer_unique_id)
                   customer_unique_id, customer_city, customer_state
              FROM analytics.stg_customers
        ),
        last_order AS (
            SELECT DISTINCT ON (customer_unique_id)
                   customer_unique_id,
                   order_purchase_timestamp,
                   payment_value,
                   item_count,
                   freight_value,
                   review_score,
                   delivery_days
              FROM analytics.int_customer_orders
             WHERE order_status NOT IN ('canceled', 'unavailable')
             ORDER BY customer_unique_id, order_purchase_timestamp DESC
        ),
        first_order AS (
            SELECT customer_unique_id,
                   MIN(order_purchase_timestamp) AS first_purchase
              FROM analytics.int_customer_orders
             GROUP BY customer_unique_id
        ),
        top_shap AS (
            SELECT DISTINCT ON (prediction_id)
                   prediction_id, feature_name, feature_value, shap_value
              FROM serving.shap_values
             WHERE rank = 1
        )
        SELECT tp.prediction_id,
               tp.customer_unique_id,
               tp.snapshot_date,
               tp.churn_probability,
               tp.threshold,
               tp.model_version,
               cf.frequency,
               cf.recency_days,
               cf.monetary_total,
               cf.avg_review_score,
               cf.avg_delivery_days,
               cl.customer_city,
               cl.customer_state,
               lo.order_purchase_timestamp,
               lo.payment_value,
               lo.item_count,
               lo.freight_value,
               fo.first_purchase,
               ts.feature_name AS top_feature,
               dn.display_name
          FROM top_pred tp
          LEFT JOIN analytics.customer_features cf
            ON cf.customer_unique_id = tp.customer_unique_id
           AND cf.snapshot_date     = tp.snapshot_date
          LEFT JOIN cust_loc cl
            ON cl.customer_unique_id = tp.customer_unique_id
          LEFT JOIN last_order lo
            ON lo.customer_unique_id = tp.customer_unique_id
          LEFT JOIN first_order fo
            ON fo.customer_unique_id = tp.customer_unique_id
          LEFT JOIN top_shap ts
            ON ts.prediction_id = tp.prediction_id
          LEFT JOIN serving.customer_display_names dn
            ON dn.customer_unique_id = tp.customer_unique_id
         ORDER BY tp.churn_probability DESC
        """
    )
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(sql, {"limit": limit}).mappings().all()]


def _summary_from_row(row: dict, threshold: float, _now: datetime) -> dict:
    risk = float(row["churn_probability"])
    monetary = float(row["monetary_total"]) if row.get("monetary_total") is not None else 0.0
    # Anchor "joined N mo/yr ago" to the prediction snapshot date — that's the
    # point in time the model "saw" this customer, so the tenure narrative
    # matches the features it scored on.
    snapshot = row.get("snapshot_date")
    anchor = (
        datetime.combine(snapshot, datetime.min.time())
        if snapshot is not None
        else datetime.utcnow()
    )
    first_purchase = row.get("first_purchase")
    if first_purchase is not None and getattr(first_purchase, "tzinfo", None) is not None:
        first_purchase = first_purchase.replace(tzinfo=None)
    return {
        "customer_unique_id": row["customer_unique_id"],
        "display_name": _display_name(
            row["customer_unique_id"], row.get("display_name")
        ),
        "city": _humanize_city(row.get("customer_city"), row.get("customer_state")),
        "ltv_brl": round(monetary),
        "risk": round(risk, 4),
        "tier": _tier(risk, threshold),
        "recency_days": int(row["recency_days"]) if row.get("recency_days") is not None else 0,
        "reviews_avg": float(row["avg_review_score"]) if row.get("avg_review_score") is not None else 0.0,
        "delivery_avg_days": float(row["avg_delivery_days"]) if row.get("avg_delivery_days") is not None else 0.0,
        "orders_lifetime": int(row["frequency"]) if row.get("frequency") is not None else 0,
        "joined_human": _months_since(first_purchase, anchor),
        "last_order_label": _last_order_label(
            row.get("payment_value"), row.get("item_count"), row.get("freight_value")
        ),
        "top_driver": _top_driver_label(row.get("top_feature")),
        # The email / sent state is sourced from serving.generated_emails on
        # the detail call; the queue only knows whether any draft exists.
        "status": "open",
        "email_sent_at": None,
    }


def _queue_metadata(rows: list[dict], threshold: float) -> dict:
    if not rows:
        return {
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "model_version": "—",
            "threshold": threshold,
        }
    # ``predicted_at`` reflects when the batch-scoring run wrote the rows;
    # that's what the "synced … ago" chip should compare against, not the
    # snapshot date (which lives in 2017).
    sql = text("SELECT MAX(predicted_at) FROM serving.predictions")
    with engine.connect() as conn:
        scored_at = conn.execute(sql).scalar()
    return {
        "scored_at": (scored_at.isoformat() if scored_at else datetime.now(timezone.utc).isoformat()),
        "model_version": rows[0].get("model_version") or "—",
        "threshold": round(float(rows[0].get("threshold") or threshold), 4),
    }


# ---------------------------------------------------------------------------

def inbox_customers(risk_filter: str = "all", limit: int = 100, offset: int = 0) -> dict:
    """The at-risk queue — summaries sorted by risk DESC, with tier totals.

    ``risk_filter`` is ``all`` | ``crit`` | ``high`` | ``med``; ``high`` means
    "high OR critical" (the queue filter behaves as "high or worse").
    """
    rows = _queue_rows(threshold=0.33, limit=MAX_QUEUE)
    meta = _queue_metadata(rows, threshold=0.33)
    threshold = meta["threshold"]
    now = datetime.now(timezone.utc)
    summaries = [_summary_from_row(r, threshold, now) for r in rows]

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

    return {
        "customers": summaries[offset : offset + limit],
        "totals": totals,
        **meta,
    }


def _drivers_for(prediction_id: int) -> list[dict]:
    sql = text(
        """
        SELECT feature_name, feature_value, shap_value, rank
          FROM serving.shap_values
         WHERE prediction_id = :pid
         ORDER BY rank
         LIMIT 6
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"pid": prediction_id}).mappings().all()
    return [
        {
            "feature": r["feature_name"],
            "value": _format_value(r["feature_name"], r["feature_value"]),
            "contrib": round(float(r["shap_value"]), 3),
            "why": DRIVER_WHY.get(
                r["feature_name"],
                "Contributes meaningfully to this customer's churn probability.",
            ),
        }
        for r in rows
    ]


def _history_for(customer_unique_id: str, snapshot_date) -> list[dict]:
    """Synthesize a short event history from the customer's order ledger.

    Pulls the most recent order, the customer's first order, and one mid-life
    peak (the order with the highest item count) — the events the right-rail
    activity card expects. Order timestamps after the snapshot are excluded
    so the history matches what the model "saw" at scoring time.
    """
    sql = text(
        """
        SELECT order_purchase_timestamp,
               order_delivered_customer_date,
               payment_value,
               item_count,
               review_score,
               delivery_days
          FROM analytics.int_customer_orders
         WHERE customer_unique_id = :cuid
           AND order_purchase_timestamp <= :snap
         ORDER BY order_purchase_timestamp
        """
    )
    with engine.connect() as conn:
        orders = list(
            conn.execute(sql, {"cuid": customer_unique_id, "snap": snapshot_date}).mappings()
        )
    if not orders:
        return []

    # Order timestamps in the warehouse are tz-naive — drop tz info on the
    # snapshot anchor so the deltas line up.
    snapshot_dt = (
        datetime.combine(snapshot_date, datetime.min.time())
        if snapshot_date is not None
        else datetime.utcnow()
    )

    def relative(ts: datetime) -> str:
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.replace(tzinfo=None)
        delta = snapshot_dt - ts
        days = max(0, int(delta.total_seconds() // 86400))
        if days == 0:
            return "today"
        if days < 30:
            return f"{days}d ago"
        if days < 365:
            return f"{days // 30} mo ago"
        return f"{days // 365} yr ago"

    last = orders[-1]
    first = orders[0]

    last_pay = float(last["payment_value"] or 0)
    last_delivery = last.get("delivery_days")
    last_review = last.get("review_score")
    last_note_bits = [f"R$ {last_pay:.0f}"]
    if last_delivery is not None:
        last_note_bits.append(f"delivered {int(round(last_delivery))} days later")
    if last_review is not None:
        last_note_bits.append(f"{int(last_review)}-star review")

    events: list[dict] = [
        {
            "ts": last["order_purchase_timestamp"].isoformat(),
            "ts_human": relative(last["order_purchase_timestamp"]),
            "title": "Last order",
            "note": " · ".join(last_note_bits),
            "tag": "risk"
            if (last_review is not None and last_review <= 2)
            or (last_delivery is not None and last_delivery >= 18)
            else "neutral",
        }
    ]

    # If there's a clearly bad review somewhere in history, surface it.
    bad = [o for o in orders if o.get("review_score") is not None and o["review_score"] <= 2]
    if bad and bad[-1] is not last:
        b = bad[-1]
        events.append(
            {
                "ts": b["order_purchase_timestamp"].isoformat(),
                "ts_human": relative(b["order_purchase_timestamp"]),
                "title": f"Left a {int(b['review_score'])}-star review",
                "note": None,
                "tag": "risk",
            }
        )

    if first is not last:
        events.append(
            {
                "ts": first["order_purchase_timestamp"].isoformat(),
                "ts_human": relative(first["order_purchase_timestamp"]),
                "title": "First order",
                "note": None,
                "tag": "neutral",
            }
        )

    # Events render newest-first in the activity card.
    events.sort(key=lambda e: e["ts"], reverse=True)
    return events


def _email_and_eval(prediction_id: int) -> tuple[dict, dict]:
    """Latest email draft for a prediction + its judge grade, if either exists."""
    sql = text(
        """
        SELECT id, subject, body, model, generated_at
          FROM serving.generated_emails
         WHERE prediction_id = :pid
         ORDER BY generated_at DESC
         LIMIT 1
        """
    )
    grade_sql = text(
        """
        SELECT overall_score, latency_ms, passed
          FROM serving.eval_scores
         WHERE email_id = :eid
         ORDER BY created_at DESC
         LIMIT 1
        """
    )
    with engine.connect() as conn:
        email_row = conn.execute(sql, {"pid": prediction_id}).mappings().first()
        grade_row = None
        if email_row is not None:
            grade_row = conn.execute(grade_sql, {"eid": email_row["id"]}).mappings().first()

    if email_row is None:
        return _empty_email(), _empty_eval()

    generated_at = (
        email_row["generated_at"].isoformat()
        if email_row.get("generated_at")
        else datetime.now(timezone.utc).isoformat()
    )
    email = {
        "generated_at": generated_at,
        "generated_by": email_row["model"] or "claude-haiku-4-5",
        "persona": "evidence-grounded",
        "grounded_on": "top SHAP drivers",
        "subject": email_row["subject"] or "",
        "body": email_row["body"] or "",
        "to": "—",
        "from_name": "Retention",
    }
    eval_block = (
        {
            "judge_score": round(float(grade_row["overall_score"]), 2),
            "judge_ms": int(grade_row["latency_ms"] or 0),
            "pass_threshold": 4.0,
            "passed": bool(grade_row["passed"]),
        }
        if grade_row is not None
        else _empty_eval()
    )
    return email, eval_block


def _empty_email() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "—",
        "persona": "—",
        "grounded_on": "—",
        "subject": "No email drafted yet",
        "body": (
            "No retention email has been generated for this customer.\n\n"
            "Run the pipeline with the “Generate retention emails” option on, "
            "or trigger email generation from the Scoring page, and the draft "
            "will appear here."
        ),
        "to": "—",
        "from_name": "Retention",
    }


def _empty_eval() -> dict:
    return {"judge_score": 0.0, "judge_ms": 0, "pass_threshold": 4.0, "passed": False}


def _plays_for(top_feature: str | None) -> list[dict]:
    base = PLAY_BY_DRIVER.get(top_feature or "", DEFAULT_PLAYS)
    plays: list[dict] = []
    for i, p in enumerate(base):
        plays.append({**p, "active": i == 0})
    return plays


def _cohort_label(top_feature: str | None, ltv_brl: float) -> str:
    base = {
        "avg_review_score": "review-risk",
        "avg_delivery_days": "slow-delivery",
        "recency_days": "lapsed",
        "frequency": "declining-frequency",
        "avg_freight_value": "price-sensitive",
        "avg_categories_per_order": "single-category",
    }.get(top_feature or "", "at-risk")
    tier = (
        "high-value"
        if ltv_brl >= 1500
        else "mid-value"
        if ltv_brl >= 500
        else "low-value"
    )
    return f"{base} · {tier}"


def inbox_customer(customer_id: str) -> dict | None:
    """Full centre + right-pane detail for one customer, or ``None`` if unknown."""
    sql = text(
        """
        SELECT p.id AS prediction_id,
               p.customer_unique_id,
               p.snapshot_date,
               p.churn_probability,
               p.threshold,
               p.model_version,
               cf.frequency, cf.recency_days, cf.monetary_total,
               cf.avg_review_score, cf.avg_delivery_days,
               cl.customer_city, cl.customer_state,
               lo.order_purchase_timestamp, lo.payment_value,
               lo.item_count, lo.freight_value,
               fo.first_purchase,
               ts.feature_name AS top_feature,
               dn.display_name
          FROM serving.predictions p
          LEFT JOIN analytics.customer_features cf
            ON cf.customer_unique_id = p.customer_unique_id
           AND cf.snapshot_date     = p.snapshot_date
          LEFT JOIN (
            SELECT DISTINCT ON (customer_unique_id)
                   customer_unique_id, customer_city, customer_state
              FROM analytics.stg_customers
          ) cl ON cl.customer_unique_id = p.customer_unique_id
          LEFT JOIN (
            SELECT DISTINCT ON (customer_unique_id)
                   customer_unique_id, order_purchase_timestamp, payment_value,
                   item_count, freight_value, review_score, delivery_days
              FROM analytics.int_customer_orders
             WHERE order_status NOT IN ('canceled', 'unavailable')
             ORDER BY customer_unique_id, order_purchase_timestamp DESC
          ) lo ON lo.customer_unique_id = p.customer_unique_id
          LEFT JOIN (
            SELECT customer_unique_id, MIN(order_purchase_timestamp) AS first_purchase
              FROM analytics.int_customer_orders
             GROUP BY customer_unique_id
          ) fo ON fo.customer_unique_id = p.customer_unique_id
          LEFT JOIN (
            SELECT DISTINCT ON (prediction_id)
                   prediction_id, feature_name FROM serving.shap_values WHERE rank = 1
          ) ts ON ts.prediction_id = p.id
          LEFT JOIN serving.customer_display_names dn
            ON dn.customer_unique_id = p.customer_unique_id
         WHERE p.customer_unique_id = :cuid
         ORDER BY p.predicted_at DESC
         LIMIT 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"cuid": customer_id}).mappings().first()
    if row is None:
        return None

    threshold = float(row["threshold"] or 0.33)
    summary = _summary_from_row(dict(row), threshold, datetime.now(timezone.utc))
    drivers = _drivers_for(row["prediction_id"])
    history = _history_for(customer_id, row["snapshot_date"])
    email, eval_block = _email_and_eval(row["prediction_id"])

    # If a real email exists, surface its sent timestamp on the summary.
    if email["generated_by"] != "—":
        summary["status"] = "sent"
        summary["email_sent_at"] = email["generated_at"]

    ltv = summary["ltv_brl"]
    plays = _plays_for(row.get("top_feature"))
    cohort_label = _cohort_label(row.get("top_feature"), ltv)
    cohort_save_rate_pct = plays[0]["save_rate_pct"] if plays else 0
    cohort_n = plays[0]["sample_n"] if plays else 0

    return {
        "summary": summary,
        "drivers": drivers,
        "history": history,
        "email": email,
        "eval": eval_block,
        "plays": plays,
        "cohort_label": cohort_label,
        "cohort_save_rate_pct": cohort_save_rate_pct,
        "cohort_n": cohort_n,
    }


# Back-compat — older modules expect this name to exist.
def _summary(c: dict) -> dict:  # pragma: no cover
    """Retained only to keep imports compatible with earlier fixture code."""
    return c
