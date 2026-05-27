"""Read-only DB tools the retention-email generator can call to ground its
output in real customer and marketplace data.

Each function:
- Takes the inputs Claude will pass (typically customer_unique_id + optional limit).
- Returns a plain dict/list-of-dicts that is JSON-serializable (no datetime objects).
- Returns an explicit empty-result shape if the customer/category isn't found,
  rather than raising — this lets the model adapt gracefully when grounding
  data is missing.

All queries are raw SQL via the shared SQLAlchemy engine (matches the existing
pattern in src/backend/api/scoring.py and services.py).
"""

from sqlalchemy import text

from src.backend.db.session import engine


def get_customer_delivery_stats(customer_unique_id: str) -> dict:
    """Customer's delivery performance vs. marketplace baseline.

    Returns a dict with:
      customer_unique_id, customer_avg_delivery_days, customer_delivered_orders,
      marketplace_avg_delivery_days, gap_vs_marketplace_days
    """
    customer_sql = text(
        """
        SELECT
            AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400.0) AS avg_days,
            COUNT(*) AS delivered_orders
        FROM raw.olist_orders o
        JOIN raw.olist_customers c ON c.customer_id = o.customer_id
        WHERE c.customer_unique_id = :cuid
          AND o.order_delivered_customer_date IS NOT NULL
          AND o.order_delivered_customer_date <> ''
        """
    )
    marketplace_sql = text(
        """
        SELECT AVG(EXTRACT(EPOCH FROM (order_delivered_customer_date::timestamp - order_purchase_timestamp::timestamp)) / 86400.0) AS avg_days
        FROM raw.olist_orders
        WHERE order_delivered_customer_date IS NOT NULL
          AND order_delivered_customer_date <> ''
        """
    )

    with engine.connect() as conn:
        customer = conn.execute(customer_sql, {"cuid": customer_unique_id}).mappings().first()
        marketplace = conn.execute(marketplace_sql).mappings().first()

    customer_avg = float(customer["avg_days"]) if customer and customer["avg_days"] is not None else None
    marketplace_avg = float(marketplace["avg_days"]) if marketplace and marketplace["avg_days"] is not None else None
    delivered_orders = int(customer["delivered_orders"]) if customer else 0

    gap = None
    if customer_avg is not None and marketplace_avg is not None:
        gap = round(customer_avg - marketplace_avg, 2)

    return {
        "customer_unique_id": customer_unique_id,
        "customer_avg_delivery_days": round(customer_avg, 2) if customer_avg is not None else None,
        "customer_delivered_orders": delivered_orders,
        "marketplace_avg_delivery_days": round(marketplace_avg, 2) if marketplace_avg is not None else None,
        "gap_vs_marketplace_days": gap,
    }


