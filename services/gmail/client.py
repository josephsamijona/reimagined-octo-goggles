"""
Gmail API client with OAuth2 authentication.
Handles reading, sending, and searching emails from the JHBridge operations inbox.
"""
import base64
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from services.config import get_settings
from services.gmail.parser import parse_message

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    """Wrapper around the Gmail API with OAuth2 credentials."""

    def __init__(self):
        self.settings = get_settings()
        self.service = None
        self.creds = None

    def authenticate(self):
        """Load or create OAuth2 credentials and build the Gmail service."""
        from googleapiclient.discovery import build

        creds = None
        token_path = self.settings.GMAIL_TOKEN_PATH
        creds_path = self.settings.GMAIL_CREDENTIALS_PATH

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    logger.warning(
                        f"Gmail credentials not found at {creds_path}. "
                        "Gmail integration will be unavailable."
                    )
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        self.creds = creds
        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail client authenticated successfully")
        return True

    @property
    def is_configured(self) -> bool:
        return self.service is not None

    # ── Async wrappers (for FastAPI routes) ──────────────────────

    async def list_messages(self, max_results: int = 20, label_ids: list[str] | None = None) -> list[dict]:
        """List recent messages from the inbox."""
        if not self.is_configured:
            return []
        try:
            params = {"userId": "me", "maxResults": max_results}
            if label_ids:
                params["labelIds"] = label_ids
            else:
                params["labelIds"] = ["INBOX"]

            result = self.service.users().messages().list(**params).execute()
            messages = result.get("messages", [])

            previews = []
            for msg_ref in messages:
                msg = self.service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                previews.append(parse_message(msg, preview_only=True))

            return previews
        except Exception as e:
            logger.error(f"Gmail list_messages error: {e}")
            return []

    async def get_message(self, message_id: str) -> dict:
        """Get full message content."""
        if not self.is_configured:
            return {}
        try:
            msg = self.service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()
            return parse_message(msg, preview_only=False)
        except Exception as e:
            logger.error(f"Gmail get_message error: {e}")
            return {}

    async def send_message(self, to: str, subject: str, body_html: str, reply_to_id: str = "") -> dict:
        """Send an email."""
        if not self.is_configured:
            return {}
        try:
            message = MIMEMultipart("alternative")
            message["to"] = to
            message["subject"] = subject
            message["from"] = "dispatch@jhbridgetranslation.com"

            if reply_to_id:
                # Fetch the original to get thread ID and Message-ID
                original = self.service.users().messages().get(
                    userId="me", id=reply_to_id, format="metadata",
                    metadataHeaders=["Message-ID"],
                ).execute()
                thread_id = original.get("threadId", "")
                headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
                if "Message-ID" in headers:
                    message["In-Reply-To"] = headers["Message-ID"]
                    message["References"] = headers["Message-ID"]

            message.attach(MIMEText(body_html, "html"))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {"raw": raw}
            if reply_to_id:
                body["threadId"] = thread_id

            sent = self.service.users().messages().send(userId="me", body=body).execute()
            return {"id": sent.get("id", ""), "threadId": sent.get("threadId", "")}
        except Exception as e:
            logger.error(f"Gmail send_message error: {e}")
            return {}

    async def search_messages(self, query: str, max_results: int = 10) -> list[dict]:
        """Search messages using Gmail query syntax."""
        if not self.is_configured:
            return []
        try:
            result = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            messages = result.get("messages", [])

            previews = []
            for msg_ref in messages:
                msg = self.service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                previews.append(parse_message(msg, preview_only=True))

            return previews
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return []

    # ── Sync wrappers (for ADK tools which run synchronously) ────

    def list_messages_sync(self, max_results: int = 20) -> list[dict]:
        if not self.is_configured:
            return []
        result = self.service.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        messages = result.get("messages", [])
        previews = []
        for msg_ref in messages:
            msg = self.service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            previews.append(parse_message(msg, preview_only=True))
        return previews

    def get_message_sync(self, message_id: str) -> dict:
        if not self.is_configured:
            return {}
        msg = self.service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        return parse_message(msg, preview_only=False)

    def send_message_sync(self, to: str, subject: str, body_html: str, reply_to_id: str = "") -> dict:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.send_message(to, subject, body_html, reply_to_id)
        )

    def search_messages_sync(self, query: str, max_results: int = 10) -> list[dict]:
        if not self.is_configured:
            return []
        result = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        previews = []
        for msg_ref in messages:
            msg = self.service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            previews.append(parse_message(msg, preview_only=True))
        return previews
