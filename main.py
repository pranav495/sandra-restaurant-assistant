"""
GoodFoods AI Reservation Assistant
===================================
An end-to-end conversational reservation agent with:
- Streamlit chat UI
- SQLite database with ~50-100 restaurant locations
- Tool-calling layer for LLM integration
- Llama 3.3 8B (or similar) via HTTP API
"""

# =============================================================================
# 1) IMPORTS AND CONFIG
# =============================================================================
import streamlit as st
import sqlite3
import datetime
import json
import random
import requests
from typing import Optional

# Streamlit page configuration
st.set_page_config(
    page_title="GoodFoods AI Reservation Assistant",
    page_icon="🍽️",
    layout="centered"
)

# Database file path
DB_PATH = "goodfoods.db"

# LLM API Configuration
LLAMA_API_URL = "http://localhost:11434/api/chat"
LLM_MODEL = "llama3.2:3b"


# =============================================================================
# 2) DATABASE LAYER
# =============================================================================
def init_db() -> sqlite3.Connection:
    """Initialize database connection and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS restaurants(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            location_area TEXT NOT NULL,
            city TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            seating_capacity INTEGER NOT NULL,
            average_price_per_person INTEGER NOT NULL,
            features TEXT,
            opening_time TEXT NOT NULL,
            closing_time TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations(
            id INTEGER PRIMARY KEY,
            restaurant_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            party_size INTEGER NOT NULL,
            reservation_datetime TEXT NOT NULL,
            special_requests TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed',
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)
    
    conn.commit()
    return conn


def seed_restaurants_if_empty(conn: sqlite3.Connection) -> None:
    """Seed the restaurants table with 75 fake restaurants if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM restaurants")
    if cursor.fetchone()[0] > 0:
        return

    location_areas = ["Andheri", "Bandra", "Juhu", "Colaba", "Powai", "Lower Parel",
                      "Worli", "Malad", "Goregaon", "Churchgate", "Fort", "Kurla",
                      "Thane", "Vashi", "Panvel"]
    cuisines = ["North Indian", "South Indian", "Italian", "Chinese", "Japanese",
                "Thai", "Mexican", "Continental", "Multi-cuisine", "Mughlai",
                "Seafood", "Mediterranean", "Korean", "French", "American"]
    name_prefixes = ["The", "Royal", "Golden", "Silver", "Blue", "Green", "Red",
                     "Grand", "Little", "Big", "Urban", "Classic", "Modern", "Spice"]
    name_suffixes = ["Kitchen", "Bistro", "Cafe", "Restaurant", "Diner", "Grill",
                     "House", "Garden", "Terrace", "Lounge", "Table", "Plate",
                     "Bites", "Corner", "Palace"]
    features_list = ["rooftop", "family-friendly", "bar", "live-music", "outdoor-seating",
                     "private-dining", "valet-parking", "wifi", "pet-friendly",
                     "wheelchair-accessible", "romantic", "buffet"]
    opening_times = ["10:00", "11:00", "11:30", "12:00"]
    closing_times = ["22:00", "22:30", "23:00", "23:30", "00:00"]

    restaurants = []
    used_names = set()

    while len(restaurants) < 75:
        prefix = random.choice(name_prefixes)
        suffix = random.choice(name_suffixes)
        cuisine = random.choice(cuisines)
        name = f"{prefix} {suffix}"
        if name in used_names:
            name = f"{prefix} {cuisine} {suffix}"
        if name in used_names:
            continue
        used_names.add(name)

        restaurants.append((
            name, random.choice(location_areas), "Mumbai", cuisine,
            random.randint(20, 120), random.randint(300, 1200),
            ",".join(random.sample(features_list, random.randint(2, 4))),
            random.choice(opening_times), random.choice(closing_times)
        ))

    cursor.executemany("""
        INSERT INTO restaurants (name, location_area, city, cuisine, seating_capacity,
            average_price_per_person, features, opening_time, closing_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, restaurants)
    conn.commit()


# =============================================================================
# 3) TOOL FUNCTIONS (BACKEND LOGIC)
# =============================================================================
def search_restaurants(conn: sqlite3.Connection, location: str, cuisine: Optional[str],
                       party_size: int, iso_datetime: str, budget: Optional[int] = None) -> list[dict]:
    """Search for restaurants based on criteria."""
    try:
        if party_size <= 0:
            return [{"error": "Party size must be greater than 0"}]
        try:
            dt = datetime.datetime.fromisoformat(iso_datetime)
            request_time = dt.strftime("%H:%M")
        except ValueError:
            return [{"error": "Invalid datetime format. Use ISO 8601 format."}]

        cursor = conn.cursor()
        query = "SELECT * FROM restaurants WHERE LOWER(location_area) LIKE LOWER(?) AND seating_capacity >= ?"
        params = [f"%{location}%", party_size]

        if cuisine:
            query += " AND LOWER(cuisine) LIKE LOWER(?)"
            params.append(f"%{cuisine}%")
        if budget:
            query += " AND average_price_per_person <= ?"
            params.append(budget)

        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            opening, closing = row["opening_time"], row["closing_time"]
            if (opening <= request_time or closing == "00:00") and (closing == "00:00" or request_time <= closing):
                results.append({
                    "id": row["id"], "name": row["name"], "location_area": row["location_area"],
                    "cuisine": row["cuisine"], "seating_capacity": row["seating_capacity"],
                    "average_price_per_person": row["average_price_per_person"],
                    "features": row["features"], "opening_time": opening, "closing_time": closing
                })
        return results[:10] if results else [{"message": "No restaurants found matching your criteria."}]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


def check_availability(conn: sqlite3.Connection, restaurant_id: int, iso_datetime: str, party_size: int) -> dict:
    """Check if a restaurant has availability."""
    try:
        if party_size <= 0:
            return {"error": "Party size must be greater than 0"}
        try:
            dt = datetime.datetime.fromisoformat(iso_datetime)
        except ValueError:
            return {"error": "Invalid datetime format. Use ISO 8601 format."}

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            return {"error": "Restaurant not found"}

        request_time = dt.strftime("%H:%M")
        opening, closing = restaurant["opening_time"], restaurant["closing_time"]
        if not (opening <= request_time and (closing == "00:00" or request_time <= closing)):
            return {"available": False, "reason": f"Restaurant is closed. Hours: {opening} - {closing}"}
        if party_size > restaurant["seating_capacity"]:
            return {"available": False, "reason": f"Party size exceeds capacity of {restaurant['seating_capacity']}"}

        time_start = (dt - datetime.timedelta(hours=1)).isoformat()
        time_end = (dt + datetime.timedelta(hours=1)).isoformat()
        cursor.execute("""
            SELECT SUM(party_size) as total FROM reservations
            WHERE restaurant_id = ? AND reservation_datetime BETWEEN ? AND ? AND status = 'confirmed'
        """, (restaurant_id, time_start, time_end))
        total_reserved = cursor.fetchone()["total"] or 0
        available_seats = restaurant["seating_capacity"] - total_reserved

        if available_seats >= party_size:
            return {"available": True, "restaurant_name": restaurant["name"],
                    "available_seats": available_seats, "requested_datetime": iso_datetime}
        return {"available": False, "reason": f"Only {available_seats} seats remaining for this time slot."}
    except Exception as e:
        return {"error": f"Availability check failed: {str(e)}"}


def create_reservation(conn: sqlite3.Connection, restaurant_id: int, customer_name: str,
                       phone: str, party_size: int, iso_datetime: str,
                       special_requests: Optional[str] = None) -> dict:
    """Create a new reservation."""
    try:
        if party_size <= 0:
            return {"error": "Party size must be greater than 0"}
        if not customer_name.strip():
            return {"error": "Customer name is required"}
        if not phone.strip():
            return {"error": "Phone number is required"}
        try:
            datetime.datetime.fromisoformat(iso_datetime)
        except ValueError:
            return {"error": "Invalid datetime format. Use ISO 8601 format."}

        availability = check_availability(conn, restaurant_id, iso_datetime, party_size)
        if "error" in availability:
            return availability
        if not availability.get("available", False):
            return {"error": availability.get("reason", "Restaurant not available")}

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reservations (restaurant_id, customer_name, phone, party_size,
                reservation_datetime, special_requests, status)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
        """, (restaurant_id, customer_name.strip(), phone.strip(), party_size, iso_datetime, special_requests))
        conn.commit()

        cursor.execute("SELECT name FROM restaurants WHERE id = ?", (restaurant_id,))
        return {
            "success": True, "reservation_id": cursor.lastrowid,
            "restaurant_name": cursor.fetchone()["name"], "customer_name": customer_name,
            "party_size": party_size, "datetime": iso_datetime, "status": "confirmed",
            "message": f"Reservation confirmed! Your reservation ID is {cursor.lastrowid}."
        }
    except Exception as e:
        return {"error": f"Failed to create reservation: {str(e)}"}


