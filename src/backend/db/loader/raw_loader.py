"""One-time migration: load the 9 Olist CSVs into the `raw` Postgres schema.

This is a bootstrap step, not part of the recurring pipeline. Run it once,
after the database is up and Alembic migrations are applied:

    python -m backend.db.loader.raw_loader

Each CSV becomes an all-text table in the `raw` schema — a verbatim copy of
source. The medallion "silver" cleaning and typing happens later, in dbt.
The load is a full refresh: every table is dropped and recreated, so the
script is idempotent and safe to re-run.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from ..session import engine

RAW_SCHEMA = "raw"
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "raw"


def _table_name(csv_path: Path) -> str:
    """Derive the raw table name from a CSV filename (drops a `_dataset` suffix)."""
    stem = csv_path.stem
    suffix = "_dataset"
    return stem[: -len(suffix)] if stem.endswith(suffix) else stem


def _read_header(csv_path: Path) -> list[str]:
    """Return normalised column names from a CSV header (BOM-tolerant)."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh))
    return [col.strip().lower() for col in header]


def _count_records(csv_path: Path) -> int:
    """Count data rows in a CSV — quoted fields with embedded newlines included."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def load_csv(raw_conn, csv_path: Path) -> tuple[str, int]:
    """Drop/recreate a `raw.*` table from the CSV header and COPY the file in.

    Returns the table name and the number of rows loaded.
    """
    table = _table_name(csv_path)
    columns = _read_header(csv_path)
    cols_ddl = ", ".join(f'"{c}" text' for c in columns)
    cols_list = ", ".join(f'"{c}"' for c in columns)
    qualified = f'{RAW_SCHEMA}."{table}"'

    with raw_conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {qualified}")
        cur.execute(
            f"CREATE TABLE {qualified} "
            f"({cols_ddl}, _loaded_at timestamptz NOT NULL DEFAULT now())"
        )
        copy_sql = (
            f"COPY {qualified} ({cols_list}) "
            f"FROM STDIN WITH (FORMAT csv, HEADER true)"
        )
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            cur.copy_expert(copy_sql, fh)
        cur.execute(f"SELECT count(*) FROM {qualified}")
        loaded = cur.fetchone()[0]
    raw_conn.commit()
    return table, loaded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load the Olist CSVs into the raw Postgres schema."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory of source CSVs (default: {DEFAULT_DATA_DIR})",
    )
    args = parser.parse_args(argv)

    csv_files = sorted(args.data_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {args.data_dir}", file=sys.stderr)
        return 1

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
        raw_conn.commit()

        print(f"Loading {len(csv_files)} CSV(s) into schema '{RAW_SCHEMA}'")
        failures = 0
        for csv_path in csv_files:
            expected = _count_records(csv_path)
            table, loaded = load_csv(raw_conn, csv_path)
            ok = loaded == expected
            failures += int(not ok)
            status = "OK" if ok else f"MISMATCH (expected {expected:,})"
            print(f"  raw.{table:<34} {loaded:>9,} rows  {status}")

        if failures:
            print(f"{failures} table(s) failed the row-count check", file=sys.stderr)
            return 1
        print("Done.")
        return 0
    finally:
        raw_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
