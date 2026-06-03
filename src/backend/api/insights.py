"""LLM-as-judge insights — aggregate + per-email views over ``serving.eval_scores``.

The judge persists a structured grade per email (overall_score, certainty,
reasoning, weaknesses, clauses_evaluated). This module rolls those rows into
two shapes the dashboard consumes:

- ``judge_insights()`` — aggregate stats (score histogram, certainty,
  pass-rate, clause verdicts, top recurring weaknesses).
- ``judge_grades()``  — per-email rows joined with the email + customer.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Iterable

from sqlalchemy import text

from ..db.session import engine
from ..domain.tiers import risk_tier_short


def _to_list(value: Any) -> list[Any]:
    """JSONB may come back as native list or as JSON-encoded text."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
    return []


_STOPWORDS = {
    "the", "a", "an", "to", "for", "of", "in", "on", "is", "as", "and", "or",
    "but", "with", "without", "that", "this", "these", "those", "be", "been",
    "are", "was", "were", "has", "have", "had", "do", "does", "did", "not",
    "no", "yes", "it", "its", "their", "them", "they", "you", "your",
}
_TOKEN_RE = re.compile(r"[a-zA-Z']{3,}")


def _key_phrases(text_value: str) -> list[str]:
    """Cheap content-word tokenisation used to cluster recurring weaknesses."""
    return [
        word.lower()
        for word in _TOKEN_RE.findall(text_value)
        if word.lower() not in _STOPWORDS
    ]


def judge_insights() -> dict:
    """Aggregate the judge's grades across all currently-scored emails."""
    summary_sql = text(
        """
        SELECT COUNT(*)                                AS total,
               AVG(overall_score)                      AS avg_score,
               MIN(overall_score)                      AS min_score,
               MAX(overall_score)                      AS max_score,
               STDDEV_POP(overall_score)               AS stddev_score,
               AVG(certainty)                          AS avg_certainty,
               AVG(CASE WHEN passed THEN 1.0 ELSE 0.0 END) AS pass_rate,
               MAX(created_at)                         AS latest_at,
               MAX(judge_model)                        AS judge_model
          FROM serving.eval_scores
        """
    )
    histo_sql = text(
        """
        SELECT FLOOR(overall_score)::int AS bucket, COUNT(*) AS n
          FROM serving.eval_scores
         GROUP BY 1
         ORDER BY 1
        """
    )
    rows_sql = text(
        """
        SELECT weaknesses, clauses_evaluated, overall_score
          FROM serving.eval_scores
         WHERE weaknesses IS NOT NULL OR clauses_evaluated IS NOT NULL
        """
    )

    with engine.connect() as conn:
        summary = conn.execute(summary_sql).mappings().one()
        if int(summary["total"] or 0) == 0:
            return {
                "available": False,
                "total": 0,
                "judge_model": None,
                "latest_at": None,
            }
        histogram_rows = conn.execute(histo_sql).mappings().all()
        rows = conn.execute(rows_sql).mappings().all()

    # Roll up clause verdicts and weaknesses across every graded email.
    verdict_counts: Counter[str] = Counter()
    clause_text_by_verdict: dict[str, Counter[str]] = {
        "met": Counter(),
        "partially_met": Counter(),
        "not_met": Counter(),
        "not_assessable": Counter(),
    }
    weakness_corpus: list[str] = []

    for r in rows:
        for w in _to_list(r["weaknesses"]):
            if isinstance(w, str) and w.strip():
                weakness_corpus.append(w.strip())

        for c in _to_list(r["clauses_evaluated"]):
            if not isinstance(c, dict):
                continue
            verdict = (c.get("verdict") or "").lower()
            clause = (c.get("clause") or "").strip()
            if verdict in verdict_counts or verdict in clause_text_by_verdict:
                verdict_counts[verdict] += 1
                clause_text_by_verdict[verdict][clause[:140]] += 1
            elif verdict:
                verdict_counts[verdict] += 1

    # Cluster recurring weakness phrases by their content words. The cheap
    # n-gram approach is enough to surface the top complaints — "subject line",
    # "[brand] placeholder", "generic CTA", etc. — without an embedding pass.
    phrase_counts: Counter[str] = Counter()
    for snippet in weakness_corpus:
        words = _key_phrases(snippet)
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i : i + n])
                phrase_counts[phrase] += 1

    # Filter to phrases that appear in at least ~5% of weaknesses (or twice,
    # whichever is larger) so we don't surface noise. Also drop bigrams that
    # are subphrases of a more common trigram with the same count.
    min_count = max(2, int(len(weakness_corpus) * 0.05) or 2)
    candidates = [
        (phrase, count)
        for phrase, count in phrase_counts.items()
        if count >= min_count
    ]
    candidates.sort(key=lambda pc: (-pc[1], pc[0]))
    seen_in_trigram: set[str] = set()
    for phrase, count in candidates:
        if phrase.count(" ") == 2:
            tokens = phrase.split()
            seen_in_trigram.add(f"{tokens[0]} {tokens[1]}")
            seen_in_trigram.add(f"{tokens[1]} {tokens[2]}")
    deduped = [
        (phrase, count)
        for phrase, count in candidates
        if phrase.count(" ") == 2 or phrase not in seen_in_trigram
    ][:12]

    # Sample concrete weakness quotes for the page's right column.
    sample_quotes = weakness_corpus[:20]

    histogram = [
        {"bucket": int(h["bucket"]), "count": int(h["n"])} for h in histogram_rows
    ]
    return {
        "available": True,
        "total": int(summary["total"]),
        "avg_score": round(float(summary["avg_score"]), 2),
        "min_score": float(summary["min_score"]),
        "max_score": float(summary["max_score"]),
        "stddev_score": round(float(summary["stddev_score"] or 0.0), 2),
        "avg_certainty": round(float(summary["avg_certainty"] or 0.0), 2),
        "pass_rate": round(float(summary["pass_rate"] or 0.0), 3),
        "latest_at": summary["latest_at"].isoformat() if summary["latest_at"] else None,
        "judge_model": summary["judge_model"],
        "score_histogram": histogram,
        "clause_verdicts": {
            k: verdict_counts.get(k, 0)
            for k in ("met", "partially_met", "not_met", "not_assessable")
        },
        "top_clauses_partial": [
            {"clause": c, "count": n}
            for c, n in clause_text_by_verdict["partially_met"].most_common(8)
        ],
        "top_clauses_not_met": [
            {"clause": c, "count": n}
            for c, n in clause_text_by_verdict["not_met"].most_common(8)
        ],
        "top_weakness_phrases": [
            {"phrase": phrase, "count": int(count)} for phrase, count in deduped
        ],
        "weakness_samples": sample_quotes,
    }