def modify_reservation(conn: sqlite3.Connection, reservation_id: int,
                       new_iso_datetime: Optional[str] = None, new_party_size: Optional[int] = None) -> dict:
    """Modify an existing reservation."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, rest.name as restaurant_name FROM reservations r
            JOIN restaurants rest ON r.restaurant_id = rest.id WHERE r.id = ?
        """, (reservation_id,))
        reservation = cursor.fetchone()
        if not reservation:
            return {"error": "Reservation not found"}
        if reservation["status"] == "cancelled":
            return {"error": "Cannot modify a cancelled reservation"}

        final_datetime = new_iso_datetime or reservation["reservation_datetime"]
        final_party_size = new_party_size or reservation["party_size"]

        if new_iso_datetime:
            try:
                datetime.datetime.fromisoformat(new_iso_datetime)
            except ValueError:
                return {"error": "Invalid datetime format. Use ISO 8601 format."}

        if new_iso_datetime or new_party_size:
            cursor.execute("UPDATE reservations SET status = 'temp' WHERE id = ?", (reservation_id,))
            availability = check_availability(conn, reservation["restaurant_id"], final_datetime, final_party_size)
            cursor.execute("UPDATE reservations SET status = 'confirmed' WHERE id = ?", (reservation_id,))
            if "error" in availability or not availability.get("available", False):
                return {"error": availability.get("reason", availability.get("error", "Not available"))}

        cursor.execute("UPDATE reservations SET reservation_datetime = ?, party_size = ? WHERE id = ?",
                       (final_datetime, final_party_size, reservation_id))
        conn.commit()
        return {"success": True, "reservation_id": reservation_id,
                "restaurant_name": reservation["restaurant_name"],
                "new_datetime": final_datetime, "new_party_size": final_party_size,
                "message": "Reservation successfully modified."}
    except Exception as e:
        return {"error": f"Failed to modify reservation: {str(e)}"}


