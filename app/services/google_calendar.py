"""
Google Calendar sync for Assignments.

Uses a Google Service Account to create/update/delete events on the company's
private Google Calendar (works with basic Gmail accounts too — just share
the calendar with the service account email).

Setup (one-time):
  1. Go to Google Cloud Console → APIs & Services → Credentials
  2. Create a Service Account (or use an existing one)
  3. Download the JSON key
  4. Enable the Google Calendar API for the project
  5. In Google Calendar settings, share your calendar with the service
     account email (e.g. xyz@project.iam.gserviceaccount.com) and give
     it "Make changes to events" permission
  6. Set these env vars on Railway / .env:

       # Option A — base64 (recommended, avoids newline problems):
       #   Windows PowerShell:
       #     [Convert]::ToBase64String([IO.File]::ReadAllBytes("service-account.json"))
       #   Linux/Mac:
       #     base64 -w 0 < service-account.json
       GOOGLE_SERVICE_ACCOUNT_JSON_B64=eyJ0eXBlIjoic2VydmljZ...

       # Option B — raw JSON (must be a single line, no line breaks):
       GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

       GOOGLE_CALENDAR_ID=your.email@gmail.com

All functions run in a background thread so they never block HTTP responses.
Errors are caught and logged, never raised to the caller.
"""
import base64
import json
import logging
import threading

from django.conf import settings
from django.utils import timezone

from shared.constants import tz_for_state

logger = logging.getLogger(__name__)

# Google Calendar color IDs
_STATUS_COLOR = {
    'PENDING':     '5',   # banana (yellow)
    'CONFIRMED':   '9',   # blueberry (blue)
    'IN_PROGRESS': '3',   # grape (purple)
    'COMPLETED':   '2',   # sage (green)
    'CANCELLED':   '8',   # graphite
    'NO_SHOW':     '8',   # graphite
}

_TERMINAL_STATUSES = {'CANCELLED', 'NO_SHOW'}

# HTTP timeout for Google API calls (seconds)
_API_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Internal: build the Google Calendar API client (cached per-process)
# ---------------------------------------------------------------------------
_cached_service = None
_cached_calendar_id = None
_service_lock = threading.Lock()


def _load_service_account_info():
    """Load service account JSON — supports base64 (B64) or raw JSON env var."""
    # Try base64 first (recommended — avoids newline issues in .env)
    b64_value = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON_B64', '') or ''
    if b64_value:
        try:
            decoded = base64.b64decode(b64_value)
            return json.loads(decoded)
        except Exception:
            logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON_B64 is invalid — trying raw JSON")

    # Fallback: raw JSON string
    raw_json = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON', '{}')
    try:
        return json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return None


def _get_service():
    """Return (google calendar service, calendar_id) or (None, None).

    Thread-safe: uses a lock to avoid double-init.
    """
    global _cached_service, _cached_calendar_id

    if _cached_service is not None:
        return _cached_service, _cached_calendar_id

    with _service_lock:
        # Double-check after acquiring lock
        if _cached_service is not None:
            return _cached_service, _cached_calendar_id

        calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', '')
        if not calendar_id:
            logger.debug("GOOGLE_CALENDAR_ID not set — calendar sync disabled")
            return None, None

        info = _load_service_account_info()
        if not info:
            logger.warning("Google service account JSON not configured — calendar sync disabled")
            return None, None

        if info.get('type') != 'service_account':
            logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON is not a service_account key — calendar sync disabled")
            return None, None

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            import httplib2

            scopes = ['https://www.googleapis.com/auth/calendar']
            creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            http = httplib2.Http(timeout=_API_TIMEOUT)
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
            _cached_service, _cached_calendar_id = service, calendar_id
            logger.info("Google Calendar service initialized successfully")
            return service, calendar_id
        except ImportError:
            logger.warning("google-api-python-client not installed — calendar sync disabled")
            return None, None
        except Exception:
            logger.exception("Failed to build Google Calendar service")
            return None, None


def _invalidate_service_cache():
    """Clear the cached service (e.g. after an auth failure)."""
    global _cached_service, _cached_calendar_id
    with _service_lock:
        _cached_service = None
        _cached_calendar_id = None


# ---------------------------------------------------------------------------
# Build event body from an Assignment instance
# ---------------------------------------------------------------------------

