import json
from datetime import datetime
from zoneinfo import ZoneInfo

from ai.db_tools import (
    get_category_baseline,
    get_customer_delivery_stats,
    get_customer_recent_orders,
    get_customer_review_history,
)


def get_current_datetime(timezone: str = "UTC") -> str:
    """Return the current date and time in the specified timezone."""
    try:
        now = datetime.now(ZoneInfo(timezone))
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as e:
        return f"Error: {str(e)}"


TOOL_FUNCTIONS = {
    "get_current_datetime": get_current_datetime,
    "get_customer_delivery_stats": get_customer_delivery_stats,
    "get_customer_recent_orders": get_customer_recent_orders,
    "get_category_baseline": get_category_baseline,
    "get_customer_review_history": get_customer_review_history,
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
