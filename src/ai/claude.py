import json
import os
from datetime import datetime
import anthropic
from dotenv import load_dotenv

from src.ai.prompts.RETENTION_EMAIL_SYSTEM_PROMPT import RETENTION_EMAIL_SYSTEM_PROMPT
from src.ai.prompts.test_dataset import test_input_service_failure
from src.ai.tools import run_tools
from src.ai.tools_schema import FORMAT_RESPONSE_OUTPUT_CONFIG, TOOL_SCHEMAS

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


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None, model="claude-haiku-4-5", output_config=None):
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
    model="claude-haiku-4-5",
    system=None,
    temperature=1.0,
    stop_sequences=None,
    tools=None,
    output_config=None,
    max_turns=10,
):
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

        tool_results = run_tools(response)
        add_user_message(messages, tool_results)

    raise RuntimeError(f"run_conversation exceeded max_turns={max_turns} without terminating")


if __name__ == "__main__":
    messages = []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    add_user_message(
        messages,
        "Generate an email and format it as JSON according to the schema. Use the following input data:"
        + json.dumps(test_input_service_failure),
    )

    final = run_conversation(
        messages,
        system=RETENTION_EMAIL_SYSTEM_BLOCKS,
        temperature=0.0,
        output_config=FORMAT_RESPONSE_OUTPUT_CONFIG,
    )

    print(f"Cache write: {final.usage.cache_creation_input_tokens} tokens")
    print(f"Cache hit:   {final.usage.cache_read_input_tokens} tokens")

    structured = json.loads(text_from_message(final))

    print(" ============== Subject ================== ")
    print(structured["subject"])

    print(" ============== Body ================== ")
    print(structured["body"])

    now2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Start time: {now}")
    print(f"End time: {now2}")
    print(f"Elapsed time: {datetime.strptime(now2, '%Y-%m-%d %H:%M:%S') - datetime.strptime(now, '%Y-%m-%d %H:%M:%S')}")