import json

from src.ai.claude import (
    add_user_message,
    run_conversation,
    text_from_message,
)
from src.ai.prompts.GRADER_SYSTEM_PROMPT import GRADER_SYSTEM_PROMPT
from src.ai.tools_schema import GRADER_OUTPUT_CONFIG


GRADER_SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": GRADER_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


def grade_email(test_case: dict, generated_email: dict, tool_calls: list[dict] | None = None) -> dict:
    """Score one generated email against its test case's success criteria.

    `tool_calls` is the optional list of {name, input, output} dicts returned
    by generate_email — passing it lets the grader verify that numbers/facts in
    the email are sourced from real tool outputs rather than fabricated.

    Returns a dict with keys: test_case_name, score (1-10), success_criteria,
    clauses_evaluated, weaknesses, reasoning, certainty (0-1).
    """
    payload = {
        "test_case_name": test_case["name"],
        "success_criteria": test_case["success_criteria"],
        "customer_input": test_case["input"],
        "generated_email": generated_email,
        "tool_calls": tool_calls or [],
    }
    messages = []
    add_user_message(
        messages,
        "Adversarial-review mode. Default score is 6; competent baseline is 7. "
        "Anything above 7 requires at least three distinct active strengths cited in `reasoning`.\n\n"
        "Methodology (follow in order):\n"
        "1. Parse success_criteria into distinct clauses; produce one entry per clause in "
        "`clauses_evaluated` with a verdict and quoted evidence.\n"
        "2. Identify at least 2 specific weaknesses in `weaknesses` — even strong emails have them. "
        "If you cannot find two, you are reading too charitably; re-read.\n"
        "3. Before flagging any number or fact in the email as a fabrication, scan `tool_calls` "
        "for a matching value in any tool output. Tool outputs are LEGITIMATE grounding.\n"
        "4. Apply hard caps (any MUST violated → ≤6; any 'must NOT' violated → ≤3; fabricated facts "
        "not sourced from customer_input OR tool_calls → ≤5; schema failure → 1).\n"
        "5. Compute the score under the rubric and write `reasoning` that connects clauses + "
        "weaknesses to the score. If torn between two scores, pick the lower.\n\n"
        "Return JSON per the schema, no prose outside.\n\n"
        "INPUT:\n"
        + json.dumps(payload),
    )
    final = run_conversation(
        messages,
        system=GRADER_SYSTEM_BLOCKS,
        temperature=0.0,
        output_config=GRADER_OUTPUT_CONFIG,
    )
    return json.loads(text_from_message(final))
