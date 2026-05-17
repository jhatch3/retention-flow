"""Timed pipeline rebuild — drop the `analytics` schema and re-run `dbt build`,
streaming a progress event per dbt node so the dashboard can time the run.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from ..db.session import engine
from .runs import record_run

REPO_ROOT = Path(__file__).resolve().parents[3]
TRANSFORM_DIR = REPO_ROOT / "transform"

_NODE = re.compile(r"(\d+) of (\d+)")
_KEEP = (" OK ", " PASS ", " ERROR", " FAIL", "Completed successfully", "Done.")


def rebuild_events() -> Iterator[dict]:
    """Drop `analytics`, run `dbt build`, yielding a timed event per dbt node."""
    t0 = time.perf_counter()

    def ev(stage: str, message: str, progress: float, **extra) -> dict:
        return {
            "stage": stage,
            "message": message,
            "progress": progress,
            "elapsed": round(time.perf_counter() - t0, 2),
            "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            **extra,
        }

    yield ev("start", "Dropping the analytics schema", 0.02)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS analytics CASCADE"))
    yield ev("wiped", "analytics schema dropped — running dbt build", 0.05)

    proc = subprocess.Popen(
        [
            "dbt", "--no-use-colors", "build",
            "--project-dir", str(TRANSFORM_DIR),
            "--profiles-dir", str(TRANSFORM_DIR),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip()
        if not any(k in line for k in _KEEP):
            continue
        match = _NODE.search(line)
        progress = (
            int(match.group(1)) / int(match.group(2)) * 0.9 + 0.05
            if match
            else 0.95
        )
        # drop dbt's leading timestamp, collapse its dotted padding
        message = line.split("  ", 1)[-1].strip() if "  " in line else line
        message = re.sub(r"\s*\.{3,}\s*", "  ", message)
        yield ev("dbt", message, min(progress, 0.95))
    proc.wait()

    if proc.returncode != 0:
        yield ev("error", f"dbt build failed (exit {proc.returncode})", 1.0,
                 done=True, error=True)
        record_run("rebuild", "error", t0, "dbt build failed")
        return

    with engine.connect() as conn:
        rows = conn.execute(
            text("select count(*) from analytics.customer_features")
        ).scalar_one()
    total = round(time.perf_counter() - t0, 2)
    yield ev("done", f"Rebuilt {int(rows):,} gold rows in {total:.1f}s", 1.0,
             done=True, gold_rows=int(rows), total_seconds=total)
    record_run("rebuild", "success", t0, f"{int(rows):,} gold rows · 26 dbt nodes")
