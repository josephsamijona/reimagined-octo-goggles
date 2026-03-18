"""
FastAPI routes for Gmail integration.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from services.schemas.email import (
    EmailFull,
    EmailLogOut,
    EmailReplyRequest,
    EmailSearchRequest,
    EmailSendRequest,
    InboxResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail"])

# Gmail client injected at startup
_gmail_client = None


def set_gmail_client(client):
    global _gmail_client
    _gmail_client = client


def _require_client():
    if not _gmail_client or not _gmail_client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Gmail integration not configured. Set up OAuth2 credentials.",
        )


@router.get("/inbox")
async def get_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List recent emails from the JHBridge operations inbox."""
    _require_client()
    emails = await _gmail_client.list_messages(max_results=page_size)
    return {
        "emails": emails,
        "total": len(emails),
        "page": page,
        "page_size": page_size,
    }


@router.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Get full content of a specific email."""
    _require_client()
    email = await _gmail_client.get_message(message_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


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

    # Get original email to build reply subject
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


@router.get("/sync")
async def force_sync():
    """Force-sync new emails from Gmail (normally runs every 2 minutes)."""
    from services.gmail.sync import sync_new_emails
    count = await sync_new_emails()
    return {"status": "synced", "new_emails": count}


@router.get("/search")
async def search_emails(
    q: str = Query(..., description="Gmail search query"),
    max_results: int = Query(10, ge=1, le=50),
):
    """Search emails using Gmail query syntax."""
    _require_client()
    results = await _gmail_client.search_messages(query=q, max_results=max_results)
    return {"count": len(results), "emails": results}
