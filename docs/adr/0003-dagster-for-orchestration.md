# Dagster for pipeline orchestration

The dbt transformations need to run on a schedule. We orchestrate them with
Dagster rather than plain cron or dbt Cloud. Via the `dagster-dbt` integration,
each dbt model becomes an observable Dagster asset and each dbt test becomes an
asset check — giving lineage, run history, and failure visibility that a cron
entry does not. dbt Cloud was rejected to avoid a SaaS dependency in an
otherwise self-hostable stack.

This adds a substantial tool to an otherwise lean project (the README
deliberately avoids heavy infrastructure). The trade-off is accepted because
the data pipeline — load, transform, test, schedule — is itself a core part of
what this project demonstrates.

## Consequences

- Dagster orchestrates dbt only. The one-time CSV→`raw` migration is not a
  Dagster asset; the asset graph begins from the raw tables already in Postgres.
