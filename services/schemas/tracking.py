"""Pydantic schemas for GPS tracking."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LocationUpdate(BaseModel):
    interpreter_id: int
    latitude: float
    longitude: float
    accuracy: float | None = None
    is_on_mission: bool = False
    current_assignment_id: int | None = None


class LivePosition(BaseModel):
    interpreter_id: int
    name: str
    latitude: float
    longitude: float
    accuracy: float | None = None
    is_on_mission: bool = False
    current_assignment_id: int | None = None
    timestamp: datetime | None = None
