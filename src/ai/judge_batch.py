"""Run the LLM-as-judge against generated retention emails, persist the full
structured grade to ``serving.eval_scores``.

Two entry points:

- ``grade_unjudged_emails(limit, concurrency)`` — the high-level pipeline step.
  Pulls the most recent emails that don't yet have a judge grade, derives
  per-customer success criteria from each customer's SHAP profile, judges them
  in parallel, and writes the structured grade (including reasoning,
  weaknesses, clauses_evaluated, certainty) back to the warehouse.
- ``derive_success_criteria(customer_input)`` — exposed for tests; turns the
  generator input into the prose ``success_criteria`` the judge expects.

The judge methodology requires per-case ``success_criteria``. In production we
don't ship hand-written criteria per customer — they're synthesised from the
customer's risk tier and SHAP profile, mirroring the same rules the generator
follows.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

import anthropic
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

from ai.grader import GRADER_SYSTEM_BLOCKS
from ai.tools_schema import GRADER_OUTPUT_CONFIG
from backend.db.session import engine

load_dotenv()

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_CONCURRENCY = 6
DEFAULT_LIMIT = 200
PASS_THRESHOLD = 7.0

# --- Per-customer success-criteria synthesis ---------------------------------

SERVICE_FAILURE_FEATURES = {"avg_review_score", "avg_delivery_days"}
PRICE_FEATURES = {"avg_freight_value", "monetary_total", "monetary_avg"}
RECENCY_FEATURES = {"recency_days", "order_interval_mean", "order_interval_median"}


def _top_positive(shap_factors: list[dict]) -> dict | None:
    pos = [f for f in shap_factors if (f.get("shap_value") or 0) > 0]
    if not pos:
        return None
    return max(pos, key=lambda f: f["shap_value"])


def _has_strong_protective(shap_factors: list[dict]) -> bool:
    return any(
        f.get("feature_name") in ("frequency", "avg_review_score")
        and (f.get("shap_value") or 0) <= -0.10
        for f in shap_factors
    )


def _is_weak_signal(shap_factors: list[dict], risk_tier: str) -> bool:
    if risk_tier not in ("low", "medium"):
        return False
    top = _top_positive(shap_factors)
    if top is None:
        return True
    return top["shap_value"] < 0.15


def derive_success_criteria(customer_input: dict) -> str:
    """Synthesise the judge's per-customer success_criteria from a generator input.

    The clauses mirror the rules in ``RETENTION_EMAIL_SYSTEM_PROMPT`` — the
    judge applies the same rules the generator was given.
    """
    risk_tier = customer_input.get("risk_tier") or "medium"
    shap_factors = customer_input.get("shap_factors") or []
    top = _top_positive(shap_factors)
    top_feature = top["feature_name"] if top else None

    is_service_failure = top_feature in SERVICE_FAILURE_FEATURES
    is_price_signal = top_feature in PRICE_FEATURES
    is_recency_driven = top_feature in RECENCY_FEATURES
    has_strong_history = _has_strong_protective(shap_factors)
    weak_signal = _is_weak_signal(shap_factors, risk_tier)

    clauses: list[str] = []

    if is_service_failure:
        clauses += [
            "Tone MUST be 'acknowledging'",
            "includes_offer MUST be false (an offer would read as bribery for service failures)",
            "call_to_action.intent MUST be 'support'",
            f"Body MUST acknowledge the specific failure surfaced by SHAP ({top_feature})",
        ]
    elif weak_signal:
        clauses += [
            "Tone MUST be 'neutral' (signals are weak)",
            "includes_offer MUST be false (weak signal does not justify discounting)",
            "call_to_action.intent should be 'browse' or 'feedback' (not 'redeem', not 'support')",
            "reasoning MUST acknowledge that signals were weak rather than constructing a narrative",
        ]
    elif is_price_signal:
        clauses += [
            "Tone should be 'reassuring' or 'appreciative'",
            "includes_offer SHOULD be true (price/freight is offer-addressable)",
            "If includes_offer is true, call_to_action.intent MUST be 'redeem'",
            "Offer MUST use the {{offer_detail}} placeholder; no invented discount specifics",
        ]
    elif is_recency_driven and has_strong_history:
        clauses += [
            "Tone should be 'appreciative' (lapsed but happy)",
            "includes_offer SHOULD be true",
            "If includes_offer is true, call_to_action.intent MUST be 'redeem'",
            "Body should reference the customer's order history concretely",
        ]
    elif is_recency_driven:
        clauses += [
            "Tone should be 'reassuring' or 'neutral'",
            "If includes_offer is true, call_to_action.intent MUST be 'redeem'",
            "Body should avoid the 'we miss you' framing",
        ]
    else:
        # Generic fallback — still apply the universal CTA/tone constraints.
        clauses += [
            "Tone should match SHAP profile (neutral/reassuring/appreciative)",
            "If includes_offer is true, call_to_action.intent MUST be 'redeem'",
        ]

    # Universal clauses applied to every grade.
    clauses += [
        "Body MUST NOT use prohibited phrases ('we miss you', 'come back', 'it's been a while', 'we'd love to have you back')",
        "Body MUST NOT mention churn, risk scores, probabilities, or that the customer was flagged",
        "Subject line should anchor to a specific signal (number, delivery delay, category) and avoid generic transactional-confirmation framing",
        "Body should round day counts to integers (e.g., '13 days', not '12.56 days')",
        "Sign-off MUST be the exact string 'The Hatch Brand Team' (no '{{brand}}', no '[Brand]')",
    ]
    if top_feature:
        clauses.append(
            f"grounding.shap_factors_addressed MUST include the top positive SHAP factor "
            f"({top_feature})"
        )

    return ". ".join(clauses) + "."


# --- Async judge fan-out -----------------------------------------------------

def _load_unjudged_emails(limit: int) -> list[dict]:
    """Most recent generated emails that don't yet have a judge grade."""
    sql = text(
        """
        SELECT e.id            AS email_id,
               e.subject,
               e.body,
               e.model         AS generator_model,
               e.generated_at,
               p.id            AS prediction_id,
               p.customer_unique_id,
               p.churn_probability,
               p.threshold,
               cf.frequency,
               cf.recency_days,
               cf.tenure_days,
               cf.monetary_total,
               cf.monetary_avg,
               cf.avg_review_score,
               cf.avg_delivery_days,
               cf.customer_state
          FROM serving.generated_emails e
          JOIN serving.predictions p ON p.id = e.prediction_id
          LEFT JOIN analytics.customer_features cf
            ON cf.customer_unique_id = p.customer_unique_id
           AND cf.snapshot_date      = p.snapshot_date
         WHERE NOT EXISTS (
           SELECT 1 FROM serving.eval_scores s WHERE s.email_id = e.id
         )
         ORDER BY e.generated_at DESC
         LIMIT :limit
        """
    )
    shap_sql = text(
        """
        SELECT prediction_id, feature_name, feature_value, shap_value, rank
          FROM serving.shap_values
         WHERE prediction_id = ANY(:pids)
         ORDER BY prediction_id, rank
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": int(limit)}).mappings().all()
        if not rows:
            return []
        pids = [r["prediction_id"] for r in rows]
        shap_rows = conn.execute(shap_sql, {"pids": pids}).mappings().all()

    by_pid: dict[int, list[dict]] = {}
    for s in shap_rows:
        by_pid.setdefault(s["prediction_id"], []).append(
            {
                "feature_name": s["feature_name"],
                "feature_value": (
                    float(s["feature_value"]) if s["feature_value"] is not None else None
                ),
                "shap_value": float(s["shap_value"]),
                "rank": int(s["rank"]),
            }
        )

    out: list[dict] = []
    for r in rows:
        churn = float(r["churn_probability"])
        risk_tier = (
            "critical" if churn >= 0.85
            else "high" if churn >= 0.65
            else "medium" if churn >= float(r["threshold"] or 0.33)
            else "low"
        )
        context_fields = {
            "frequency": r["frequency"],
            "recency_days": r["recency_days"],
            "tenure_days": r["tenure_days"],
            "monetary_total": r["monetary_total"],
            "monetary_avg": r["monetary_avg"],
            "avg_review_score": r["avg_review_score"],
            "avg_delivery_days": r["avg_delivery_days"],
            "customer_state": r["customer_state"],
        }
        context = {
            k: (float(v) if hasattr(v, "__float__") else v)
            for k, v in context_fields.items()
            if v is not None
        }
        customer_input = {
            "customer_id": r["customer_unique_id"],
            "churn_probability": round(churn, 4),
            "risk_tier": risk_tier,
            "shap_factors": (by_pid.get(r["prediction_id"]) or [])[:5],
            "customer_context": context,
        }
        out.append(
            {
                "email_id": int(r["email_id"]),
                "customer_input": customer_input,
                "generated_email": {
                    "subject": r["subject"] or "",
                    "body": r["body"] or "",
                    "model": r["generator_model"],
                },
            }
        )
    return out


def _payload(email_row: dict) -> dict:
    return {
        "test_case_name": f"prod_email_{email_row['email_id']}",
        "success_criteria": derive_success_criteria(email_row["customer_input"]),
        "customer_input": email_row["customer_input"],
        "generated_email": email_row["generated_email"],
        "tool_calls": [],
    }


async def _grade_one(
    client: anthropic.AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    email_row: dict,
    model: str,
) -> tuple[dict, dict | None, Exception | None]:
    payload = _payload(email_row)
    user_msg = (
        "Adversarial-review mode. Default score is 6; competent baseline is 7. "
        "Anything above 7 requires at least three distinct active strengths cited in `reasoning`.\n\n"
        "Return JSON per the schema, no prose outside.\n\n"
        "INPUT:\n" + json.dumps(payload)
    )
    t0 = time.perf_counter()
    async with semaphore:
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=0.0,
                system=GRADER_SYSTEM_BLOCKS,
                output_config=GRADER_OUTPUT_CONFIG,
                messages=[{"role": "user", "content": user_msg}],
            )
            text_out = "\n".join(b.text for b in response.content if b.type == "text")
            grade = json.loads(text_out)
            grade["_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return email_row, grade, None
        except Exception as e:
            return email_row, None, e


async def _gather_grades(
    rows: list[dict], concurrency: int, model: str
) -> list[tuple[dict, dict | None, Exception | None]]:
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(concurrency)
    try:
        return await asyncio.gather(
            *(_grade_one(client, semaphore, r, model) for r in rows)
        )
    finally:
        await client.close()


def _persist(rows: list[dict]) -> int:
    """Write the structured grades to ``serving.eval_scores``."""
    if not rows:
        return 0
    pd.DataFrame(rows).to_sql(
        "eval_scores",
        engine,
        schema="serving",
        if_exists="append",
        index=False,
    )
    return len(rows)


def grade_unjudged_emails(
    limit: int = DEFAULT_LIMIT,
    concurrency: int = DEFAULT_CONCURRENCY,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Grade up to ``limit`` recent generated emails that don't yet have a grade."""
    t0 = time.perf_counter()
    rows = _load_unjudged_emails(limit)
    if not rows:
        return {
            "graded": 0,
            "failed": 0,
            "requested": limit,
            "elapsed_seconds": 0.0,
            "model": model,
        }

    results = asyncio.run(_gather_grades(rows, concurrency, model))

    persist_rows: list[dict] = []
    failed = 0
    now = datetime.now(timezone.utc)
    for email_row, grade, err in results:
        if grade is None or err is not None:
            failed += 1
            continue
        overall = float(grade.get("score", 0))
        persist_rows.append(
            {
                "email_id": int(email_row["email_id"]),
                "evaluator": "llm_judge",
                "overall_score": overall,
                "passed": overall >= PASS_THRESHOLD,
                "judge_model": model,
                "latency_ms": grade.get("_latency_ms"),
                "certainty": grade.get("certainty"),
                "reasoning": grade.get("reasoning"),
                "weaknesses": json.dumps(grade.get("weaknesses") or []),
                "clauses_evaluated": json.dumps(grade.get("clauses_evaluated") or []),
                "created_at": now,
                "updated_at": now,
            }
        )

    written = _persist(persist_rows)
    return {
        "graded": written,
        "failed": failed,
        "requested": limit,
        "concurrency": concurrency,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "model": model,
    }


if __name__ == "__main__":
    summary = grade_unjudged_emails()
    print(json.dumps(summary, indent=2))
