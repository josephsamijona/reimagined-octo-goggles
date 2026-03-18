"""Pydantic schemas for calendar sync."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    event_id: str = ""
    title: str
    start: datetime
    end: datetime
    location: str = ""
    description: str = ""
    attendees: list[str] = []


class SyncAssignmentRequest(BaseModel):
    assignment_id: int


class SyncAllTodayResponse(BaseModel):
    synced: int
    errors: list[str] = []