def _build_event_body(assignment):
    """Convert an Assignment model instance to a Google Calendar event dict."""
    tz_name = tz_for_state(assignment.state)

    # Summary: "[STATUS] ServiceType — SourceLang → TargetLang"
    status_label = assignment.get_status_display() if hasattr(assignment, 'get_status_display') else assignment.status
    svc = str(assignment.service_type) if assignment.service_type else 'Assignment'
    src = str(assignment.source_language) if assignment.source_language else '?'
    tgt = str(assignment.target_language) if assignment.target_language else '?'
    summary = f"[{status_label}] {svc} — {src} → {tgt}"

    # Client info
    if assignment.client:
        client_display = str(assignment.client)
        client_phone = getattr(assignment.client, 'phone', '') or ''
        client_email = getattr(assignment.client, 'email', '') or ''
        # Try to get from the related User
        if not client_phone and hasattr(assignment.client, 'user'):
            client_phone = getattr(assignment.client.user, 'phone', '') or ''
        if not client_email and hasattr(assignment.client, 'user'):
            client_email = getattr(assignment.client.user, 'email', '') or ''
    else:
        client_display = assignment.client_name or 'N/A'
        client_phone = assignment.client_phone or ''
        client_email = assignment.client_email or ''

    # Interpreter info
    if assignment.interpreter and hasattr(assignment.interpreter, 'user'):
        interp_name = assignment.interpreter.user.get_full_name() or assignment.interpreter.user.username
        interp_phone = getattr(assignment.interpreter.user, 'phone', '') or ''
        interp_email = assignment.interpreter.user.email or ''
    else:
        interp_name = 'Unassigned'
        interp_phone = ''
        interp_email = ''

    # Location string
    location_parts = [p for p in [
        assignment.location,
        assignment.city,
        assignment.state,
        assignment.zip_code,
    ] if p]
    location_str = ', '.join(location_parts)

    # Description with all relevant details
    lines = [
        f"Client: {client_display}",
    ]
    if client_phone:
        lines.append(f"Client Phone: {client_phone}")
    if client_email:
        lines.append(f"Client Email: {client_email}")
    lines.append(f"Interpreter: {interp_name}")
    if interp_phone:
        lines.append(f"Interpreter Phone: {interp_phone}")
    if interp_email:
        lines.append(f"Interpreter Email: {interp_email}")
    lines.append(f"Service: {svc}")
    lines.append(f"Languages: {src} → {tgt}")
    lines.append(f"Location: {location_str}")
    lines.append(f"Rate: ${assignment.interpreter_rate}/hr" if assignment.interpreter_rate else "")
    lines.append(f"Status: {status_label}")
    if assignment.notes:
        lines.append(f"Notes: {assignment.notes[:500]}")
    if assignment.special_requirements:
        lines.append(f"Special Requirements: {assignment.special_requirements[:500]}")

    description = '\n'.join(line for line in lines if line)

    # No attendees — service accounts on basic Gmail cannot invite attendees.
    # Both admins see events by sharing the calendar directly.

    event = {
        'summary': summary,
        'location': location_str,
        'description': description,
        'start': {
            'dateTime': assignment.start_time.isoformat(),
            'timeZone': tz_name,
        },
        'end': {
            'dateTime': assignment.end_time.isoformat(),
            'timeZone': tz_name,
        },
        'colorId': _STATUS_COLOR.get(assignment.status, '8'),
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},
                {'method': 'popup', 'minutes': 15},
            ],
        },
        'extendedProperties': {
            'private': {
                'assignment_id': str(assignment.pk),
                'jhbridge': 'true',
            },
        },
    }

    return event


# ---------------------------------------------------------------------------
# Public API — called from signals via background thread
# ---------------------------------------------------------------------------

def schedule_sync(assignment_pk):
    """Schedule a calendar sync in a background daemon thread.

    This is the main entry point called from signals. It:
    - Returns immediately (non-blocking for the HTTP response)
    - Runs the actual Google API call in a background thread
    - Re-fetches the assignment from DB inside the thread (thread-safe ORM usage)
    """
    service, _ = _get_service()
    if service is None:
        return  # Calendar not configured — skip without spawning a thread

    thread = threading.Thread(
        target=_sync_worker,
        args=(assignment_pk,),
        daemon=True,
        name=f"gcal-sync-{assignment_pk}",
    )
    thread.start()


