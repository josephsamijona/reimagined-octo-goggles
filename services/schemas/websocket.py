"""Pydantic schemas for WebSocket messages."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WSMessage(BaseModel):
    event: str
    data: dict[str, Any] = {}
    timestamp: datetime | None = None


class WSEvent(BaseModel):
    type: str  # NEW_EMAIL, ASSIGNMENT_CREATED, etc.
    payload: dict[str, Any] = {}
    source: str = "system"
