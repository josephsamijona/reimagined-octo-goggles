"""
Google Calendar service — direct API v3 integration via service account.

Architecture:
- Credentials: service account JSON from settings.GOOGLE_SERVICE_ACCOUNT_JSON
- Target calendar: settings.GOOGLE_CALENDAR_ID (company operations calendar)
- S3 remains primary storage; calendar is a scheduling / visibility layer only
- All functions return a result dict {ok: bool, ...} — never raise to callers
- Callers (Celery tasks) inspect ok and update Assignment.gcal_sync_status

Setup (one-time):
1. Create service account in Google Cloud Console
2. Download JSON key → set GOOGLE_SERVICE_ACCOUNT_JSON env var (full JSON content)
3. Share the company calendar with the service account email
   (Calendar Settings → Share → "Make changes to events")
4. Set GOOGLE_CALENDAR_ID env var to the calendar's ID
"""
import json
import logging

from django.conf import settings
from django.utils import timezone

from shared.constants import STATE_TIMEZONES, DEFAULT_TZ_NAME

logger = logging.getLogger(__name__)

# Google Calendar colorId mapping by assignment status
_STATUS_COLOR = {
    'PENDING':     '5',   # yellow / banana
    'CONFIRMED':   '9',   # blue / blueberry
    'IN_PROGRESS': '3',   # purple / grape
    'COMPLETED':   '2',   # green / sage
    'CANCELLED':   '8',   # graphite
    'NO_SHOW':     '8',   # graphite
}

_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_calendar_service():
    """
    Build and return an authenticated Google Calendar API v3 service object.

    Reads GOOGLE_SERVICE_ACCOUNT_JSON from settings (raw JSON string),
    creates google.oauth2.service_account.Credentials, then calls
    googleapiclient.discovery.build('calendar', 'v3', credentials=creds).

    Returns:
        googleapiclient Resource or None (logs error, does not raise).
    """
    raw_json = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON', '{}')
    calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', '')

    if not calendar_id:
        logger.warning('GOOGLE_CALENDAR_ID is not set — calendar sync skipped')
        return None

    try:
        info = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error('GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON: %s', exc)
        return None

    if not info.get('type') == 'service_account':
        logger.warning('GOOGLE_SERVICE_ACCOUNT_JSON does not describe a service_account — skipped')
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=_CALENDAR_SCOPES,
        )
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.error('Failed to build Google Calendar service: %s', exc)
        return None


def _tz_for_state(state: str) -> str:
    """Return IANA timezone name for a US state code, default Eastern."""
    return STATE_TIMEZONES.get((state or '').upper().strip(), DEFAULT_TZ_NAME)


def _build_event_body(assignment) -> dict:
    """
    Convert an Assignment ORM instance to a Google Calendar event body dict.
    Pure function — no I/O.

    The extendedProperties.private.assignment_id anchors idempotency: tasks
    can query by this property to find existing events before creating new ones.
    """
    tz_name = _tz_for_state(assignment.state)

    # Interpreter info
    interp_name = ''
    interp_email = None
    if assignment.interpreter and assignment.interpreter.user:
        u = assignment.interpreter.user
        interp_name = f"{u.first_name} {u.last_name}".strip() or u.email
        interp_email = u.email

    # Client info
    if assignment.client:
        client_name = assignment.client.company_name or str(assignment.client)
    else:
        client_name = assignment.client_name or 'Unspecified Client'

    # Language pair
    src = getattr(assignment.source_language, 'name', '') if assignment.source_language else ''
    tgt = getattr(assignment.target_language, 'name', '') if assignment.target_language else ''
    lang_pair = f"{src} → {tgt}" if src or tgt else ''

    service_name = getattr(assignment.service_type, 'name', '') if assignment.service_type else ''

    summary = f"[JHBridge] {service_name} — {lang_pair}"
    if assignment.status != 'PENDING':
        summary = f"[{assignment.status}] {service_name} — {lang_pair}"

    location_parts = [p for p in [
        assignment.location,
        assignment.city,
        f"{assignment.state} {assignment.zip_code}".strip() if assignment.state else '',
    ] if p]
    location = ', '.join(location_parts)

    description_lines = [
        f"Mission #{assignment.id}",
        f"Status: {assignment.status}",
        f"Client: {client_name}",
        f"Interpreter: {interp_name}" if interp_name else 'Interpreter: Unassigned',
        f"Languages: {lang_pair}",
        f"Rate: ${assignment.interpreter_rate}/hr" if assignment.interpreter_rate else '',
    ]
    if assignment.notes:
        description_lines.append(f"Notes: {assignment.notes[:300]}")
    description = '\n'.join(l for l in description_lines if l)

    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': assignment.start_time.isoformat(),
            'timeZone': tz_name,
        },
        'end': {
            'dateTime': assignment.end_time.isoformat(),
            'timeZone': tz_name,
        },
        'colorId': _STATUS_COLOR.get(assignment.status, '5'),
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},
                {'method': 'popup', 'minutes': 15},
            ],
        },
        'extendedProperties': {
            'private': {
                'assignment_id': str(assignment.id),
                'jhbridge': 'true',
            },
        },
    }

    # Add interpreter as attendee if available
    if interp_email:
        event['attendees'] = [{'email': interp_email, 'displayName': interp_name}]

    return event


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_calendar_event(assignment) -> dict:
    """
    Create a new Google Calendar event for the assignment.

    Returns:
        {'ok': True, 'event_id': str, 'html_link': str} on success.
        {'ok': False, 'error': str} on failure.
    """
    service = _build_calendar_service()
    if service is None:
        return {'ok': False, 'error': 'not_configured'}

    body = _build_event_body(assignment)
    calendar_id = settings.GOOGLE_CALENDAR_ID

    try:
        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        logger.info('Assignment #%s created in Google Calendar: %s', assignment.id, event.get('htmlLink'))
        return {'ok': True, 'event_id': event['id'], 'html_link': event.get('htmlLink', '')}
    except Exception as exc:
        error_str = str(exc)
        if '403' in error_str:
            logger.error('Google Calendar permission/quota error for assignment #%s: %s', assignment.id, exc)
            return {'ok': False, 'error': 'permission'}
        if '429' in error_str:
            logger.warning('Google Calendar rate limited for assignment #%s', assignment.id)
            return {'ok': False, 'error': 'rate_limited'}
        logger.error('Google Calendar create failed for assignment #%s: %s', assignment.id, exc, exc_info=True)
        return {'ok': False, 'error': 'unknown'}


