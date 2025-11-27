"""
Main conversation loop - calls LLM, runs tools, returns response.
"""

import json
import sqlite3
from .tools import TOOLS, TOOL_FUNCTIONS
from .llm_client import call_llm


def run_agent(messages: list[dict], conn: sqlite3.Connection) -> dict:
    """Process user message, run any tools needed, return response."""
    try:
        llm_result = call_llm(messages, TOOLS)
        assistant_message = llm_result["message"]
        tool_calls = llm_result["tool_calls"]

        if not tool_calls:
            return {
                "role": "assistant",
                "content": llm_result["content"] or "I'm not sure how to help with that."
            }

        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content", "") or "",
            "tool_calls": tool_calls
        })

        # Run each tool
        for tc in tool_calls:
            tool_id = tc.get("id", "")
            function_info = tc.get("function", {})
            name = function_info.get("name", "")

            try:
                args = json.loads(function_info.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}

            if name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[name](conn, args)
                except Exception as e:
                    result = {"error": f"Tool execution failed: {str(e)}"}
            else:
                result = {"error": f"Unknown tool: {name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": name,
                "content": json.dumps(result)
            })

        final_llm_result = call_llm(messages, TOOLS)

        return {
            "role": "assistant",
            "content": final_llm_result["content"] or "I processed your request."
        }

    except Exception as e:
        return {
            "role": "assistant",
            "content": f"I encountered an error: {str(e)}. Please try again."
        }
