"""
Maps JHBridge Assignment data to Google Calendar Event format.

Uses state-based timezone (shared/constants.py) so that interpreters in
California, Texas, etc. see events in their correct local time instead of
always Eastern.
"""
from shared.constants import tz_for_state


def assignment_to_calendar_event(assignment: dict) -> dict:
    """Convert an assignment dict (from queries.get_assignment_by_id) to a
    Google Calendar event body suitable for the Calendar API.

    Args:
        assignment: Dict with keys: id, service_type, source_language,
            target_language, location, city, state, zip_code, start_time,
            end_time, client, interpreter, interpreter_email, notes,
            special_requirements, interpreter_rate, status.

    Returns:
        A dict ready to pass to ``calendar.events().insert(body=...)``.
    """
    state = assignment.get("state", "")
    timezone = tz_for_state(state)

    summary = (
        f"[JHBridge] {assignment.get('service_type', 'Assignment')} — "
        f"{assignment.get('source_language', '')} → {assignment.get('target_language', '')}"
    )

    location_parts = [
        assignment.get("location", ""),
        assignment.get("city", ""),
        state,
        assignment.get("zip_code", ""),
    ]
    location = ", ".join(p for p in location_parts if p)

    rate = assignment.get("interpreter_rate", "")
    special = assignment.get("special_requirements", "")

    description_lines = [
        f"Assignment #{assignment.get('id', '')}",
        f"Client: {assignment.get('client', 'N/A')}",
        f"Interpreter: {assignment.get('interpreter', 'TBD')}",
        f"Status: {assignment.get('status', '')}",
        f"Address: {location}",
    ]
    if rate:
        description_lines.append(f"Rate: ${rate}/hr")
    if special:
        description_lines.append(f"Special requirements: {special}")
    if assignment.get("notes"):
        description_lines.append(f"Notes: {assignment['notes']}")

    event = {
        "summary": summary,
        "location": location,
        "description": "\n".join(description_lines),
        "start": {
            "dateTime": assignment.get("start_time", ""),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": assignment.get("end_time", ""),
            "timeZone": timezone,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "popup", "minutes": 15},
            ],
        },
    }

    # Add interpreter as attendee when email is available
    interpreter_email = assignment.get("interpreter_email", "")
    if interpreter_email:
        event["attendees"] = [
            {
                "email": interpreter_email,
                "displayName": assignment.get("interpreter", ""),
            }
        ]

    return event
