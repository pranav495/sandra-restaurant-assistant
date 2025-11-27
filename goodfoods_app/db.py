"""
SQLite setup - creates tables and seeds sample restaurants.
"""

import sqlite3
import random
from .config import DB_PATH, DEFAULT_CITY


def init_db() -> sqlite3.Connection:
    """Connect to DB and create tables if needed."""
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
    """Add sample restaurants if the table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM restaurants")
    if cursor.fetchone()[0] > 0:
        return

    location_areas = [
        "Andheri", "Bandra", "Juhu", "Colaba", "Powai", "Lower Parel",
        "Worli", "Malad", "Goregaon", "Churchgate", "Fort", "Kurla",
        "Thane", "Vashi", "Panvel"
    ]
    cuisines = [
        "North Indian", "South Indian", "Italian", "Chinese", "Japanese",
        "Thai", "Mexican", "Continental", "Multi-cuisine", "Mughlai",
        "Seafood", "Mediterranean", "Korean", "French", "American"
    ]
    name_prefixes = [
        "The", "Royal", "Golden", "Silver", "Blue", "Green", "Red",
        "Grand", "Little", "Big", "Urban", "Classic", "Modern", "Spice"
    ]
    name_suffixes = [
        "Kitchen", "Bistro", "Cafe", "Restaurant", "Diner", "Grill",
        "House", "Garden", "Terrace", "Lounge", "Table", "Plate",
        "Bites", "Corner", "Palace"
    ]
    features_list = [
        "rooftop", "family-friendly", "bar", "live-music", "outdoor-seating",
        "private-dining", "valet-parking", "wifi", "pet-friendly",
        "wheelchair-accessible", "romantic", "buffet"
    ]
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
            name,
            random.choice(location_areas),
            DEFAULT_CITY,
            cuisine,
            random.randint(20, 120),
            random.randint(300, 1200),
            ",".join(random.sample(features_list, random.randint(2, 4))),
            random.choice(opening_times),
            random.choice(closing_times)
        ))

    cursor.executemany("""
        INSERT INTO restaurants (name, location_area, city, cuisine, seating_capacity,
            average_price_per_person, features, opening_time, closing_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, restaurants)
    conn.commit()
