"""
Dataclasses for restaurants and reservations.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Restaurant:
    id: int
    name: str
    location_area: str
    city: str
    cuisine: str
    seating_capacity: int
    average_price_per_person: int
    features: str
    opening_time: str
    closing_time: str


@dataclass
class Reservation:
    id: int
    restaurant_id: int
    customer_name: str
    phone: str
    party_size: int
    reservation_datetime: str
    special_requests: Optional[str]
    status: str  # 'confirmed', 'cancelled', 'temp'


@dataclass
class ToolResult:
    success: bool
    data: dict
    error: Optional[str] = None