def cancel_reservation(conn: sqlite3.Connection, reservation_id: int) -> dict:
    """Cancel an existing reservation."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, rest.name as restaurant_name FROM reservations r
            JOIN restaurants rest ON r.restaurant_id = rest.id WHERE r.id = ?
        """, (reservation_id,))
        reservation = cursor.fetchone()
        if not reservation:
            return {"error": "Reservation not found"}
        if reservation["status"] == "cancelled":
            return {"error": "Reservation is already cancelled"}

        cursor.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
        conn.commit()
        return {"success": True, "reservation_id": reservation_id,
                "restaurant_name": reservation["restaurant_name"],
                "message": "Reservation successfully cancelled."}
    except Exception as e:
        return {"error": f"Failed to cancel reservation: {str(e)}"}


def get_reservation_by_phone(conn: sqlite3.Connection, phone: str) -> list[dict]:
    """Get all reservations for a phone number."""
    try:
        if not phone.strip():
            return [{"error": "Phone number is required"}]
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, rest.name as restaurant_name FROM reservations r
            JOIN restaurants rest ON r.restaurant_id = rest.id
            WHERE r.phone = ? ORDER BY r.reservation_datetime DESC
        """, (phone.strip(),))
        rows = cursor.fetchall()
        if not rows:
            return [{"message": "No reservations found for this phone number."}]
        return [{"reservation_id": row["id"], "restaurant_name": row["restaurant_name"],
                 "customer_name": row["customer_name"], "party_size": row["party_size"],
                 "datetime": row["reservation_datetime"], "special_requests": row["special_requests"],
                 "status": row["status"]} for row in rows]
    except Exception as e:
        return [{"error": f"Failed to retrieve reservations: {str(e)}"}]


# =============================================================================
# 4) TOOL SCHEMA REGISTRY FOR LLM
# =============================================================================
TOOLS = [
    {
        "name": "search_restaurants",
        "description": "Search restaurants given location, cuisine, date/time, party size, and optional budget.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Area/neighborhood (e.g., 'Bandra', 'Andheri')"},
                "cuisine": {"type": "string", "description": "Type of cuisine (e.g., 'Italian', 'North Indian')"},
                "party_size": {"type": "integer", "description": "Number of people"},
                "datetime": {"type": "string", "description": "ISO 8601 datetime (e.g., '2024-12-25T19:00:00')"},
                "budget": {"type": "integer", "description": "Maximum budget per person in INR"}
            },
            "required": ["location", "party_size", "datetime"]
        }
    },
    {
        "name": "check_availability",
        "description": "Check if a restaurant has availability for a given date/time and party size.",
        "parameters": {
            "type": "object",
            "properties": {
                "restaurant_id": {"type": "integer", "description": "The restaurant ID"},
                "datetime": {"type": "string", "description": "ISO 8601 datetime"},
                "party_size": {"type": "integer", "description": "Number of people"}
            },
            "required": ["restaurant_id", "datetime", "party_size"]
        }
    },
    {
        "name": "create_reservation",
        "description": "Create a new reservation at a restaurant.",
        "parameters": {
            "type": "object",
            "properties": {
                "restaurant_id": {"type": "integer", "description": "The restaurant ID"},
                "customer_name": {"type": "string", "description": "Customer name"},
                "phone": {"type": "string", "description": "Contact phone number"},
                "party_size": {"type": "integer", "description": "Number of people"},
                "datetime": {"type": "string", "description": "ISO 8601 datetime"},
                "special_requests": {"type": "string", "description": "Special requests or notes"}
            },
            "required": ["restaurant_id", "customer_name", "phone", "party_size", "datetime"]
        }
    },
    {
        "name": "modify_reservation",
        "description": "Modify an existing reservation's date/time or party size.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "integer", "description": "The reservation ID"},
                "new_datetime": {"type": "string", "description": "New ISO 8601 datetime (optional)"},
                "new_party_size": {"type": "integer", "description": "New party size (optional)"}
            },
            "required": ["reservation_id"]
        }
    },
    {
        "name": "cancel_reservation",
        "description": "Cancel an existing reservation.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "integer", "description": "The reservation ID"}
            },
            "required": ["reservation_id"]
        }
    },
    {
        "name": "get_reservation_by_phone",
        "description": "Look up all reservations associated with a phone number.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Phone number to search"}
            },
            "required": ["phone"]
        }
    }
]


# =============================================================================
# 5) LLM CALL WRAPPER
# =============================================================================
def call_llama_api(payload: dict) -> dict:
    """
    Perform a real HTTP POST request to a generic LLM API that supports chat and tools.
    Here we use the Groq /chat/completions endpoint.
    """
    try:
        headers = {
            "Content-Type": "application/json",
        }
        resp = requests.post(
            LLAMA_API_URL,
            headers=headers,
            json=payload,
            timeout=180,
        )

        # If Groq returns an error, surface the body so we can see what is wrong
        if resp.status_code != 200:
            try:
                err_json = resp.json()
                # Groq usually returns {"error": {...}} or similar
                return {
                    "error": f"LLM API error {resp.status_code}: {json.dumps(err_json)}"
                }
            except json.JSONDecodeError:
                return {
                    "error": f"LLM API error {resp.status_code}: {resp.text}"
                }

        return resp.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"LLM API request failed: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse LLM API response: {str(e)}"}



def call_llm(messages: list[dict], tools: list[dict]) -> dict:
    """
    Call a generic LLM API that supports chat and tools.
    
    Constructs the payload and interprets the response assuming a standard
    chat-completions format with tool_calls support.
    
    Returns:
        dict with keys: 'message' (full assistant message), 'tool_calls' (list), 'content' (str)
    """
    system_prompt = """
