"""
Gmail tools for the ADK agent.
These wrap the Gmail client to provide read/send capabilities.
"""
import logging

logger = logging.getLogger(__name__)

# The Gmail client is initialized at app startup and set here
_gmail_client = None


def set_gmail_client(client):
    """Called at app startup to inject the Gmail client singleton."""
    global _gmail_client
    _gmail_client = client


def read_recent_emails(max_results: int = 20) -> dict:
    """Read the most recent emails from the JHBridge operations Gmail inbox.

    Args:
        max_results: Maximum number of emails to retrieve (default 20)

    Returns:
        List of emails with id, from, subject, snippet, date, labels
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not configured. Set up OAuth2 credentials first."}
    try:
        emails = _gmail_client.list_messages_sync(max_results=max_results)
        return {"status": "success", "count": len(emails), "emails": emails}
    except Exception as e:
        logger.error(f"Gmail read error: {e}")
        return {"status": "error", "error_message": str(e)}


def read_email_content(email_id: str) -> dict:
    """Read the full content of a specific email including body,
    attachments info, and headers.

    Args:
        email_id: The Gmail message ID
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not configured."}
    try:
        email = _gmail_client.get_message_sync(email_id)
        return {"status": "success", "email": email}
    except Exception as e:
        logger.error(f"Gmail read content error: {e}")
        return {"status": "error", "error_message": str(e)}


def send_email(to: str, subject: str, body_html: str, reply_to_id: str = "") -> dict:
    """Send an email from the JHBridge operations inbox.

    Args:
        to: Recipient email address
        subject: Email subject line
        body_html: HTML body content
        reply_to_id: Optional Gmail message ID to reply to (thread)
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not configured."}
    try:
        result = _gmail_client.send_message_sync(
            to=to, subject=subject, body_html=body_html, reply_to_id=reply_to_id
        )
        return {"status": "success", "message_id": result.get("id", ""), "thread_id": result.get("threadId", "")}
    except Exception as e:
        logger.error(f"Gmail send error: {e}")
        return {"status": "error", "error_message": str(e)}


def search_emails(query: str, max_results: int = 10) -> dict:
    """Search emails using Gmail search syntax.

    Args:
        query: Gmail search query (e.g., 'from:client@bmc.org subject:interpreter')
        max_results: Maximum results to return
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not configured."}
    try:
        emails = _gmail_client.search_messages_sync(query=query, max_results=max_results)
        return {"status": "success", "count": len(emails), "emails": emails}
    except Exception as e:
        logger.error(f"Gmail search error: {e}")
        return {"status": "error", "error_message": str(e)}
