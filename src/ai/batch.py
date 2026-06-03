"""Async parallel batch generation of retention emails for the top-N at-risk
customers.

Two entry points:

- ``generate_top_n_emails(top_n, concurrency)`` — the high-level pipeline step.
  Pulls the top-N predictions from ``serving.predictions``, builds each
  customer payload from ``serving.shap_values`` + ``analytics.customer_features``,
  generates emails concurrently with bounded async fan-out, and writes them to
  ``serving.generated_emails``. Returns a summary dict.
- ``create_batch(customer_inputs)`` — the lower-level building block. Takes a
  list of customer payloads (already shaped for the system prompt) and returns
  ``(emails, tool_logs)`` after a bounded ``asyncio.gather`` over
  ``AsyncAnthropic``.

The Dagster ``retention_emails`` asset calls ``generate_top_n_emails``.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from datetime import datetime, timezone

import anthropic
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from ai.claude import RETENTION_EMAIL_SYSTEM_BLOCKS
from ai.config import DEFAULT_MODEL
from ai.tools import run_tool
from ai.tools_schema import FORMAT_RESPONSE_OUTPUT_CONFIG, TOOL_SCHEMAS
from backend.db.session import engine
from backend.domain.tiers import risk_tier

load_dotenv()

DEFAULT_TOP_N = 500
DEFAULT_CONCURRENCY = 8
MAX_TOOL_TURNS = 10


# --- DB shaping ---------------------------------------------------------

def _load_top_n_payloads(top_n: int) -> list[tuple[int, dict]]:
    """Build the customer payload for the top-N at-risk predictions.

    Returns ``[(prediction_id, customer_input), ...]`` ordered by churn
    probability DESC. The prediction id is kept so the generated email can be
    foreign-keyed back when written.
    """
    sql = text(
        """
        SELECT p.id AS prediction_id,
               p.customer_unique_id,
               p.churn_probability,
               p.snapshot_date,
               cf.*
          FROM serving.predictions p
          JOIN analytics.customer_features cf
            ON cf.customer_unique_id = p.customer_unique_id
           AND cf.snapshot_date = p.snapshot_date
         ORDER BY p.churn_probability DESC
         LIMIT :n
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"n": int(top_n)}).mappings().all()
        if not rows:
            return []

        prediction_ids = [r["prediction_id"] for r in rows]
        shap_sql = text(
            """
            SELECT prediction_id, feature_name, feature_value, shap_value, rank
              FROM serving.shap_values
             WHERE prediction_id = ANY(:ids)
             ORDER BY prediction_id, rank
            """
        )
        shap_rows = conn.execute(shap_sql, {"ids": prediction_ids}).mappings().all()

    shap_by_pred: dict[int, list[dict]] = {}
    for s in shap_rows:
        shap_by_pred.setdefault(s["prediction_id"], []).append({
            "feature_name": s["feature_name"],
            "feature_value": (
                float(s["feature_value"]) if s["feature_value"] is not None else None
            ),
            "shap_value": float(s["shap_value"]),
            "rank": int(s["rank"]),
        })

    # Subset of customer_features columns surfaced as customer_context. These
    # mirror the keys the system prompt and grader expect.
    CONTEXT_COLS = (
        "frequency",
        "recency_days",
        "tenure_days",
        "monetary_total",
        "monetary_avg",
        "avg_review_score",
        "avg_delivery_days",
        "customer_state",
    )

    payloads: list[tuple[int, dict]] = []
    for r in rows:
        proba = float(r["churn_probability"])
        shap_factors = shap_by_pred.get(r["prediction_id"], [])[:5]
        ctx = {}
        for col in CONTEXT_COLS:
            if col in r and r[col] is not None:
                val = r[col]
                ctx[col] = float(val) if isinstance(val, (int, float)) or hasattr(val, "__float__") else val
        # frequency aliases to order_count for the prompt's wording.
        if "frequency" in ctx:
            ctx["order_count"] = int(ctx.pop("frequency"))

        payloads.append((
            int(r["prediction_id"]),
            {
                "customer_id": r["customer_unique_id"],
                "churn_probability": round(proba, 4),
                "risk_tier": risk_tier(proba),
                "shap_factors": shap_factors,
                "customer_context": ctx,
            },
        ))
    return payloads


def _persist_emails(rows: list[dict]) -> int:
    """Write generated emails to ``serving.generated_emails``."""
    if not rows:
        return 0
    pd.DataFrame(rows).to_sql(
        "generated_emails",
        engine,
        schema="serving",
        if_exists="append",
        index=False,
    )
    return len(rows)


# --- Async Claude --------------------------------------------------------

def _user_prompt(customer_input: dict) -> str:
    return (
        "Generate a retention email for the customer below. Return the structured "
        "JSON output exactly per the schema.\n\n"
        "INPUT:\n" + json.dumps(customer_input)
    )


async def _run_tools_async(message: anthropic.types.Message) -> list[dict]:
    """Execute every tool_use block on the message off the event loop."""
    requests = [b for b in message.content if b.type == "tool_use"]
    if not requests:
        return []

    def _run_sync() -> list[dict]:
        out: list[dict] = []
        for req in requests:
            try:
                payload = run_tool(req.name, req.input)
                out.append({
                    "type": "tool_result",
                    "tool_use_id": req.id,
                    "content": json.dumps(payload),
                    "is_error": False,
                })
            except Exception as e:
                out.append({
                    "type": "tool_result",
                    "tool_use_id": req.id,
                    "content": f"Error: {e}",
                    "is_error": True,
                })
        return out

    return await asyncio.to_thread(_run_sync)