You are GoodFoods AI, a helpful restaurant reservation assistant for Mumbai.

Your main tasks:
- Help users search for restaurants.
- Check availability.
- Create, modify, and cancel reservations.
- Look up existing reservations by phone.

CONVERSATION FLOW (VERY IMPORTANT):

1) When a user says they want to make a reservation but has not chosen a restaurant yet:
   - DO NOT call any tools immediately.
   - First, ask for:
     - Date and time
     - Party size
     - Preferred location/area
     - Optional: cuisine and budget
   - Once you have at least location, party_size, and datetime, THEN call the tool
     `search_restaurants` to find candidates.

2) After calling `search_restaurants`:
   - Summarise the top 3–5 options clearly.
   - Always show each option with:
     - Restaurant name
     - Area
     - Cuisine
     - Approx. price per person
     - The restaurant_id from the tool result.
   - Ask the user to choose one restaurant by its restaurant_id.

3) Only after the user has selected a restaurant_id:
   - Use `check_availability` for that restaurant_id and requested datetime and party_size.
   - If available, use `create_reservation` to confirm the booking.

4) NEVER invent restaurant_ids.
   - Only use restaurant_ids that:
     - Came from a previous tool result, or
     - Were explicitly provided by the user.
   - If you do not know the restaurant_id, ask the user to pick one from the list you just showed.

