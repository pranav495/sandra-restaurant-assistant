"""
Tool functions and schema registry for GoodFoods AI.
Contains all business logic for restaurant operations.
"""

import sqlite3
import datetime
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer


# Embedding model (loaded once)
_EMBEDDING_MODEL = None

def get_embedding_model() -> SentenceTransformer:
    """Load embedding model if not already loaded."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDING_MODEL


# Cache embeddings so we don't recompute every time
_RESTAURANT_EMBEDDINGS: dict[int, np.ndarray] = {}
_RESTAURANT_DATA: dict[int, dict] = {}


def get_restaurant_embeddings(conn: sqlite3.Connection) -> tuple[dict[int, np.ndarray], dict[int, dict]]:
    """Grab cached embeddings or compute them from DB."""
    global _RESTAURANT_EMBEDDINGS, _RESTAURANT_DATA
    
    if _RESTAURANT_EMBEDDINGS:
        return _RESTAURANT_EMBEDDINGS, _RESTAURANT_DATA

    # First time - load from DB
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM restaurants")
    rows = cursor.fetchall()
    
    if not rows:
        return {}, {}
    
    texts = []
    restaurant_ids = []
    for row in rows:
        rest_id = row["id"]
        text = f"{row['name']}. Area: {row['location_area']}. Cuisine: {row['cuisine']}. Features: {row['features'] or 'none'}."
        texts.append(text)
        restaurant_ids.append(rest_id)
        _RESTAURANT_DATA[rest_id] = {
            "id": rest_id,
            "name": row["name"],
            "location_area": row["location_area"],
            "city": row["city"],
            "cuisine": row["cuisine"],
            "seating_capacity": row["seating_capacity"],
            "average_price_per_person": row["average_price_per_person"],
            "features": row["features"],
            "opening_time": row["opening_time"],
            "closing_time": row["closing_time"]
        }
    
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    for i, rest_id in enumerate(restaurant_ids):
        _RESTAURANT_EMBEDDINGS[rest_id] = embeddings[i]
    
    return _RESTAURANT_EMBEDDINGS, _RESTAURANT_DATA


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """How similar are these two vectors?"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# --- Core functions ---

def search_restaurants(
    conn: sqlite3.Connection,
    location: str,
    cuisine: Optional[str],
    party_size: int,
    iso_datetime: str,
    budget: Optional[int] = None
) -> list[dict]:
    """Find restaurants matching location, cuisine, party size, time."""
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
                    "id": row["id"],
                    "name": row["name"],
                    "location_area": row["location_area"],
                    "cuisine": row["cuisine"],
                    "seating_capacity": row["seating_capacity"],
                    "average_price_per_person": row["average_price_per_person"],
                    "features": row["features"],
                    "opening_time": opening,
                    "closing_time": closing
                })
        return results[:10] if results else [{"message": "No restaurants found matching your criteria."}]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


def check_availability(
    conn: sqlite3.Connection,
    restaurant_id: int,
    iso_datetime: str,
    party_size: int
) -> dict:
    """Can we fit this party at this time?"""
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
            return {
                "available": True,
                "restaurant_name": restaurant["name"],
                "available_seats": available_seats,
                "requested_datetime": iso_datetime
            }
        return {"available": False, "reason": f"Only {available_seats} seats remaining for this time slot."}
    except Exception as e:
        return {"error": f"Availability check failed: {str(e)}"}


def create_reservation(
    conn: sqlite3.Connection,
    restaurant_id: int,
    customer_name: str,
    phone: str,
    party_size: int,
    iso_datetime: str,
    special_requests: Optional[str] = None
) -> dict:
    """Book a table."""
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
            "success": True,
            "reservation_id": cursor.lastrowid,
            "restaurant_name": cursor.fetchone()["name"],
            "customer_name": customer_name,
            "party_size": party_size,
            "datetime": iso_datetime,
            "status": "confirmed",
            "message": f"Reservation confirmed! Your reservation ID is {cursor.lastrowid}."
        }
    except Exception as e:
        return {"error": f"Failed to create reservation: {str(e)}"}


def modify_reservation(
    conn: sqlite3.Connection,
    reservation_id: int,
    new_iso_datetime: Optional[str] = None,
    new_party_size: Optional[int] = None
) -> dict:
    """Change time or party size on existing booking."""
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

        cursor.execute(
            "UPDATE reservations SET reservation_datetime = ?, party_size = ? WHERE id = ?",
            (final_datetime, final_party_size, reservation_id)
        )
        conn.commit()
        return {
            "success": True,
            "reservation_id": reservation_id,
            "restaurant_name": reservation["restaurant_name"],
            "new_datetime": final_datetime,
            "new_party_size": final_party_size,
            "message": "Reservation successfully modified."
        }
    except Exception as e:
        return {"error": f"Failed to modify reservation: {str(e)}"}


def cancel_reservation(conn: sqlite3.Connection, reservation_id: int) -> dict:
    """Cancel a booking."""
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
        return {
            "success": True,
            "reservation_id": reservation_id,
            "restaurant_name": reservation["restaurant_name"],
            "message": "Reservation successfully cancelled."
        }
    except Exception as e:
        return {"error": f"Failed to cancel reservation: {str(e)}"}