def _sync_worker(assignment_pk):
    """Background worker: re-fetch assignment and sync to Google Calendar.

    Runs in a daemon thread. All exceptions are caught — never crashes.
    """
    try:
        from django.db import close_old_connections
        close_old_connections()

        from app.models import Assignment
        assignment = (
            Assignment.objects
            .select_related(
                'client', 'client__user',
                'interpreter', 'interpreter__user',
                'service_type', 'source_language', 'target_language',
            )
            .filter(pk=assignment_pk)
            .first()
        )

        if assignment is None:
            logger.warning("Calendar sync: Assignment #%s not found", assignment_pk)
            return

        # Validate required fields
        if not assignment.start_time or not assignment.end_time:
            logger.debug("Calendar sync skipped: Assignment #%s has no start/end time", assignment_pk)
            _mark_sync_status(assignment, 'SKIPPED')
            return

        _do_sync(assignment)

    except Exception:
        logger.exception("Calendar sync thread crashed for Assignment #%s", assignment_pk)
    finally:
        try:
            from django.db import close_old_connections
            close_old_connections()
        except Exception:
            pass


def _do_sync(assignment):
    """Actual sync logic — create, update, or delete the calendar event."""
    service, calendar_id = _get_service()
    if service is None:
        return

    try:
        if assignment.status in _TERMINAL_STATUSES:
            _handle_terminal(service, calendar_id, assignment)
        elif assignment.gcal_event_id:
            _update_event(service, calendar_id, assignment)
        else:
            _create_event(service, calendar_id, assignment)
    except Exception:
        logger.exception("Calendar sync error for Assignment #%s", assignment.pk)
        _mark_sync_status(assignment, 'FAILED')


def _create_event(service, calendar_id, assignment):
    body = _build_event_body(assignment)
    event = service.events().insert(
        calendarId=calendar_id,
        body=body,
        sendUpdates='none',
    ).execute()

    event_id = event.get('id', '')
    logger.info("Created calendar event %s for Assignment #%s", event_id, assignment.pk)

    from app.models import Assignment
    Assignment.objects.filter(pk=assignment.pk).update(
        gcal_event_id=event_id,
        gcal_sync_status='SYNCED',
        gcal_synced_at=timezone.now(),
    )


def _update_event(service, calendar_id, assignment):
    body = _build_event_body(assignment)
    try:
        service.events().update(
            calendarId=calendar_id,
            eventId=assignment.gcal_event_id,
            body=body,
            sendUpdates='none',
        ).execute()
    except Exception as exc:
        # If event was deleted from Google Calendar, re-create it
        if _is_not_found(exc):
            logger.info(
                "Calendar event %s not found (deleted?), re-creating for Assignment #%s",
                assignment.gcal_event_id, assignment.pk,
            )
            _create_event(service, calendar_id, assignment)
            return
        raise

    logger.info("Updated calendar event %s for Assignment #%s", assignment.gcal_event_id, assignment.pk)

    from app.models import Assignment
    Assignment.objects.filter(pk=assignment.pk).update(
        gcal_sync_status='SYNCED',
        gcal_synced_at=timezone.now(),
    )


def _handle_terminal(service, calendar_id, assignment):
    """Delete event for cancelled / no-show assignments."""
    if assignment.gcal_event_id:
        try:
            service.events().delete(
                calendarId=calendar_id,
                eventId=assignment.gcal_event_id,
                sendUpdates='none',
            ).execute()
            logger.info("Deleted calendar event %s for Assignment #%s", assignment.gcal_event_id, assignment.pk)
        except Exception:
            logger.warning("Could not delete calendar event %s — may already be deleted", assignment.gcal_event_id)

        from app.models import Assignment
        Assignment.objects.filter(pk=assignment.pk).update(
            gcal_sync_status='DELETED',
            gcal_synced_at=timezone.now(),
        )
    else:
        from app.models import Assignment
        Assignment.objects.filter(pk=assignment.pk).update(
            gcal_sync_status='SKIPPED',
        )


def _mark_sync_status(assignment, status):
    """Utility to mark sync status without triggering signals."""
    try:
        from app.models import Assignment
        Assignment.objects.filter(pk=assignment.pk).update(
            gcal_sync_status=status,
        )
    except Exception:
        logger.exception("Failed to update gcal_sync_status for Assignment #%s", assignment.pk)


def _is_not_found(exc):
    """Check if a Google API exception is a 404 Not Found."""
    try:
        from googleapiclient.errors import HttpError
        return isinstance(exc, HttpError) and exc.resp.status == 404
    except ImportError:
        return False


# Keep backward compat — old name still works if called directly
sync_assignment_to_calendar = _do_sync
