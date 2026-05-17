"""Lightweight run log — records pipeline rebuilds and scoring runs so the
dashboard's Runs view has real history. Stored as JSON (local runtime state,
gitignored under data/).
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNS_FILE = REPO_ROOT / "data" / "runs.json"
MAX_RUNS = 50


def _load() -> list[dict]:
    if not RUNS_FILE.exists():
        return []
    try:
        return json.loads(RUNS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def record_run(kind: str, status: str, started: float, detail: str) -> None:
    """Append a run record.

    ``started`` is the ``time.perf_counter()`` value captured when the run
    began; the duration is computed from now.
    """
    record = {
        "id": "run-" + uuid.uuid4().hex[:8],
        "kind": kind,
        "status": status,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(time.perf_counter() - started, 1),
        "detail": detail,
    }
    runs = [record, *_load()][:MAX_RUNS]
    RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNS_FILE.write_text(json.dumps(runs, indent=1))


def recent_runs(limit: int = 15) -> dict:
    """Return the most recent run records."""
    return {"runs": _load()[:limit]}
