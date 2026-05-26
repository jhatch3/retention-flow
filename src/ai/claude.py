import os
import json

import anthropic

from anthropic.types import Message

from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from datetime import datetime
from pprint import pprint 

from src.ai.prompts.RETENTION_EMAIL_SYSTEM_PROMPT import RETENTION_EMAIL_SYSTEM_PROMPT
from src.ai.tools import run_tools
from src.ai.tools_schema import TOOL_SCHEMAS, FORMAT_RESPONSE_OUTPUT_CONFIG
from src.ai.prompts.test_dataset import test_input_service_failure

load_dotenv()

key = os.environ.get("ANTHROPIC_API_KEY")
assert key is not None, "ANTHROPIC_API_KEY environment variable is not set"
assert RETENTION_EMAIL_SYSTEM_PROMPT is not None, "RETENTION_EMAIL_SYSTEM_PROMPT is not set"
assert TOOL_SCHEMAS is not None, "TOOL_SCHEMAS is not set"

client = anthropic.Anthropic()


def add_user_message(messages, message):
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None, model="claude-haiku-4-5", output_config=None):
    params = {
        "model": model,
        "max_tokens": 1000,
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
    return "\n".join([block.text for block in message.content if block.type == "text"])


def run_conversation(messages, model="claude-haiku-4-5", system=None, temperature=1.0, stop_sequences=None, tools=None, output_config=None):
    while True:
        response = chat(
            messages,
            tools=tools,
            model=model,
            system=system,
            temperature=temperature,
            stop_sequences=stop_sequences,
            output_config=output_config
        )

        add_assistant_message(messages, response)

        if response.stop_reason != "tool_use":
            return response

        tool_results = run_tools(response)
        add_user_message(messages, tool_results)



if __name__ == "__main__":
    print(datetime.now(ZoneInfo("America/Los_Angeles"))) 
    messages = []
    add_user_message(
        messages,
        "Generate an email and format it as JSON according to the schema. Use the following input data:" + str(test_input_service_failure) 
    )

    final = run_conversation(
        messages,
        system=RETENTION_EMAIL_SYSTEM_PROMPT,
        temperature=0.0,
        tools=TOOL_SCHEMAS,
        output_config=FORMAT_RESPONSE_OUTPUT_CONFIG
    )

    structured = json.loads(text_from_message(final))
    
    print(f" ============== Subject ================== ")
    print(structured["subject"])

    print(f" ============== Body ================== ")
    print(structured["body"])
    