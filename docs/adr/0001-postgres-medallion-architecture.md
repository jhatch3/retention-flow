# Postgres medallion architecture with dbt and Dagster

The README's original design kept raw Olist data as files (CSV → Parquet). We
instead make Postgres the whole data pipeline. A one-time migration loads all 9
raw Olist tables, verbatim and all-text, into a `raw` schema, and a simulation
adds synthetic repeat orders in a `synthetic` schema. dbt then transforms them —
staging models as **views** (the cleaned "silver" layer) and a gold table
`customer_features` — into an `analytics` schema. Dagster orchestrates the dbt
transformations on a nightly schedule.

There is no materialized silver schema — silver is just dbt views inside
`analytics`. The CSV load is a one-time bootstrap, not a recurring pipeline
step; the nightly pipeline reads only from Postgres.

## Consequences

- The loader owns `raw` and `synthetic`; dbt owns `analytics`.
- dbt rebuilds the gold table on every run (`table` materialization drops and
  recreates it), so anything consuming it must treat it as a rebuilt table,
  not a stable reference target.
