from datetime import datetime

from src.ai.claude import generate_email
from src.ai.grader import grade_email
from src.ai.prompts.test_dataset import TEST_CASES


def _verdict_counts(clauses):
    counts = {"met": 0, "partially_met": 0, "not_met": 0, "not_assessable": 0}
    for c in clauses:
        v = c.get("verdict", "not_assessable")
        counts[v] = counts.get(v, 0) + 1
    return counts


if __name__ == "__main__":
    overall_start = datetime.now()
    results = []

    for i, case in enumerate(TEST_CASES, start=1):
        print(f"\n=== Test case {i}/{len(TEST_CASES)}: {case['name']} ===")
        case_start = datetime.now()

        email, tool_calls = generate_email(case["input"])
        grade = grade_email(case, email, tool_calls=tool_calls)

        elapsed = datetime.now() - case_start
        v = _verdict_counts(grade["clauses_evaluated"])

        print(f"Subject:    {email['subject']}")
        print(f"Tone:       {email['tone']}    Offer: {email['includes_offer']}    "
              f"CTA: {email['call_to_action']['intent']} ({email['call_to_action']['text']})")
        print(f"Tools used: {len(tool_calls)} "
              + (", ".join(tc["name"] for tc in tool_calls) if tool_calls else "(none)"))
        print(f"Score:      {grade['score']:.1f}/10   (certainty: {grade['certainty']:.2f})")
        print(f"Clauses:    {v['met']} met, {v['partially_met']} partial, "
              f"{v['not_met']} missed, {v['not_assessable']} n/a")
        print(f"Weaknesses:")
        for w in grade["weaknesses"]:
            print(f"  - {w}")
        print(f"Reasoning:  {grade['reasoning']}")
        print(f"Elapsed:    {elapsed}")

        results.append(
            {
                "name": case["name"],
                "score": grade["score"],
                "certainty": grade["certainty"],
                "verdicts": v,
                "tool_call_count": len(tool_calls),
            }
        )

    overall_elapsed = datetime.now() - overall_start

    print("\n=== Summary ===")
    print(f"{'Test case':<40} {'Score':>6} {'Cert.':>6} {'tools':>6} {'met':>5} {'part':>5} {'miss':>5}")
    print("-" * 78)
    for r in results:
        print(
            f"{r['name']:<40} "
            f"{r['score']:>6.1f} "
            f"{r['certainty']:>6.2f} "
            f"{r['tool_call_count']:>6} "
            f"{r['verdicts']['met']:>5} "
            f"{r['verdicts']['partially_met']:>5} "
            f"{r['verdicts']['not_met']:>5}"
        )

    scores = [r["score"] for r in results]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    score_min = min(scores) if scores else 0.0
    score_max = max(scores) if scores else 0.0
    print("-" * 78)
    print(f"{'Mean':<40} {mean_score:>6.2f}")
    print(f"{'Range':<40} {score_min:>6.1f} -> {score_max:.1f}")
    print(f"\nTotal elapsed: {overall_elapsed}")