5) For modifying or cancelling reservations:
   - Ask the user for either:
     - reservation_id, or
     - phone number + date/time so you can call `get_reservation_by_phone` first.
   - Again, DO NOT invent ids.

6) When a tool returns an error:
   - Briefly explain the issue in natural language.
   - Then guide the user with a specific next question or suggestion.
   - Do not repeat low-level technical error messages.

Other rules:
- Always use ISO 8601 format for dates and times (e.g., 2024-12-25T19:00:00).
- Be concise, polite, and clear.
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream": False,
        "temperature": 0.3
    }
    
    response = call_llama_api(payload)
    
    # Handle API errors
    if "error" in response:
        return {
            "message": {"role": "assistant", "content": response["error"]},
            "tool_calls": [],
            "content": response["error"]
        }
    
    # Parse Ollama response format: {"message": {"role": "assistant", "content": "..."}}
    try:
        message = response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        content = message.get("content", "") or ""
        
        return {
            "message": message,
            "tool_calls": tool_calls,
            "content": content
        }
    except (KeyError, IndexError) as e:
        error_msg = f"Unexpected LLM API response format: {str(e)}"
        return {
            "message": {"role": "assistant", "content": error_msg},
            "tool_calls": [],
            "content": error_msg
        }


# =============================================================================
# 6) AGENT LOOP
# =============================================================================
TOOL_FUNCTIONS = {
    "search_restaurants": lambda conn, args: search_restaurants(
        conn, args.get("location", ""), args.get("cuisine"), args.get("party_size", 1),
        args.get("datetime", ""), args.get("budget")),
    "check_availability": lambda conn, args: check_availability(
        conn, args.get("restaurant_id", 0), args.get("datetime", ""), args.get("party_size", 1)),
    "create_reservation": lambda conn, args: create_reservation(
        conn, args.get("restaurant_id", 0), args.get("customer_name", ""), args.get("phone", ""),
        args.get("party_size", 1), args.get("datetime", ""), args.get("special_requests")),
    "modify_reservation": lambda conn, args: modify_reservation(
        conn, args.get("reservation_id", 0), args.get("new_datetime"), args.get("new_party_size")),
    "cancel_reservation": lambda conn, args: cancel_reservation(conn, args.get("reservation_id", 0)),
    "get_reservation_by_phone": lambda conn, args: get_reservation_by_phone(conn, args.get("phone", ""))
}


