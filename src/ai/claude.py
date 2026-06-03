import json
import os
from datetime import datetime
import anthropic
from dotenv import load_dotenv

from ai.config import DEFAULT_MODEL
from ai.prompts.RETENTION_EMAIL_SYSTEM_PROMPT import RETENTION_EMAIL_SYSTEM_PROMPT
from ai.prompts.test_dataset import test_case_service_failure
from ai.tools import run_tools
from ai.tools_schema import FORMAT_RESPONSE_OUTPUT_CONFIG, TOOL_SCHEMAS

load_dotenv()

key = os.environ.get("ANTHROPIC_API_KEY")
assert key is not None, "ANTHROPIC_API_KEY environment variable is not set"
assert RETENTION_EMAIL_SYSTEM_PROMPT is not None, "RETENTION_EMAIL_SYSTEM_PROMPT is not set"

client = anthropic.Anthropic()

RETENTION_EMAIL_SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": RETENTION_EMAIL_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


def add_user_message(messages, content):
    messages.append({"role": "user", "content": content})


def add_assistant_message(messages, message):
    messages.append({"role": "assistant", "content": message.content})


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None, model=DEFAULT_MODEL, output_config=None):
    params = {
        "model": model,
        "max_tokens": 4096,
        "messages": messages,
        "temperature": temperature,
    }

    if stop_sequences:
        params["stop_sequences"] = stop_sequences
    if tools:
        params["tools"] = tools
    if system:
        params["system"] = system
    if output_config:
        params["output_config"] = output_config

    return client.messages.create(**params)


def text_from_message(message):
    return "\n".join(block.text for block in message.content if block.type == "text")


def run_conversation(
    messages,
    model=DEFAULT_MODEL,
    system=None,
    temperature=1.0,
    stop_sequences=None,
    tools=None,
    output_config=None,
    max_turns=10,
    tool_log=None,
):
    """Run a tool-loop conversation. If `tool_log` is a list, it's appended to
    in-place with one dict per tool call: {name, input, output}.
    """
    pending: dict[str, dict] = {}
    for _ in range(max_turns):
        response = chat(
            messages,
            tools=tools,
            model=model,
            system=system,
            temperature=temperature,
            stop_sequences=stop_sequences,
            output_config=output_config,
        )

        add_assistant_message(messages, response)

        if response.stop_reason != "tool_use":
            return response

        if tool_log is not None:
            for block in response.content:
                if block.type == "tool_use":
                    pending[block.id] = {"name": block.name, "input": block.input}

        tool_results = run_tools(response)

        if tool_log is not None:
            for tr in tool_results:
                entry = pending.pop(tr["tool_use_id"], None)
                if entry is not None:
                    entry["output"] = tr["content"]
                    tool_log.append(entry)

        add_user_message(messages, tool_results)

    raise RuntimeError(f"run_conversation exceeded max_turns={max_turns} without terminating")


def generate_email(customer_input: dict, use_db_tools: bool = True) -> tuple[dict, list[dict]]:
    """Generate one structured retention email for the given customer payload.

    When use_db_tools is True, the model may call read-only DB tools to ground
    the email in real customer history. Returns (email_dict, tool_calls) where
    tool_calls is a list of {name, input, output} dicts (empty if tools weren't
    used or weren't called).
    """
    messages = []
    add_user_message(
        messages,
        "Generate a retention email for the customer below. Return the structured "
        "JSON output exactly per the schema.\n\n"
        "Before you emit, verify each item:\n"
        "  1. Tone matches risk tier + SHAP profile. risk_tier='low' OR mostly-protective "
        "     top SHAPs → tone MUST be 'neutral' (no warm phrasing in the body).\n"
        "  2. Offer decision matches SHAP driver type. Service failure → no offer. "
        "     Weak/protective signals → no offer. Price/engagement risk → offer with {{offer_detail}}.\n"
        "  3. CTA intent matches offer: includes_offer=true ⟺ intent='redeem'. "
        "     Service failure → 'support'. Review concern → 'feedback' or 'support', NOT 'browse'. "
        "     Low/weak signal → 'browse' or 'feedback', NEVER 'redeem'.\n"
        "  4. Subject anchors to a specific signal (a number, a behavior, a question). "
        "     NO transactional 'Your X order arrived' framing.\n"
        "  5. Sign-off is the exact string 'The Hatch Brand Team' — no '{{brand}}', no '[Brand]', no invented employee names.\n"
        "  6. Tool calls: if risk_tier='low' OR signals are weak (most top SHAPs protective), "
        "     call ZERO tools. Otherwise at most 2.\n"
        "  7. Numbers in the body trace to customer_input or a tool output. ROUND day counts to integers "
        "     ('13 days', not '12.56 days' or '13.0 days'). Money may keep two decimals when meaningful.\n\n"
        "INPUT:\n"
        + json.dumps(customer_input),
    )
    tool_log: list[dict] = []
    final = run_conversation(
        messages,
        system=RETENTION_EMAIL_SYSTEM_BLOCKS,
        temperature=0.0,
        tools=TOOL_SCHEMAS if use_db_tools else None,
        output_config=FORMAT_RESPONSE_OUTPUT_CONFIG,
        tool_log=tool_log if use_db_tools else None,
    )
    return json.loads(text_from_message(final)), tool_log


if __name__ == "__main__":
    now = datetime.now()
    email, tool_calls = generate_email(test_case_service_failure["input"])
    now2 = datetime.now()

    print(" ============== Subject ================== ")
    print(email["subject"])
    print(" ============== Body ================== ")
    print(email["body"])
    print(f"Elapsed: {now2 - now}")