def update_calendar_event(assignment) -> dict:
    """
    Update an existing Google Calendar event.

    Falls back to create_calendar_event() if gcal_event_id is missing.
    On 404 (event deleted externally), recreates the event.

    Returns:
        {'ok': True, 'event_id': str, 'html_link': str} on success.
        {'ok': False, 'error': str} on failure.
    """
    if not assignment.gcal_event_id:
        return create_calendar_event(assignment)

    service = _build_calendar_service()
    if service is None:
        return {'ok': False, 'error': 'not_configured'}

    body = _build_event_body(assignment)
    calendar_id = settings.GOOGLE_CALENDAR_ID

    try:
        event = service.events().update(
            calendarId=calendar_id,
            eventId=assignment.gcal_event_id,
            body=body,
        ).execute()
        logger.info('Assignment #%s updated in Google Calendar', assignment.id)
        return {'ok': True, 'event_id': event['id'], 'html_link': event.get('htmlLink', '')}
    except Exception as exc:
        error_str = str(exc)
        if '404' in error_str:
            logger.warning(
                'Calendar event %s not found for assignment #%s — recreating',
                assignment.gcal_event_id, assignment.id,
            )
            return create_calendar_event(assignment)
        if '403' in error_str:
            logger.error('Google Calendar permission error updating assignment #%s: %s', assignment.id, exc)
            return {'ok': False, 'error': 'permission'}
        if '429' in error_str:
            return {'ok': False, 'error': 'rate_limited'}
        logger.error('Google Calendar update failed for assignment #%s: %s', assignment.id, exc, exc_info=True)
        return {'ok': False, 'error': 'unknown'}


def delete_calendar_event(event_id: str) -> dict:
    """
    Delete a Google Calendar event by its event ID.

    404 responses are treated as success (already deleted).

    Args:
        event_id: Google Calendar event ID string.

    Returns:
        {'ok': True} on success / 404.
        {'ok': False, 'error': str} on failure.
    """
    service = _build_calendar_service()
    if service is None:
        return {'ok': False, 'error': 'not_configured'}

    calendar_id = settings.GOOGLE_CALENDAR_ID

    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info('Calendar event %s deleted', event_id)
        return {'ok': True}
    except Exception as exc:
        if '404' in str(exc):
            logger.info('Calendar event %s already gone — treating as success', event_id)
            return {'ok': True}
        logger.error('Google Calendar delete failed for event %s: %s', event_id, exc, exc_info=True)
        return {'ok': False, 'error': 'unknown'}


def sync_assignment(assignment_id: int) -> dict:
    """
    High-level orchestrator called by Celery tasks.

    Logic:
    - CANCELLED/NO_SHOW + has event_id → delete event
    - CANCELLED + no event_id → mark SKIPPED, do nothing
    - Has event_id → update
    - No event_id → create
    - Updates Assignment gcal_* fields in-place (update_fields only)

    Args:
        assignment_id: Assignment primary key.

    Returns:
        Result dict from underlying create/update/delete call.
    """
    from app.models import Assignment

    try:
        assignment = Assignment.objects.select_related(
            'interpreter__user',
            'service_type',
            'source_language',
            'target_language',
            'client',
        ).get(pk=assignment_id)
    except Assignment.DoesNotExist:
        logger.warning('sync_assignment: Assignment #%s not found', assignment_id)
        return {'ok': False, 'error': 'not_found'}

    terminal_statuses = {Assignment.Status.CANCELLED, Assignment.Status.NO_SHOW}

    # --- Delete path ---
    if assignment.status in terminal_statuses:
        if assignment.gcal_event_id:
            result = delete_calendar_event(assignment.gcal_event_id)
            if result['ok']:
                Assignment.objects.filter(pk=assignment_id).update(
                    gcal_sync_status=Assignment.GCalSyncStatus.DELETED,
                    gcal_event_id=None,
                    gcal_synced_at=timezone.now(),
                )
            else:
                Assignment.objects.filter(pk=assignment_id).update(
                    gcal_sync_status=Assignment.GCalSyncStatus.FAILED,
                )
            return result
        else:
            Assignment.objects.filter(pk=assignment_id).update(
                gcal_sync_status=Assignment.GCalSyncStatus.SKIPPED,
            )
            return {'ok': True, 'skipped': True}

    # --- Create or Update path ---
    if assignment.gcal_event_id:
        result = update_calendar_event(assignment)
    else:
        result = create_calendar_event(assignment)

    if result['ok']:
        Assignment.objects.filter(pk=assignment_id).update(
            gcal_event_id=result.get('event_id', assignment.gcal_event_id),
            gcal_sync_status=Assignment.GCalSyncStatus.SYNCED,
            gcal_synced_at=timezone.now(),
        )
    else:
        Assignment.objects.filter(pk=assignment_id).update(
            gcal_sync_status=Assignment.GCalSyncStatus.FAILED,
        )

    return result
