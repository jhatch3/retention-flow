"""Timed pipeline rebuild — drop the `analytics` schema and re-run `dbt build`,
streaming a progress event per dbt node so the dashboard can time the run.

Also exposes the unified ``pipeline_events`` generator that drives the dashboard
"Run pipeline" button. It composes the rebuild, the (optional) model retrain,
the batch scoring, and the (optional) retention-email generation into one
event stream.
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from ..db.session import engine
from .runs import record_run

REPO_ROOT = Path(__file__).resolve().parents[3]
TRANSFORM_DIR = REPO_ROOT / "src" / "transform"

_NODE = re.compile(r"(\d+) of (\d+)")
_KEEP = (" OK ", " PASS ", " ERROR", " FAIL", "Completed successfully", "Done.")

DEFAULT_EMAIL_TOP_N = 50


def _phase_progress(
    run_fn: Callable[[Callable[[int, int], None]], dict],
    *,
    ev: Callable[..., dict],
    stage: str,
    floor: float,
    alloc: float,
    verb: str,
) -> Iterator[dict]:
    """Stream live ``n/total`` progress for a blocking batch step.

    ``run_fn`` is a callable that accepts a ``progress_cb(done, total)`` and
    returns a summary dict (e.g. ``generate_top_n_emails``). It runs in a worker
    thread; each ``progress_cb`` call is turned into an SSE event scaled into the
    phase's ``[floor, floor + alloc]`` slice of the overall progress bar.

    Yields events; the wrapped function's summary is the generator's return
    value — use ``summary = yield from _phase_progress(...)``.
    """
    q: queue.Queue = queue.Queue()
    box: dict = {}

    def cb(done: int, total: int) -> None:
        q.put((done, total))

    def worker() -> None:
        try:
            box["value"] = run_fn(cb)
        except Exception as exc:  # re-raised below, after the queue has drained
            box["error"] = exc
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = q.get()
        if item is None:
            break
        done, total = item
        frac = (done / total) if total else 1.0
        yield ev(
            stage,
            f"{verb} {done}/{total}…",
            floor + alloc * (0.1 + 0.85 * frac),
            phase=stage,
        )

    if "error" in box:
        raise box["error"]
    return box["value"]


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


def pipeline_events(
    *,
    train: bool = True,
    emails: bool = True,
    email_top_n: int = DEFAULT_EMAIL_TOP_N,
) -> Iterator[dict]:
    """Unified pipeline runner driving the dashboard "Run pipeline" button.

    Phases (each optional via the flags):
      1. dbt rebuild              (always)
      2. churn-model retrain      (if ``train``)
      3. batch scoring + SHAP     (always)
      4. retention emails         (if ``emails``)
      5. LLM-as-judge grading     (if ``emails`` — judges every new email)

    Yields SSE events for each phase. The final ``done`` event carries a
    summary report and the run is logged to ``serving.run_log``.
    """
    from .scoring import score_events

    t0 = time.perf_counter()
    report: dict = {}
    detail_parts: list[str] = ["dbt"]

    # Phase allocation across the [0, 1] progress range.
    #   dbt:    always — proportion shrinks as more phases are enabled
    #   train:  0.18 if enabled, else 0
    #   score:  always
    #   emails: 0.16 if enabled, else 0  (drafting)
    #   judge:  0.14 if enabled, else 0  (LLM-as-judge over drafts)
    train_alloc = 0.18 if train else 0.0
    emails_alloc = 0.16 if emails else 0.0
    judge_alloc = 0.14 if emails else 0.0
    if train and emails:
        score_alloc = 0.27
    elif train or emails:
        score_alloc = 0.34
    else:
        score_alloc = 0.55
    dbt_alloc = 1.0 - train_alloc - score_alloc - emails_alloc - judge_alloc

    def ev(stage: str, message: str, progress: float, **extra) -> dict:
        return {
            "stage": stage,
            "message": message,
            "progress": round(progress, 3),
            "elapsed": round(time.perf_counter() - t0, 1),
            "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            **extra,
        }

    yield ev("start", "Starting pipeline run", 0.01, phase="dbt")

    # Phase 1 — dbt rebuild
    for e in rebuild_events():
        if e.get("done"):
            if e.get("error"):
                yield ev("error", "Pipeline failed at the dbt build", 1.0,
                         done=True, error=True)
                record_run("pipeline", "error", t0, "dbt build failed")
                return
            report["dbt"] = {
                "gold_rows": e.get("gold_rows"),
                "seconds": e.get("total_seconds"),
            }
        else:
            yield {**e, "progress": round(e["progress"] * dbt_alloc, 3), "phase": "dbt"}

    progress_floor = dbt_alloc

    # Phase 2 — optional model retrain
    if train:
        from ..ml.train import train_and_log

        yield ev("train", "Training the churn model…", progress_floor + train_alloc * 0.1, phase="train")
        try:
            out = train_and_log(run_tags={"trigger": "dashboard-pipeline-run"})
        except Exception as exc:
            yield ev("error", f"Model training failed: {exc}", 1.0, done=True, error=True)
            record_run("pipeline", "error", t0, f"train failed: {exc}")
            return

        val = out["results"]["validation"]
        report["model"] = {
            "version": out["model_version"],
            "roc_auc": round(val["roc_auc"], 3),
            "pr_auc": round(val["pr_auc"], 3),
            "threshold": out["threshold"],
        }
        detail_parts.append("train")
        yield ev(
            "train",
            f"Registered {out['model_name']} v{out['model_version']} · "
            f"ROC-AUC {val['roc_auc']:.3f}",
            progress_floor + train_alloc,
            phase="train",
        )
        progress_floor += train_alloc

    # Phase 3 — batch scoring + SHAP with the current champion
    for e in score_events():
        if e.get("done"):
            report["scoring"] = e["result"]
            detail_parts.append("score")
        else:
            yield {
                **e,
                "progress": round(progress_floor + e["progress"] * score_alloc, 3),
                "phase": "score",
            }
    progress_floor += score_alloc

    # Phase 4 — optional email generation
    if emails:
        from ai.batch import generate_top_n_emails

        yield ev(
            "emails",
            f"Generating retention emails for the top {email_top_n} at-risk customers…",
            progress_floor + emails_alloc * 0.05,
            phase="emails",
        )
        try:
            summary = yield from _phase_progress(
                lambda cb: generate_top_n_emails(top_n=email_top_n, progress_cb=cb),
                ev=ev,
                stage="emails",
                floor=progress_floor,
                alloc=emails_alloc,
                verb="Drafted",
            )
        except Exception as exc:
            yield ev(
                "error",
                f"Email generation failed: {exc}",
                1.0,
                done=True,
                error=True,
            )
            record_run("pipeline", "error", t0, f"email generation failed: {exc}")
            return

        report["emails"] = summary
        detail_parts.append("emails")
        yield ev(
            "emails",
            f"Generated {summary['generated']} emails · "
            f"{summary['failed']} failed · {summary['elapsed_seconds']}s",
            progress_floor + emails_alloc,
            phase="emails",
        )
        progress_floor += emails_alloc

        # Phase 5 — LLM-as-judge grading of every email that doesn't yet have
        # a grade. Persists reasoning + weaknesses + clause-verdicts to
        # serving.eval_scores so the dashboard's Insights page can visualise.
        from ai.judge_batch import grade_unjudged_emails

        yield ev(
            "judge",
            "Judging generated emails with the adversarial rubric…",
            progress_floor + judge_alloc * 0.05,
            phase="judge",
        )
        try:
            judge_limit = max(email_top_n, summary.get("generated", 0) or email_top_n)
            judge_summary = yield from _phase_progress(
                lambda cb: grade_unjudged_emails(limit=judge_limit, progress_cb=cb),
                ev=ev,
                stage="judge",
                floor=progress_floor,
                alloc=judge_alloc,
                verb="Judged",
            )
        except Exception as exc:
            yield ev(
                "error",
                f"Email judging failed: {exc}",
                1.0,
                done=True,
                error=True,
            )
            record_run("pipeline", "error", t0, f"judge failed: {exc}")
            return

        report["judge"] = judge_summary
        detail_parts.append("judge")
        yield ev(
            "judge",
            f"Judged {judge_summary['graded']} emails · "
            f"{judge_summary['failed']} failed · "
            f"{judge_summary['elapsed_seconds']}s",
            progress_floor + judge_alloc,
            phase="judge",
        )
        progress_floor += judge_alloc

    total = round(time.perf_counter() - t0, 1)
    report["total_seconds"] = total
    yield ev(
        "done",
        f"Pipeline complete in {total:.0f}s",
        1.0,
        done=True,
        phase="judge" if emails else "score",
        report=report,
    )
    record_run(
        "pipeline",
        "success",
        t0,
        f"{' + '.join(detail_parts)} · {total:.0f}s",
    )


# Back-compat wrappers — older callers / tests still expect these names.

def full_pipeline_events() -> Iterator[dict]:
    """Run the full pipeline — dbt rebuild → train → score (no emails)."""
    yield from pipeline_events(train=True, emails=False)


def quick_pipeline_events() -> Iterator[dict]:
    """Run the pipeline without retraining — dbt rebuild → score."""
    yield from pipeline_events(train=False, emails=False)
