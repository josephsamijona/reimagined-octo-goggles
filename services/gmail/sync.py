"""
Background Gmail sync — periodically checks for new emails,
classifies them with AI, saves to EmailLog, and broadcasts via WebSocket.
"""
import asyncio
import logging
from datetime import datetime, timezone

from services.db.database import async_session_factory
from services.db import queries

logger = logging.getLogger(__name__)

# References set at app startup
_gmail_client = None
_ai_router = None
_ws_broadcaster = None

SYNC_INTERVAL_SECONDS = 120  # 2 minutes


def configure_sync(gmail_client, broadcaster):
    """Inject dependencies at app startup."""
    global _gmail_client, _ws_broadcaster
    _gmail_client = gmail_client
    _ws_broadcaster = broadcaster


async def sync_new_emails():
    """Fetch new emails from Gmail, classify them, and save to DB."""
    if not _gmail_client or not _gmail_client.is_configured:
        logger.debug("Gmail sync skipped — client not configured")
        return 0

    try:
        # Get recent emails from Gmail
        emails = await _gmail_client.list_messages(max_results=10)
        if not emails:
            return 0

        synced = 0
        async with async_session_factory() as db:
            for email_preview in emails:
                gmail_id = email_preview.get("gmail_id", "")
                if not gmail_id:
                    continue

                # Check if already in DB
                from sqlalchemy import select
                from services.db.models import EmailLog
                existing = await db.execute(
                    select(EmailLog.id).where(EmailLog.gmail_id == gmail_id)
                )
                if existing.scalar_one_or_none():
                    continue

                # Get full email content for classification
                full_email = await _gmail_client.get_message(gmail_id)
                body_text = full_email.get("body_text", "") or full_email.get("snippet", "")
                body_preview = body_text[:500] if body_text else ""

                # Try to classify with AI (non-blocking, fallback to uncategorized)
                classification = await _classify_email_safe(email_preview, body_preview)

                # Parse received_at
                received_at_str = email_preview.get("received_at", "")
                try:
                    received_at = datetime.fromisoformat(received_at_str)
                except (ValueError, TypeError):
                    received_at = datetime.now(timezone.utc)

                # Save to EmailLog
                email_data = {
                    "gmail_id": gmail_id,
                    "gmail_thread_id": email_preview.get("thread_id", ""),
                    "from_email": email_preview.get("from_email", ""),
                    "from_name": email_preview.get("from_name", ""),
                    "subject": email_preview.get("subject", ""),
                    "body_preview": body_preview,
                    "received_at": received_at,
                    "category": classification.get("category"),
                    "priority": classification.get("priority"),
                    "ai_confidence": classification.get("confidence"),
                    "ai_extracted_data": classification.get("extracted_data", {}),
                    "ai_suggested_actions": classification.get("suggested_actions", []),
                    "has_attachments": email_preview.get("has_attachments", False),
                    "created_at": datetime.now(timezone.utc),
                }

                email_id = await queries.save_email_log(db, email_data)
                synced += 1

                # Broadcast via WebSocket
                if _ws_broadcaster:
                    await _ws_broadcaster.broadcast_event("email-updates", {
                        "type": "NEW_EMAIL",
                        "payload": {
                            "id": email_id,
                            "gmail_id": gmail_id,
                            "from_email": email_preview.get("from_email", ""),
                            "from_name": email_preview.get("from_name", ""),
                            "subject": email_preview.get("subject", ""),
                            "category": classification.get("category", "OTHER"),
                            "priority": classification.get("priority", "MEDIUM"),
                        },
                    })

        logger.info(f"Gmail sync: {synced} new emails processed")
        return synced

    except Exception as e:
        logger.error(f"Gmail sync error: {e}")
        return 0


async def _classify_email_safe(email_preview: dict, body_preview: str) -> dict:
    """Classify an email using the AI agent, with fallback on error."""
    try:
        from services.ai_agent.router import _invoke_agent, _parse_json_response

        prompt = (
            f"Classify this email. Use the email_classifier sub-agent.\n\n"
            f"From: {email_preview.get('from_name', '')} <{email_preview.get('from_email', '')}>\n"
            f"Subject: {email_preview.get('subject', '')}\n\n"
            f"{body_preview}"
        )
        response = await _invoke_agent(prompt)
        return _parse_json_response(response)
    except Exception as e:
        logger.warning(f"Email classification failed, using defaults: {e}")
        return {
            "category": "OTHER",
            "priority": "MEDIUM",
            "confidence": 0.0,
            "extracted_data": {},
            "suggested_actions": [],
        }


async def run_sync_loop():
    """Background task that syncs emails at regular intervals."""
    logger.info(f"Gmail sync loop started (interval: {SYNC_INTERVAL_SECONDS}s)")
    while True:
        try:
            await sync_new_emails()
        except Exception as e:
            logger.error(f"Gmail sync loop error: {e}")
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
