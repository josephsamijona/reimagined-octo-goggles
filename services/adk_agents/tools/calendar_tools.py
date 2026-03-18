"""
Google Calendar tools for the ADK agent.
"""
import logging

logger = logging.getLogger(__name__)

# Calendar client is injected at app startup
_calendar_client = None


def set_calendar_client(client):
    """Called at app startup to inject the Calendar client singleton."""
    global _calendar_client
    _calendar_client = client


def sync_assignment_to_calendar(assignment_id: int) -> dict:
    """Sync an assignment to Google Calendar, creating a calendar event
    with all details including client, interpreter, location, and languages.

    Args:
        assignment_id: The assignment's database ID
    """
    if not _calendar_client:
        return {"status": "error", "error_message": "Calendar client not configured. Set up OAuth2 credentials first."}
    try:
        event = _calendar_client.sync_assignment(assignment_id)
        return {
            "status": "success",
            "event_id": event.get("id", ""),
            "link": event.get("htmlLink", ""),
            "message": f"Assignment {assignment_id} synced to calendar",
        }
    except Exception as e:
        logger.error(f"Calendar sync error: {e}")
        return {"status": "error", "error_message": str(e)}


def get_calendar_events(date_start: str, date_end: str) -> dict:
    """Get all calendar events between two dates.

    Args:
        date_start: Start date in YYYY-MM-DD format
        date_end: End date in YYYY-MM-DD format
    """
    if not _calendar_client:
        return {"status": "error", "error_message": "Calendar client not configured."}
    try:
        events = _calendar_client.list_events(date_start, date_end)
        return {"status": "success", "count": len(events), "events": events}
    except Exception as e:
        logger.error(f"Calendar list error: {e}")
        return {"status": "error", "error_message": str(e)}