def get_reservation_by_phone(conn: sqlite3.Connection, phone: str) -> list[dict]:
    """Look up bookings by phone number."""
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
        return [{
            "reservation_id": row["id"],
            "restaurant_name": row["restaurant_name"],
            "customer_name": row["customer_name"],
            "party_size": row["party_size"],
            "datetime": row["reservation_datetime"],
            "special_requests": row["special_requests"],
            "status": row["status"]
        } for row in rows]
    except Exception as e:
        return [{"error": f"Failed to retrieve reservations: {str(e)}"}]


def semantic_recommend(
    conn: sqlite3.Connection,
    location: str,
    mood: str,
    cuisine: Optional[str] = None,
    budget: Optional[int] = None,
    top_k: int = 5
) -> list[dict]:
    """Find restaurants that match the user's vibe/mood using embeddings."""
    try:
        query_parts = [mood]
        if location:
            query_parts.append(f"Area: {location}")
        if cuisine:
            query_parts.append(f"Cuisine: {cuisine}")
        query_text = ". ".join(query_parts) + "."
        
        model = get_embedding_model()
        query_embedding = model.encode(query_text, convert_to_numpy=True)
        
        embeddings, restaurant_data = get_restaurant_embeddings(conn)
        
        if not embeddings:
            return [{"message": "No restaurants available in the database."}]
        
        scored_restaurants = []
        
        for rest_id, rest_embedding in embeddings.items():
            rest_info = restaurant_data[rest_id]
            
            # Skip if doesn't match filters
            if location and location.lower() not in rest_info["location_area"].lower():
                continue
            if cuisine and cuisine.lower() not in rest_info["cuisine"].lower():
                continue
            if budget and rest_info["average_price_per_person"] > budget:
                continue
            
            similarity = cosine_similarity(query_embedding, rest_embedding)
            
            scored_restaurants.append({
                "id": rest_info["id"],
                "name": rest_info["name"],
                "location_area": rest_info["location_area"],
                "cuisine": rest_info["cuisine"],
                "average_price_per_person": rest_info["average_price_per_person"],
                "features": rest_info["features"],
                "opening_time": rest_info["opening_time"],
                "closing_time": rest_info["closing_time"],
                "similarity": round(similarity, 4)
            })
        
        if not scored_restaurants:
            return [{"message": "No suitable restaurants found for your preferences."}]
        
        scored_restaurants.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_restaurants[:top_k]
        
    except Exception as e:
        return [{"error": f"Semantic recommendation failed: {str(e)}"}]


# --- Tool schemas for LLM ---

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
    },
    {
        "name": "semantic_recommend",
        "description": "Recommend restaurants based on user mood, occasion, or vibe using semantic similarity. Use this when the user describes their preferences in terms of mood (romantic, casual, lively), occasion (anniversary, birthday, business meeting), or atmosphere rather than strict filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Preferred area/neighborhood in the city (e.g., 'Bandra', 'Andheri')"},
                "mood": {"type": "string", "description": "User's mood, occasion, or vibe description (e.g., 'romantic anniversary dinner', 'casual friends night out', 'quiet business meeting')"},
                "cuisine": {"type": "string", "description": "Optional preferred cuisine type"},
                "budget": {"type": "integer", "description": "Optional maximum budget per person in INR"},
                "top_k": {"type": "integer", "description": "Number of recommendations to return (default: 5)"}
            },
            "required": ["location", "mood"]
        }
    }
]


# Map tool names to functions

TOOL_FUNCTIONS = {
    "search_restaurants": lambda conn, args: search_restaurants(
        conn,
        args.get("location", ""),
        args.get("cuisine"),
        args.get("party_size", 1),
        args.get("datetime", ""),
        args.get("budget")
    ),
    "check_availability": lambda conn, args: check_availability(
        conn,
        args.get("restaurant_id", 0),
        args.get("datetime", ""),
        args.get("party_size", 1)
    ),
    "create_reservation": lambda conn, args: create_reservation(
        conn,
        args.get("restaurant_id", 0),
        args.get("customer_name", ""),
        args.get("phone", ""),
        args.get("party_size", 1),
        args.get("datetime", ""),
        args.get("special_requests")
    ),
    "modify_reservation": lambda conn, args: modify_reservation(
        conn,
        args.get("reservation_id", 0),
        args.get("new_datetime"),
        args.get("new_party_size")
    ),
    "cancel_reservation": lambda conn, args: cancel_reservation(
        conn,
        args.get("reservation_id", 0)
    ),
    "get_reservation_by_phone": lambda conn, args: get_reservation_by_phone(
        conn,
        args.get("phone", "")
    ),
    "semantic_recommend": lambda conn, args: semantic_recommend(
        conn,
        args.get("location", ""),
        args.get("mood", ""),
        args.get("cuisine"),
        args.get("budget"),
        args.get("top_k", 5)
    )
}