def run_agent(messages: list[dict], conn: sqlite3.Connection) -> dict:
    """
    Run the agent loop with support for multiple tool calls.
    
    1. Call the LLM with messages and tools
    2. If tool_calls are present, execute each tool and append results
    3. Call LLM again to generate final response based on tool results
    4. Return the final assistant message
    """
    try:
        # First LLM call
        llm_result = call_llm(messages, TOOLS)
        assistant_message = llm_result["message"]
        tool_calls = llm_result["tool_calls"]
        
        # If no tool calls, return the assistant's content directly
        if not tool_calls:
            return {"role": "assistant", "content": llm_result["content"] or "I'm not sure how to help with that."}
        
        # Process each tool call
        # First, append the assistant message that requested the tools
        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content", "") or "",
            "tool_calls": tool_calls
        })
        
        # Execute each tool and append results
        for tc in tool_calls:
            tool_id = tc.get("id", "")
            function_info = tc.get("function", {})
            name = function_info.get("name", "")
            
            # Parse arguments (they come as a JSON string)
            try:
                args = json.loads(function_info.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            
            # Execute the tool function
            if name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[name](conn, args)
                except Exception as e:
                    result = {"error": f"Tool execution failed: {str(e)}"}
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            # Append tool result message in the generic format
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": name,
                "content": json.dumps(result)
            })
        
        # Second LLM call to get the final response based on tool results
        final_llm_result = call_llm(messages, TOOLS)
        
        return {"role": "assistant", "content": final_llm_result["content"] or "I processed your request."}
        
    except Exception as e:
        return {"role": "assistant", "content": f"I encountered an error: {str(e)}. Please try again."}


# =============================================================================
# 7) STREAMLIT CHAT UI
# =============================================================================
def main():
    """Main Streamlit application."""
    st.title("🍽️ GoodFoods AI Reservation Assistant")
    st.caption("Your personal assistant for restaurant reservations in Mumbai")

    conn = init_db()
    seed_restaurants_if_empty(conn)

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": """Welcome to GoodFoods! 👋 I'm your AI reservation assistant.

I can help you:
- 🔍 **Search** for restaurants by location, cuisine, or budget
- 📅 **Check availability** at specific restaurants
- ✅ **Make reservations** for you
- ✏️ **Modify** existing bookings
- ❌ **Cancel** reservations
- 📱 **Look up** your reservations by phone number

How can I help you today?"""
        }]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            agent_messages = [{"role": m["role"], "content": m["content"]}
                              for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
            response = run_agent(agent_messages, conn)
        
        st.session_state.messages.append(response)
        st.rerun()

    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""**GoodFoods AI** - Conversational reservation assistant.
        
**Areas:** Mumbai (Bandra, Andheri, Juhu, Colaba, Powai, Lower Parel, etc.)

**Cuisines:** North Indian, South Indian, Italian, Chinese, Japanese, Thai, and more!""")
        st.divider()
        st.header("🔧 Debug Info")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM restaurants")
        st.metric("Restaurants", cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM reservations")
        st.metric("Total Reservations", cursor.fetchone()[0])


# =============================================================================
# 8) ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    main()
