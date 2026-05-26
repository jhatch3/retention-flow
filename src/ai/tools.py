import json
from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_datetime(timezone: str = "UTC") -> str:
    """Return the current date and time in the specified timezone."""
    try:
        now = datetime.now(ZoneInfo(timezone))
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as e:
        return f"Error: {str(e)}"

def format_response(
    customer_id: str,
    subject: str,
    body: str,
    call_to_action: dict,
    tone: str,
    risk_tier: str,
    includes_offer: bool,
    grounding: dict,
    reasoning: str,
) -> dict:
    """
    Tool handler for the format_response tool. Claude calls this with the
    structured email it has composed. This function validates the structure
    and returns it back as the tool result.

    Since the schema enforcement happens at the API level, this function
    primarily exists to (1) satisfy the tool-use contract and (2) give us
    a hook for any post-processing or persistence.
    """
    return json.dump({
        "customer_id": customer_id,
        "subject": subject,
        "body": body,
        "call_to_action": call_to_action,
        "tone": tone,
        "risk_tier": risk_tier,
        "includes_offer": includes_offer,
        "grounding": grounding,
        "reasoning": reasoning,
    })



TOOL_FUNCTIONS = {
    "get_current_datetime": get_current_datetime,
    "format_response": format_response,
}


def run_tool(tool_name, tool_input):
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    return TOOL_FUNCTIONS[tool_name](**tool_input)


def run_tools(message):
    tool_requests = [block for block in message.content if block.type == "tool_use"]
    tool_result_blocks = []

    for tool_request in tool_requests:
        try:
            tool_output = run_tool(tool_request.name, tool_request.input)
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": json.dumps(tool_output),
                "is_error": False,
            }
        except Exception as e:
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {e}",
                "is_error": True,
            }

        tool_result_blocks.append(tool_result_block)

    return tool_result_blocks