def judge_grades(limit: int = 50) -> dict:
    """Per-email judge output joined with the email + customer."""
    sql = text(
        """
        SELECT s.id              AS grade_id,
               s.email_id,
               s.overall_score,
               s.certainty,
               s.passed,
               s.reasoning,
               s.weaknesses,
               s.clauses_evaluated,
               s.judge_model,
               s.latency_ms,
               s.created_at,
               e.subject,
               e.body,
               e.model           AS generator_model,
               p.id              AS prediction_id,
               p.customer_unique_id,
               p.churn_probability,
               p.threshold,
               dn.display_name
          FROM serving.eval_scores s
          JOIN serving.generated_emails e ON e.id = s.email_id
          LEFT JOIN serving.predictions p ON p.id = e.prediction_id
          LEFT JOIN serving.customer_display_names dn
            ON dn.customer_unique_id = p.customer_unique_id
         ORDER BY s.created_at DESC
         LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": int(limit)}).mappings().all()

    grades = []
    for r in rows:
        risk = float(r["churn_probability"]) if r["churn_probability"] is not None else None
        threshold = float(r["threshold"]) if r["threshold"] is not None else None
        tier = risk_tier_short(risk, threshold)
        grades.append(
            {
                "grade_id": int(r["grade_id"]),
                "email_id": int(r["email_id"]),
                "customer_unique_id": r["customer_unique_id"],
                "display_name": r["display_name"]
                or (
                    f"Customer {r['customer_unique_id'][:8].upper()}"
                    if r["customer_unique_id"]
                    else "—"
                ),
                "subject": r["subject"] or "",
                "body": r["body"] or "",
                "generator_model": r["generator_model"],
                "judge_model": r["judge_model"],
                "overall_score": float(r["overall_score"]) if r["overall_score"] is not None else None,
                "certainty": float(r["certainty"]) if r["certainty"] is not None else None,
                "passed": bool(r["passed"]) if r["passed"] is not None else None,
                "reasoning": r["reasoning"] or "",
                "weaknesses": _to_list(r["weaknesses"]),
                "clauses_evaluated": _to_list(r["clauses_evaluated"]),
                "churn_probability": round(risk, 4) if risk is not None else None,
                "risk_tier": tier,
                "graded_at": r["created_at"].isoformat() if r["created_at"] else None,
                "latency_ms": float(r["latency_ms"]) if r["latency_ms"] is not None else None,
            }
        )

    return {"grades": grades, "total": len(grades)}
