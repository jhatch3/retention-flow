# Three-schema medallion database with dbt and Dagster

The README's original design kept raw Olist data as files (CSV → Parquet) and
used Postgres only for derived data. We instead make Postgres the whole
pipeline. A one-time migration loads all 9 raw Olist tables, verbatim and
all-text, into a `raw` schema. dbt then transforms them — staging models as
**views** (the cleaned "silver" layer) and a gold table `customer_features` —
into an `analytics` schema. The `serving` schema (predictions, SHAP values,
generated emails, eval scores) is owned by Alembic. Dagster orchestrates the
dbt transformations on a nightly schedule.

Three schemas, not four: there is no materialized silver schema — silver is
just dbt views inside `analytics`. The CSV load is a one-time bootstrap, not a
recurring pipeline step; the nightly pipeline reads only from Postgres.

## Consequences

- dbt rebuilds the gold table on every run, so `serving.predictions` references
  a feature snapshot by **natural key** (`customer_unique_id` + `snapshot_date`),
  not a foreign key. Referential integrity into gold is by convention.
- Ownership is split three ways: the loader owns `raw`, dbt owns `analytics`,
  Alembic owns `serving`. No single tool manages the whole database.
