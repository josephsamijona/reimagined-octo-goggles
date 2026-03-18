"""
Google Calendar API client with OAuth2 authentication.
Syncs JHBridge assignments to Google Calendar.
"""
import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from services.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarClient:
    """Wrapper around the Google Calendar API with OAuth2 credentials."""

    def __init__(self):
        self.settings = get_settings()
        self.service = None
        self.creds = None

    def authenticate(self):
        """Load or create OAuth2 credentials and build the Calendar service."""
        from googleapiclient.discovery import build

        creds = None
        token_path = self.settings.GMAIL_TOKEN_PATH  # Shared token file
        creds_path = self.settings.GMAIL_CREDENTIALS_PATH

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    logger.warning(
                        f"Calendar credentials not found at {creds_path}. "
                        "Calendar integration will be unavailable."
                    )
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        self.creds = creds
        self.service = build("calendar", "v3", credentials=creds)
        logger.info("Calendar client authenticated successfully")
        return True

    @property
    def is_configured(self) -> bool:
        return self.service is not None

    # ── Async wrappers ────────────────────────────────────────────

    async def create_event(self, event_body: dict) -> dict:
        """Create a calendar event and return it."""
        if not self.is_configured:
            return {}
        try:
            calendar_id = self.settings.CALENDAR_ID
            event = self.service.events().insert(
                calendarId=calendar_id, body=event_body
            ).execute()
            return {
                "event_id": event.get("id", ""),
                "html_link": event.get("htmlLink", ""),
            }
        except Exception as e:
            logger.error(f"Calendar create_event error: {e}")
            return {}

    async def get_events(
        self, time_min: str, time_max: str, max_results: int = 50
    ) -> list[dict]:
        """List calendar events in a time range (ISO 8601 strings)."""
        if not self.is_configured:
            return []
        try:
            calendar_id = self.settings.CALENDAR_ID
            result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = []
            for item in result.get("items", []):
                start = item.get("start", {})
                end = item.get("end", {})
                events.append({
                    "event_id": item.get("id", ""),
                    "title": item.get("summary", ""),
                    "start": start.get("dateTime", start.get("date", "")),
                    "end": end.get("dateTime", end.get("date", "")),
                    "location": item.get("location", ""),
                    "description": item.get("description", ""),
                    "html_link": item.get("htmlLink", ""),
                })
            return events
        except Exception as e:
            logger.error(f"Calendar get_events error: {e}")
            return []

    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event by ID."""
        if not self.is_configured:
            return False
        try:
            calendar_id = self.settings.CALENDAR_ID
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Calendar delete_event error: {e}")
            return False

    # ── Sync wrappers (for ADK tools) ─────────────────────────────

    def create_event_sync(self, event_body: dict) -> dict:
        if not self.is_configured:
            return {}
        calendar_id = self.settings.CALENDAR_ID
        event = self.service.events().insert(
            calendarId=calendar_id, body=event_body
        ).execute()
        return {
            "event_id": event.get("id", ""),
            "html_link": event.get("htmlLink", ""),
        }

    def get_events_sync(
        self, time_min: str, time_max: str, max_results: int = 50
    ) -> list[dict]:
        if not self.is_configured:
            return []
        calendar_id = self.settings.CALENDAR_ID
        result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            events.append({
                "event_id": item.get("id", ""),
                "title": item.get("summary", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
                "location": item.get("location", ""),
                "description": item.get("description", ""),
            })
        return events
