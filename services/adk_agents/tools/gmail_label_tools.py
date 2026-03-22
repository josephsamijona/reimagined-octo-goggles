"""
Gmail label and archiving tools for the ADK agent.
Used to organize the inbox after processing emails.
"""
import logging

logger = logging.getLogger(__name__)

_gmail_client = None


def set_gmail_client(client):
    global _gmail_client
    _gmail_client = client


def apply_label(email_id: str, label_name: str) -> dict:
    """Apply a Gmail label to an email (creates the label if it doesn't exist).
    Use labels like 'Agent/Processed', 'Agent/Pending', 'Agent/Failed' to
    organize the inbox after the agent processes emails.

    Args:
        email_id: Gmail message ID
        label_name: Label name, e.g. 'Agent/Processed'
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not available"}
    try:
        result = _gmail_client.apply_label_sync(email_id, label_name)
        return {"status": "success", "label_applied": label_name, "result": result}
    except Exception as e:
        logger.error(f"apply_label error: {e}")
        return {"status": "error", "error_message": str(e)}


def archive_email(email_id: str) -> dict:
    """Archive an email (removes from Inbox, keeps in All Mail).
    Use this after successfully processing an email to keep the inbox clean.

    Args:
        email_id: Gmail message ID
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not available"}
    try:
        result = _gmail_client.archive_message_sync(email_id)
        return {"status": "success", "archived": True, "result": result}
    except Exception as e:
        logger.error(f"archive_email error: {e}")
        return {"status": "error", "error_message": str(e)}


def mark_email_read(email_id: str) -> dict:
    """Mark an email as read in Gmail.

    Args:
        email_id: Gmail message ID
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not available"}
    try:
        result = _gmail_client.mark_as_read_sync(email_id)
        return {"status": "success", "marked_read": True}
    except Exception as e:
        logger.error(f"mark_email_read error: {e}")
        return {"status": "error", "error_message": str(e)}
