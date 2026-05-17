# RetentionFlow

A churn-aware retention system: it predicts customer churn from Olist
e-commerce data, explains each prediction with SHAP, and generates grounded
retention emails. The database is a medallion-style pipeline across three
Postgres schemas, orchestrated nightly by Dagster.

## Language

### Data layers

**Raw** — `raw` schema:
The 9 Olist source tables loaded verbatim from CSV (all-text columns) by a one-time migration. The pipeline's source of truth — never re-loaded from CSV by the recurring pipeline.
_Avoid_: "bronze" in code/schema names; the schema is `raw`.

**Synthetic augmentation** — `synthetic` schema:
Simulated repeat orders generated to give the data a learnable churn signal — Olist itself has almost no repeat customers. Reorder propensity is driven by the customer's real first-order experience. Unioned with `raw` by the dbt staging views.

**Staging** — dbt views in the `analytics` schema:
Cleaned, typed, deduplicated views over the raw tables — the medallion "silver" layer. Exists only as dbt views, not as a maintained schema of tables.
_Avoid_: "silver schema" — there is no separate silver schema.

**Gold table** — `analytics.customer_features`:
The ML-ready training table — one feature snapshot per customer, carrying the churn label and a train/test/validation split.
_Avoid_: "training data" (ambiguous with the split), "customers" (that is the raw source table).

**Serving** — `serving` schema:
Inference outputs and audit trail: predictions, SHAP values, generated emails, eval scores. The application's write model.

### Domain terms

**Snapshot date**:
The point-in-time feature cutoff. Every feature in a feature snapshot is computed using only events on or before this date.

**Observation horizon**:
The window after the snapshot date over which churn is observed (default 180 days).

**Feature snapshot**:
The set of engineered behavioral features for one customer computed as of one snapshot date — one row of the gold table.

**Churn label**:
True when a customer placed no order within the observation horizon following the snapshot date.
_Avoid_: the older "as-of-snapshot dormancy" definition — that is target-leaky against recency features.

**Split**:
The train / test / validation assignment carried on every gold row, set by a churn-label-stratified deterministic hash of `customer_unique_id` (70 / 15 / 15).

## Relationships

- **Raw** and the **Synthetic augmentation** are unioned by the dbt **Staging** views, which are aggregated into the **Gold table**
- A model reads the **Gold table** and writes predictions into **Serving**
- **Dagster** orchestrates the dbt transformations on a nightly schedule
- A **prediction** references its **feature snapshot** by natural key (`customer_unique_id` + `snapshot_date`), not a foreign key — the gold table is rebuilt by dbt

## Flagged ambiguities

- "customers" meant both the Olist source table and the engineered feature table — **resolved**: the source table is `raw.olist_customers`; the gold table is `analytics.customer_features`.
- "silver" was nearly used as a schema name for verbatim-loaded raw data — **resolved**: a verbatim load is the **Raw** layer; silver is the dbt **Staging** views, with no schema of its own.
