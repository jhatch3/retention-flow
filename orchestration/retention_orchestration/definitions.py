"""Dagster definitions for the RetentionFlow pipeline.

Via the dagster-dbt integration, every dbt model becomes a Dagster asset and
every dbt test becomes an asset check. A nightly schedule rebuilds the whole
graph with `dbt build`.

The one-time CSV-to-`raw` migration is deliberately NOT modelled here — the
asset graph starts from the raw tables already present in Postgres. See
docs/adr/0003-dagster-for-orchestration.md.
"""

from __future__ import annotations

from pathlib import Path

from dagster import Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

# The dbt project lives at the repo root, beside this orchestration package.
TRANSFORM_DIR = Path(__file__).resolve().parents[2] / "transform"

dbt_project = DbtProject(
    project_dir=TRANSFORM_DIR,
    profiles_dir=TRANSFORM_DIR,
)
# Generate target/manifest.json from the dbt project when running `dagster dev`.
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def retention_dbt_assets(context, dbt: DbtCliResource):
    """All dbt models as assets; all dbt tests as asset checks."""
    yield from dbt.cli(["build"], context=context).stream()


# A job over the full dbt asset graph, scheduled nightly at 02:00.
nightly_job = define_asset_job(name="nightly_pipeline", selection="*")

nightly_schedule = ScheduleDefinition(
    name="nightly_refresh",
    job=nightly_job,
    cron_schedule="0 2 * * *",
)

defs = Definitions(
    assets=[retention_dbt_assets],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt_project,
            profiles_dir=str(TRANSFORM_DIR),
        ),
    },
    schedules=[nightly_schedule],
)