def get_customer_recent_orders(customer_unique_id: str, limit: int = 5) -> list[dict]:
    """Last N orders for the customer with category, delivery_days, and review_score.

    Empty list if the customer has no orders. limit is clamped to [1, 20].
    """
    limit = max(1, min(int(limit), 20))

    sql = text(
        """
        SELECT
            o.order_id,
            o.order_status,
            o.order_purchase_timestamp AS purchase_date,
            NULLIF(o.order_delivered_customer_date, '') AS delivered_date,
            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                 AND o.order_delivered_customer_date <> ''
                THEN EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400.0
                ELSE NULL
            END AS delivery_days,
            STRING_AGG(DISTINCT COALESCE(pt.product_category_name_english, p.product_category_name), ', ') AS categories,
            AVG(NULLIF(r.review_score, '')::numeric) AS avg_review_score
        FROM raw.olist_customers c
        JOIN raw.olist_orders o ON c.customer_id = o.customer_id
        LEFT JOIN raw.olist_order_items oi ON o.order_id = oi.order_id
        LEFT JOIN raw.olist_products p ON oi.product_id = p.product_id
        LEFT JOIN raw.product_category_name_translation pt ON p.product_category_name = pt.product_category_name
        LEFT JOIN raw.olist_order_reviews r ON o.order_id = r.order_id
        WHERE c.customer_unique_id = :cuid
        GROUP BY o.order_id, o.order_status, o.order_purchase_timestamp, o.order_delivered_customer_date
        ORDER BY o.order_purchase_timestamp DESC
        LIMIT :limit
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, {"cuid": customer_unique_id, "limit": limit}).mappings().all()

    out = []
    for r in rows:
        out.append(
            {
                "order_id": r["order_id"],
                "order_status": r["order_status"],
                "purchase_date": r["purchase_date"],
                "delivered_date": r["delivered_date"],
                "delivery_days": round(float(r["delivery_days"]), 1) if r["delivery_days"] is not None else None,
                "categories": r["categories"],
                "avg_review_score": round(float(r["avg_review_score"]), 2) if r["avg_review_score"] is not None else None,
            }
        )
    return out


def get_category_baseline(category: str) -> dict:
    """Marketplace-wide stats for a product category: avg delivery days, avg review score, order count.

    `category` accepts the English category name (e.g. "books_general_interest", "electronics", "health_beauty").
    Falls back to the Portuguese category name if the English mapping doesn't match. Returns null fields if
    the category isn't found.
    """
    sql = text(
        """
        SELECT
            COALESCE(pt.product_category_name_english, p.product_category_name) AS category,
            COUNT(DISTINCT o.order_id) AS order_count,
            AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400.0) AS avg_delivery_days,
            AVG(NULLIF(r.review_score, '')::numeric) AS avg_review_score
        FROM raw.olist_orders o
        JOIN raw.olist_order_items oi ON o.order_id = oi.order_id
        JOIN raw.olist_products p ON oi.product_id = p.product_id
        LEFT JOIN raw.product_category_name_translation pt ON p.product_category_name = pt.product_category_name
        LEFT JOIN raw.olist_order_reviews r ON o.order_id = r.order_id
        WHERE (pt.product_category_name_english = :category OR p.product_category_name = :category)
          AND o.order_delivered_customer_date IS NOT NULL
          AND o.order_delivered_customer_date <> ''
        GROUP BY COALESCE(pt.product_category_name_english, p.product_category_name)
        """
    )

    with engine.connect() as conn:
        row = conn.execute(sql, {"category": category}).mappings().first()

    if row is None:
        return {
            "category": category,
            "order_count": 0,
            "avg_delivery_days": None,
            "avg_review_score": None,
            "note": "category not found in marketplace data",
        }

    return {
        "category": row["category"],
        "order_count": int(row["order_count"]),
        "avg_delivery_days": round(float(row["avg_delivery_days"]), 2) if row["avg_delivery_days"] is not None else None,
        "avg_review_score": round(float(row["avg_review_score"]), 2) if row["avg_review_score"] is not None else None,
    }


def get_customer_review_history(customer_unique_id: str, limit: int = 10) -> list[dict]:
    """Last N reviews the customer has left, with score, date, comment, and category context.

    Empty list if the customer has no reviews. limit is clamped to [1, 25].
    """
    limit = max(1, min(int(limit), 25))

    sql = text(
        """
        SELECT
            r.review_id,
            NULLIF(r.review_score, '')::numeric AS review_score,
            r.review_creation_date AS review_date,
            NULLIF(r.review_comment_title, '') AS title,
            NULLIF(r.review_comment_message, '') AS comment,
            STRING_AGG(DISTINCT COALESCE(pt.product_category_name_english, p.product_category_name), ', ') AS categories
        FROM raw.olist_customers c
        JOIN raw.olist_orders o ON c.customer_id = o.customer_id
        JOIN raw.olist_order_reviews r ON o.order_id = r.order_id
        LEFT JOIN raw.olist_order_items oi ON o.order_id = oi.order_id
        LEFT JOIN raw.olist_products p ON oi.product_id = p.product_id
        LEFT JOIN raw.product_category_name_translation pt ON p.product_category_name = pt.product_category_name
        WHERE c.customer_unique_id = :cuid
        GROUP BY r.review_id, r.review_score, r.review_creation_date, r.review_comment_title, r.review_comment_message
        ORDER BY r.review_creation_date DESC
        LIMIT :limit
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, {"cuid": customer_unique_id, "limit": limit}).mappings().all()

    return [
        {
            "review_id": r["review_id"],
            "review_score": int(r["review_score"]) if r["review_score"] is not None else None,
            "review_date": r["review_date"],
            "title": r["title"],
            "comment": r["comment"],
            "categories": r["categories"],
        }
        for r in rows
    ]
