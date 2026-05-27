"""Recent retention-email drafts — backs the dashboard's email-outreach card.

Joins ``serving.generated_emails`` with the originating ``serving.predictions``
row so each draft carries its target customer's churn probability and the
risk-tier the model assigned. If a corresponding ``serving.eval_scores`` row
exists, the LLM-judge grade rides along too.
"""

from __future__ import annotations

from sqlalchemy import text

from ..db.session import engine


def _tier(risk: float | None, threshold: float | None) -> str:
    if risk is None:
        return "low"
    if risk >= 0.85:
        return "crit"
    if risk >= 0.65:
        return "high"
    if threshold is not None and risk >= threshold:
        return "med"
    return "low"


def recent_emails(limit: int = 20) -> dict:
    sql = text(
        """
        SELECT e.id,
               e.subject,
               e.body,
               e.model,
               e.status,
               e.generated_at,
               p.id           AS prediction_id,
               p.customer_unique_id,
               p.churn_probability,
               p.threshold,
               p.model_version,
               dn.display_name,
               s.overall_score AS judge_score,
               s.passed        AS judge_passed
          FROM serving.generated_emails e
          LEFT JOIN serving.predictions p ON p.id = e.prediction_id
          LEFT JOIN serving.customer_display_names dn
            ON dn.customer_unique_id = p.customer_unique_id
          LEFT JOIN LATERAL (
            SELECT overall_score, passed
              FROM serving.eval_scores
             WHERE email_id = e.id
             ORDER BY created_at DESC
             LIMIT 1
          ) s ON TRUE
         ORDER BY e.generated_at DESC
         LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": int(limit)}).mappings().all()
        total = conn.execute(text("SELECT COUNT(*) FROM serving.generated_emails")).scalar_one()

    emails = []
    for r in rows:
        risk = float(r["churn_probability"]) if r["churn_probability"] is not None else None
        threshold = float(r["threshold"]) if r["threshold"] is not None else None
        emails.append(
            {
                "id": int(r["id"]),
                "customer_unique_id": r["customer_unique_id"],
                "display_name": r["display_name"]
                or (
                    f"Customer {r['customer_unique_id'][:8].upper()}"
                    if r["customer_unique_id"]
                    else "—"
                ),
                "subject": r["subject"] or "",
                "preview": (r["body"] or "").split("\n\n", 1)[0][:280],
                "model": r["model"],
                "status": r["status"] or "draft",
                "generated_at": r["generated_at"].isoformat() if r["generated_at"] else None,
                "churn_probability": round(risk, 4) if risk is not None else None,
                "risk_tier": _tier(risk, threshold),
                "judge_score": (
                    round(float(r["judge_score"]), 2) if r["judge_score"] is not None else None
                ),
                "judge_passed": bool(r["judge_passed"]) if r["judge_passed"] is not None else None,
            }
        )

    return {"emails": emails, "total": int(total or 0)}
