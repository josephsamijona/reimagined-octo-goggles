"""
FastAPI routes for Google Calendar integration.
"""
import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from services.calendar_sync.mapper import assignment_to_calendar_event
from services.db.database import async_session_factory
from services.db import queries
from services.schemas.calendar import CalendarEvent, SyncAssignmentRequest, SyncAllTodayResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])

# Calendar client injected at startup
_calendar_client = None


def set_calendar_client(client):
    global _calendar_client
    _calendar_client = client


def _require_client():
    if not _calendar_client or not _calendar_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Calendar integration not configured. Set up OAuth2 credentials.",
        )


@router.get("/events")
async def list_events(
    start: str = Query(
        default="",
        description="Start date (YYYY-MM-DD), defaults to today",
    ),
    end: str = Query(
        default="",
        description="End date (YYYY-MM-DD), defaults to start + 7 days",
    ),
    max_results: int = Query(50, ge=1, le=200),
):
    """List Google Calendar events in a date range."""
    _require_client()

    if not start:
        start_dt = datetime.combine(date.today(), datetime.min.time())
    else:
        start_dt = datetime.fromisoformat(start)

    if not end:
        end_dt = start_dt + timedelta(days=7)
    else:
        end_dt = datetime.fromisoformat(end)

    time_min = start_dt.isoformat() + "Z"
    time_max = end_dt.isoformat() + "Z"

    events = await _calendar_client.get_events(
        time_min=time_min, time_max=time_max, max_results=max_results
    )
    return {"count": len(events), "events": events}


@router.post("/sync-assignment")
async def sync_assignment(req: SyncAssignmentRequest):
    """Sync a single assignment to Google Calendar."""
    _require_client()

    async with async_session_factory() as db:
        assignment = await queries.get_assignment_by_id(db, req.assignment_id)

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    event_body = assignment_to_calendar_event(assignment)
    result = await _calendar_client.create_event(event_body)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create calendar event")

    return {"status": "synced", **result}


@router.delete("/event/{event_id}")
async def delete_event(event_id: str):
    """Delete a Google Calendar event by its event ID."""
    _require_client()

    success = await _calendar_client.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete calendar event")
    return {"status": "deleted", "event_id": event_id}


@router.post("/sync-all-today")
async def sync_all_today():
    """Sync all of today's assignments to Google Calendar."""
    _require_client()

    async with async_session_factory() as db:
        assignments = await queries.get_active_assignments_today(db)

    synced = 0
    errors = []

    for a in assignments:
        # Need full assignment details for the mapper
        async with async_session_factory() as db:
            full = await queries.get_assignment_by_id(db, a["id"])
        if not full:
            errors.append(f"Assignment {a['id']} not found")
            continue

        event_body = assignment_to_calendar_event(full)
        result = await _calendar_client.create_event(event_body)
        if result:
            synced += 1
        else:
            errors.append(f"Failed to sync assignment {a['id']}")

    return {"synced": synced, "total": len(assignments), "errors": errors}
