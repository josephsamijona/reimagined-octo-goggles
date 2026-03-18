"""
FastAPI routes for Gmail integration.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.schemas.email import (
    AuthStatusResponse,
    EmailFull,
    EmailLogOut,
    EmailProcessedUpdate,
    EmailReadUpdate,
    EmailReplyRequest,
    EmailSearchRequest,
    EmailSendRequest,
    InboxResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail"])

# Injected at startup
_gmail_client = None
_db_factory = None


def set_gmail_client(client):
    global _gmail_client
    _gmail_client = client


def set_db_factory(factory):
    global _db_factory
    _db_factory = factory


def _require_client():
    if not _gmail_client or not _gmail_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Gmail integration not configured. Set up OAuth2 credentials.",
        )


# ── Auth status ──────────────────────────────────────────────────

@router.get("/auth-status", response_model=AuthStatusResponse)
async def auth_status():
    """Check whether Gmail OAuth credentials are configured."""
    if _gmail_client and _gmail_client.is_configured:
        return AuthStatusResponse(configured=True)
    return AuthStatusResponse(
        configured=False,
        reason="OAuth2 token not found or expired. Re-authenticate via credentials flow.",
    )


# ── Inbox — reads from EmailLog DB ──────────────────────────────

@router.get("/inbox", response_model=InboxResponse)
async def get_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="INTERPRETATION|QUOTE|HIRING|CONFIRMATION|PAYMENT|OTHER"),
    priority: Optional[str] = Query(None, description="URGENT|HIGH|MEDIUM|LOW"),
    is_read: Optional[bool] = Query(None),
    is_processed: Optional[bool] = Query(None),
    from_email: Optional[str] = Query(None),
):
    """List emails from the database with optional filters."""
    if not _db_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    from services.db import queries

    async with _db_factory() as db:
        rows, total = await queries.get_email_logs(
            db,
            category=category,
            priority=priority,
            is_read=is_read,
            is_processed=is_processed,
            from_email=from_email,
            page=page,
            page_size=page_size,
        )

    emails = [EmailLogOut.model_validate(row) for row in rows]
    return InboxResponse(emails=emails, total=total, page=page, page_size=page_size)


# ── Mark as read ─────────────────────────────────────────────────

@router.patch("/messages/{gmail_id}/read")
async def mark_read(gmail_id: str, body: EmailReadUpdate):
    """Mark an email as read or unread in the database."""
    if not _db_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    from services.db import queries

    async with _db_factory() as db:
        found = await queries.mark_email_read(db, gmail_id=gmail_id, is_read=body.is_read)

    if not found:
        raise HTTPException(status_code=404, detail="Email not found in database")

    return {"gmail_id": gmail_id, "is_read": body.is_read}


# ── Mark as processed ────────────────────────────────────────────

@router.patch("/messages/{gmail_id}/processed")
async def mark_processed(gmail_id: str, body: EmailProcessedUpdate):
    """Mark an email as processed in the database."""
    if not _db_factory:
        raise HTTPException(status_code=503, detail="Database not available")

    from services.db import queries

    async with _db_factory() as db:
        found = await queries.mark_email_processed(
            db, gmail_id=gmail_id, is_processed=body.is_processed
        )

    if not found:
        raise HTTPException(status_code=404, detail="Email not found in database")

    return {"gmail_id": gmail_id, "is_processed": body.is_processed}


# ── Message detail ───────────────────────────────────────────────

@router.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Get full content of a specific email from Gmail."""
    _require_client()
    email = await _gmail_client.get_message(message_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


# ── Send / Reply ─────────────────────────────────────────────────

@router.post("/send")
async def send_email(req: EmailSendRequest):
    """Send an email from the JHBridge operations inbox."""
    _require_client()
    result = await _gmail_client.send_message(
        to=req.to, subject=req.subject, body_html=req.body_html, reply_to_id=req.reply_to_id,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to send email")
    return {"status": "sent", **result}


@router.post("/reply/{message_id}")
async def reply_to_email(message_id: str, req: EmailReplyRequest):
    """Reply to a specific email."""
    _require_client()

    original = await _gmail_client.get_message(message_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original email not found")

    subject = original.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    result = await _gmail_client.send_message(
        to=original.get("from_email", ""),
        subject=subject,
        body_html=req.body_html,
        reply_to_id=message_id,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to send reply")
    return {"status": "sent", **result}


# ── Force sync ───────────────────────────────────────────────────

@router.get("/sync")
async def force_sync():
    """Force-sync new emails from Gmail (normally runs every 2 minutes)."""
    from services.gmail.sync import sync_new_emails
    count = await sync_new_emails()
    return {"status": "synced", "new_emails": count}


# ── Search ───────────────────────────────────────────────────────

@router.get("/search")
async def search_emails(
    q: str = Query(..., description="Gmail search query"),
    max_results: int = Query(10, ge=1, le=50),
):
    """Search emails using Gmail query syntax."""
    _require_client()
    results = await _gmail_client.search_messages(query=q, max_results=max_results)
    return {"count": len(results), "emails": results}
