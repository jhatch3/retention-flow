"""Synthetic repeat-order generator — augments Olist with recurring customers.

Olist is a near-pure single-purchase marketplace (~3% of customers ever
reorder), which makes any churn label degenerate. This one-time simulation
adds synthetic repeat orders so that churn becomes a learnable target.

Reorder behaviour is *signal-driven*: a customer's propensity to come back is
a function of their real first-order experience — a good review score and
fast delivery raise it, slow delivery lowers it — plus noise. The churn model
therefore has genuine signal to learn. See
docs/adr/0004-synthetic-repeat-order-augmentation.md.

Output goes to a separate `synthetic` schema; the `raw` schema stays a
verbatim copy of Olist. dbt staging models union raw + synthetic.

Run once, after the raw load and before dbt:

    python -m backend.db.simulation.repeat_orders
"""

from __future__ import annotations

import argparse
import csv
import io
import uuid
from datetime import datetime, timedelta

import numpy as np

from ..session import engine

SYNTH_SCHEMA = "synthetic"
SEED = 42
REPEAT_FRACTION = 0.35  # share of customers given repeat behaviour
MAX_EXTRA_ORDERS = 4

# Synthetic table layouts — column-for-column with the raw.olist_* tables
# (minus the loader's _loaded_at), so dbt staging models can union them.
TABLE_COLUMNS: dict[str, list[str]] = {
    "customers": [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    ],
    "orders": [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    "order_items": [
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    ],
    "order_payments": [
        "order_id", "payment_sequential", "payment_type",
        "payment_installments", "payment_value",
    ],
    "order_reviews": [
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message", "review_creation_date",
        "review_answer_timestamp",
    ],
}


def _new_id() -> str:
    """A 32-char hex id, shaped like an Olist identifier."""
    return uuid.uuid4().hex


def _fmt(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def fetch_first_orders(cur) -> list[dict]:
    """Return one row per customer: identity plus first-order experience."""
    cur.execute(
        """
        with reviews as (
            select order_id, avg(review_score::numeric) as review_score
            from raw.olist_order_reviews
            where review_score ~ '^[1-5]$'
            group by 1
        ),
        ranked as (
            select
                c.customer_unique_id,
                c.customer_id,
                c.customer_zip_code_prefix,
                c.customer_city,
                c.customer_state,
                o.order_id,
                o.order_purchase_timestamp::timestamp as purchased_at,
                extract(epoch from (
                    nullif(o.order_delivered_customer_date, '')::timestamp
                    - o.order_purchase_timestamp::timestamp)) / 86400.0
                    as delivery_days,
                row_number() over (
                    partition by c.customer_unique_id
                    order by o.order_purchase_timestamp
                ) as rn
            from raw.olist_orders o
            join raw.olist_customers c on o.customer_id = c.customer_id
            where nullif(o.order_purchase_timestamp, '') is not null
        )
        select r.customer_unique_id, r.customer_id, r.customer_zip_code_prefix,
               r.customer_city, r.customer_state, r.order_id, r.purchased_at,
               r.delivery_days, rv.review_score
        from ranked r
        left join reviews rv on rv.order_id = r.order_id
        where r.rn = 1
        """
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_order_lines(cur) -> tuple[dict, dict]:
    """Index every order's items and payments by order_id (for cloning)."""
    items: dict[str, list] = {}
    cur.execute(
        "select order_id, order_item_id, product_id, seller_id, "
        "shipping_limit_date, price, freight_value from raw.olist_order_items"
    )
    for r in cur.fetchall():
        items.setdefault(r[0], []).append(r)

    payments: dict[str, list] = {}
    cur.execute(
        "select order_id, payment_sequential, payment_type, "
        "payment_installments, payment_value from raw.olist_order_payments"
    )
    for r in cur.fetchall():
        payments.setdefault(r[0], []).append(r)
    return items, payments


def simulate(customers, items_by_order, payments_by_order, rng):
    """Generate synthetic repeat orders for the highest-propensity customers."""
    review = np.array(
        [float(c["review_score"]) if c["review_score"] is not None else 3.0
         for c in customers]
    )
    delivery = np.array(
        [float(c["delivery_days"]) if c["delivery_days"] is not None else 12.0
         for c in customers]
    )
    # Signal: good review raises propensity, slow delivery lowers it.
    z_delivery = (delivery - 12.0) / 10.0
    logit = 0.6 * (review - 3.0) - 0.5 * z_delivery + rng.normal(0, 0.5, len(customers))
    propensity = 1.0 / (1.0 + np.exp(-logit))

    # The top REPEAT_FRACTION by propensity become repeat customers.
    n_repeat = int(len(customers) * REPEAT_FRACTION)
    is_repeat = np.zeros(len(customers), dtype=bool)
    is_repeat[np.argsort(-propensity)[:n_repeat]] = True

    rows: dict[str, list] = {t: [] for t in TABLE_COLUMNS}
    for i, c in enumerate(customers):
        if not is_repeat[i]:
            continue
        p = float(propensity[i])
        n_orders = min(int(rng.geometric(0.55)), MAX_EXTRA_ORDERS)
        real_items = items_by_order.get(c["order_id"], [])
        real_payments = payments_by_order.get(c["order_id"], [])

        # Higher propensity -> shorter gaps -> reorders inside the churn window.
        mean_gap = 60.0 + (1.0 - p) * 400.0
        ts = c["purchased_at"]
        for _ in range(n_orders):
            gap = float(np.clip(rng.exponential(mean_gap), 7, 900))
            ts = ts + timedelta(days=gap)
            order_id, customer_id = _new_id(), _new_id()
            delivered = ts + timedelta(days=float(np.clip(rng.normal(12, 4), 2, 40)))

            rows["customers"].append([
                customer_id, c["customer_unique_id"],
                c["customer_zip_code_prefix"], c["customer_city"],
                c["customer_state"],
            ])
            rows["orders"].append([
                order_id, customer_id, "delivered",
                _fmt(ts), _fmt(ts + timedelta(days=1)),
                _fmt(ts + timedelta(days=3)), _fmt(delivered),
                _fmt(ts + timedelta(days=24)),
            ])
            if real_items:
                for j, it in enumerate(real_items, start=1):
                    # it = (order_id, order_item_id, product_id, seller_id,
                    #       shipping_limit_date, price, freight_value)
                    rows["order_items"].append([
                        order_id, str(j), it[2], it[3],
                        _fmt(ts + timedelta(days=2)), it[5], it[6],
                    ])
            else:
                rows["order_items"].append([
                    order_id, "1", _new_id(), _new_id(),
                    _fmt(ts + timedelta(days=2)), "100.00", "15.00",
                ])
            if real_payments:
                for seq, pay in enumerate(real_payments, start=1):
                    # pay = (order_id, payment_sequential, payment_type,
                    #        payment_installments, payment_value)
                    rows["order_payments"].append([
                        order_id, str(seq), pay[2], pay[3], pay[4],
                    ])
            else:
                rows["order_payments"].append([
                    order_id, "1", "credit_card", "1", "115.00",
                ])
            # Review score also tracks propensity (loyal -> happier).
            score = int(np.clip(round(rng.normal(2.0 + 3.0 * p, 0.8)), 1, 5))
            rows["order_reviews"].append([
                _new_id(), order_id, str(score), "", "",
                _fmt(delivered), _fmt(delivered + timedelta(days=2)),
            ])
    return rows, is_repeat


def create_schema(cur) -> None:
    """(Re)create the synthetic schema and its all-text tables."""
    cur.execute(f"create schema if not exists {SYNTH_SCHEMA}")
    for table, cols in TABLE_COLUMNS.items():
        cur.execute(f'drop table if exists {SYNTH_SCHEMA}."{table}"')
        cols_ddl = ", ".join(f'"{c}" text' for c in cols)
        cur.execute(f'create table {SYNTH_SCHEMA}."{table}" ({cols_ddl})')


def bulk_load(cur, table: str, columns: list[str], rows: list) -> None:
    """COPY generated rows into a synthetic table."""
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    buf.seek(0)
    col_list = ", ".join(f'"{c}"' for c in columns)
    cur.copy_expert(
        f'COPY {SYNTH_SCHEMA}."{table}" ({col_list}) FROM STDIN WITH (FORMAT csv)',
        buf,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate synthetic repeat orders into the synthetic schema."
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            print("Reading first-order experience per customer ...")
            customers = fetch_first_orders(cur)
            items_by_order, payments_by_order = fetch_order_lines(cur)
        print(f"  {len(customers):,} customers")

        rows, is_repeat = simulate(customers, items_by_order, payments_by_order, rng)

        with raw_conn.cursor() as cur:
            create_schema(cur)
            for table, cols in TABLE_COLUMNS.items():
                bulk_load(cur, table, cols, rows[table])
                print(f"  synthetic.{table:<16} {len(rows[table]):>9,} rows")
        raw_conn.commit()

        print(
            f"Repeat customers: {int(is_repeat.sum()):,} "
            f"({is_repeat.mean():.1%} of {len(customers):,})"
        )
        print("Done.")
        return 0
    finally:
        raw_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
