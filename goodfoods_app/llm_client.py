"""
Handles communication with the local Ollama LLM.
"""

import json
import requests
from .config import LLAMA_API_URL, LLAMA_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_TOP_P, LLM_TIMEOUT


SYSTEM_PROMPT = """
You are Sandra, a friendly and helpful restaurant reservation assistant for Mumbai.

Your main tasks:
- Help users search for restaurants.
- Recommend restaurants based on mood, occasion, or vibe.
- Check availability.
- Create, modify, and cancel reservations.
- Look up existing reservations by phone.

CONVERSATION FLOW (VERY IMPORTANT):

1) SEMANTIC RECOMMENDATIONS (mood-based queries):
   - If the user describes their preferences using "soft" terms like:
     - Mood: romantic, cozy, lively, quiet, casual, upscale
     - Occasion: anniversary, birthday, date night, business meeting, friends gathering
     - Atmosphere: rooftop, outdoor, family-friendly, live music
   - Then use the `semantic_recommend` tool instead of `search_restaurants`.
   - Example: "Looking for something romantic for an anniversary in Bandra, budget around 800"
     → Call semantic_recommend(location="Bandra", mood="romantic anniversary dinner", budget=800)

2) After calling `semantic_recommend`:
   - Present the top 3–5 recommendations clearly.
   - For each recommendation, show:
     - Restaurant name
     - Area
     - Cuisine
     - Price per person
     - The restaurant_id
     - A short sentence explaining WHY it fits their mood (based on features like "romantic", "rooftop", etc.)
   - Ask the user to choose one by Restaurant ID.

3) STRUCTURED SEARCH (filter-based queries):
   - If the user gives strict filters like specific cuisine, date/time, and party size without mood descriptors:
   - Use `search_restaurants` tool.
   - Example: "Find Italian restaurants in Andheri for 4 people tomorrow at 7pm"
     → Call search_restaurants with those specific filters.

4) When a user says they want to make a reservation but has not chosen a restaurant yet:
   - DO NOT call any tools immediately.
   - First, ask for:
     - Date and time
     - Party size
     - Preferred location/area
     - Optional: cuisine, budget, mood/occasion
   - If they mention mood/occasion, use `semantic_recommend`.
   - If they give strict filters only, use `search_restaurants`.

5) After getting restaurant suggestions (from either tool):
   - Summarise the top 3–5 options clearly with restaurant_id.
   - Ask the user to choose one restaurant by its restaurant_id.

6) Only after the user has selected a restaurant_id:
   - Use `check_availability` for that restaurant_id and requested datetime and party_size.
   - If available, use `create_reservation` to confirm the booking.

7) NEVER invent restaurant_ids.
   - Only use restaurant_ids that:
     - Came from a previous tool result, or
     - Were explicitly provided by the user.
   - If you do not know the restaurant_id, ask the user to pick one from the list you just showed.

8) For modifying or cancelling reservations:
   - Ask the user for either:
     - reservation_id, or
     - phone number + date/time so you can call `get_reservation_by_phone` first.
   - Again, DO NOT invent ids.

9) When a tool returns an error:
   - Briefly explain the issue in natural language.
   - Then guide the user with a specific next question or suggestion.
   - Do not repeat low-level technical error messages.

Other rules:
- Always use ISO 8601 format for dates and times (e.g., 2024-12-25T19:00:00).
- Be concise, polite, and clear.
- When recommending based on mood, highlight the restaurant features that match the user's vibe.
"""


import requests
import json

def call_llama_api(payload: dict) -> dict:
    """Send a request to local Ollama."""
    try:
        headers = {
            "Content-Type": "application/json",
        }
        resp = requests.post(
            LLAMA_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )

        if resp.status_code != 200:
            try:
                err_json = resp.json()
                return {"error": f"Ollama error {resp.status_code}: {json.dumps(err_json)}"}
            except json.JSONDecodeError:
                return {"error": f"Ollama error {resp.status_code}: {resp.text}"}

        return resp.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"Ollama request failed: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse Ollama response: {str(e)}"}



def call_llm(messages: list[dict], tools: list[dict]) -> dict:
    """Chat with the model and get response (handles tools if any)."""
    system_prompt = """
You are Sandra, a friendly and helpful restaurant reservation assistant for Mumbai.

Your main tasks:
- Help users search for restaurants.
- Check availability.
- Create, modify, and cancel reservations.
- Look up existing reservations by phone.

Follow the conversation flow described earlier, use tools when needed,
and answer concisely. Use ISO 8601 dates (e.g., 2024-12-25T19:00:00).
"""

    ollama_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": LLM_MODEL,
        "messages": ollama_messages,
        "stream": False,
    }

    response = call_llama_api(payload)

    if "error" in response:
        return {
            "message": {"role": "assistant", "content": response["error"]},
            "tool_calls": [],
            "content": response["error"],
        }

    try:
        msg = response.get("message", {}) or {}
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else []

        return {
            "message": msg,
            "tool_calls": tool_calls,
            "content": content,
        }
    except Exception as e:
        err = f"Unexpected Ollama response format: {str(e)}"
        return {
            "message": {"role": "assistant", "content": err},
            "tool_calls": [],
            "content": err,
        }
