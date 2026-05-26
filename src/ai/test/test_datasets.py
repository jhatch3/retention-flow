import sys
import json

from pathlib import Path

# Notebook is at src/ai/prompt_testing.ipynb
# We want the repo root on sys.path so `src.ai.xxx` resolves
sys.path.insert(0, str(Path.cwd().parent.parent))

from src.ai.prompts.test_dataset import TEST_CASES
from src.ai.prompts.RETENTION_EMAIL_SYSTEM_PROMPT import RETENTION_EMAIL_SYSTEM_PROMPT
from src.ai.claude import run_conversation, text_from_message
from src.ai.tools_schema import FORMAT_RESPONSE_OUTPUT_CONFIG

if __name__ == "__main__":
    for i, test_case in enumerate(TEST_CASES):
        print(f"\n=== Running test case {i + 1} ===")
        messages = []
        messages.append({"role": "user", "content": str(test_case)})

        final = run_conversation(
            messages,
            model = "claude-sonnet-4-6",
            system=RETENTION_EMAIL_SYSTEM_PROMPT,
            temperature=0.0,
            output_config=FORMAT_RESPONSE_OUTPUT_CONFIG,
        )

        structured = json.loads(text_from_message(final))   
        print(f"Header: {structured['subject']}")
        print(f"Body: {structured['body']}")
        print(f"CTA: {structured['call_to_action']}")

        
        