async def _generate_one(
    client: anthropic.AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    customer_input: dict,
    model: str,
) -> tuple[dict | None, list[dict], Exception | None]:
    """One full tool-loop generation for one customer."""
    messages: list[dict] = [{"role": "user", "content": _user_prompt(customer_input)}]
    tool_log: list[dict] = []
    pending: dict[str, dict] = {}

    async with semaphore:
        try:
            for _ in range(MAX_TOOL_TURNS):
                response = await client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=0.0,
                    system=RETENTION_EMAIL_SYSTEM_BLOCKS,
                    tools=TOOL_SCHEMAS,
                    output_config=FORMAT_RESPONSE_OUTPUT_CONFIG,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    text_out = "\n".join(
                        b.text for b in response.content if b.type == "text"
                    )
                    return json.loads(text_out), tool_log, None

                for block in response.content:
                    if block.type == "tool_use":
                        pending[block.id] = {"name": block.name, "input": block.input}

                tool_results = await _run_tools_async(response)
                for tr in tool_results:
                    entry = pending.pop(tr["tool_use_id"], None)
                    if entry is not None:
                        entry["output"] = tr["content"]
                        tool_log.append(entry)
                messages.append({"role": "user", "content": tool_results})

            return None, tool_log, RuntimeError(
                f"exceeded MAX_TOOL_TURNS={MAX_TOOL_TURNS}"
            )
        except Exception as e:
            return None, tool_log, e


async def _gather_emails(
    customer_inputs: list[dict],
    concurrency: int,
    model: str,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[tuple[dict | None, list[dict], Exception | None]]:
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(concurrency)
    total = len(customer_inputs)
    completed = 0
    lock = asyncio.Lock()

    async def _tracked(payload: dict):
        nonlocal completed
        result = await _generate_one(client, semaphore, payload, model)
        if progress_cb is not None:
            async with lock:
                completed += 1
                done = completed
            progress_cb(done, total)
        return result

    try:
        # gather preserves input order regardless of completion order, so the
        # returned list still aligns with the caller's prediction ids.
        return await asyncio.gather(*(_tracked(p) for p in customer_inputs))
    finally:
        await client.close()


def create_batch(
    customer_inputs: list[dict],
    concurrency: int = DEFAULT_CONCURRENCY,
    model: str = DEFAULT_MODEL,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[tuple[dict | None, list[dict], Exception | None]]:
    """Generate emails for every payload concurrently and return per-customer results.

    Each result is ``(email_dict, tool_log, error)``. ``email_dict`` is None on
    failure; ``error`` carries the exception. Bounded by ``concurrency``.

    ``progress_cb(done, total)`` — if given, called once per customer as each
    generation completes, for live progress reporting.
    """
    return asyncio.run(
        _gather_emails(customer_inputs, concurrency, model, progress_cb)
    )


# --- High-level pipeline step --------------------------------------------

def generate_top_n_emails(
    top_n: int = DEFAULT_TOP_N,
    concurrency: int = DEFAULT_CONCURRENCY,
    model: str = DEFAULT_MODEL,
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict:
    """Generate retention emails for the top-N at-risk customers.

    Reads top-N from ``serving.predictions`` (by churn probability), generates
    one email per customer in parallel, persists them to
    ``serving.generated_emails``, and returns a summary.

    ``progress_cb(done, total)`` — if given, called once per customer as each
    email is generated, so callers (the dashboard SSE stream, the Dagster asset)
    can report live ``n/total`` progress.
    """
    t0 = time.perf_counter()
    payloads = _load_top_n_payloads(top_n)
    if not payloads:
        return {
            "generated": 0,
            "failed": 0,
            "top_n_requested": top_n,
            "elapsed_seconds": 0.0,
            "model": model,
        }

    prediction_ids, customer_inputs = zip(*payloads)
    results = create_batch(
        list(customer_inputs),
        concurrency=concurrency,
        model=model,
        progress_cb=progress_cb,
    )

    rows: list[dict] = []
    failed = 0
    now = datetime.now(timezone.utc)
    for pid, (email, tool_log, err) in zip(prediction_ids, results):
        if email is None or err is not None:
            failed += 1
            continue
        rows.append({
            "prediction_id": pid,
            "subject": email["subject"][:256],
            "body": email["body"],
            "model": model,
            "status": "draft",
            # Persist the generator's tool log so the judge receives the same
            # payload it gets on the test path — without it, tool-grounded
            # numbers look like fabrications and get capped at <=5.
            "tool_calls": json.dumps(tool_log or []),
            "generated_at": now,
        })

    written = _persist_emails(rows)
    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "generated": written,
        "failed": failed,
        "top_n_requested": top_n,
        "concurrency": concurrency,
        "elapsed_seconds": elapsed,
        "model": model,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate retention emails for the top-N at-risk customers."
    )
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    summary = generate_top_n_emails(
        top_n=args.top_n, concurrency=args.concurrency, model=args.model
    )
    print(json.dumps(summary, indent=2))
