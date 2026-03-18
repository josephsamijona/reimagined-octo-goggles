"""
Email parsing utilities — extract headers, decode body, handle multipart messages.
"""
import base64
import re
from datetime import datetime
from email.utils import parsedate_to_datetime


def parse_message(msg: dict, preview_only: bool = True) -> dict:
    """Parse a Gmail API message into a clean dict."""
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    # Parse "From" header → name + email
    from_raw = headers.get("From", "")
    from_name, from_email = _parse_from(from_raw)

    # Parse date
    date_str = headers.get("Date", "")
    try:
        received_at = parsedate_to_datetime(date_str).isoformat()
    except Exception:
        received_at = date_str

    result = {
        "gmail_id": msg.get("id", ""),
        "thread_id": msg.get("threadId", ""),
        "from_email": from_email,
        "from_name": from_name,
        "subject": headers.get("Subject", "(no subject)"),
        "snippet": msg.get("snippet", ""),
        "received_at": received_at,
        "labels": msg.get("labelIds", []),
        "has_attachments": _has_attachments(payload),
    }

    if not preview_only:
        body_html, body_text = _extract_body(payload)
        result["body_html"] = body_html
        result["body_text"] = body_text
        result["to"] = [addr.strip() for addr in headers.get("To", "").split(",") if addr.strip()]
        result["cc"] = [addr.strip() for addr in headers.get("Cc", "").split(",") if addr.strip()]
        result["attachments"] = _extract_attachments(payload)

    return result


def _parse_from(from_raw: str) -> tuple[str, str]:
    """Parse 'Name <email@example.com>' into (name, email)."""
    match = re.match(r'^"?([^"<]*)"?\s*<?([^>]+)>?$', from_raw.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
        return name, email
    return "", from_raw.strip()


def _extract_body(payload: dict) -> tuple[str, str]:
    """Recursively extract HTML and plain text body from message payload."""
    body_html = ""
    body_text = ""

    mime_type = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            body_html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    elif mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    elif parts:
        for part in parts:
            html, text = _extract_body(part)
            if html and not body_html:
                body_html = html
            if text and not body_text:
                body_text = text

    # Fallback: direct body data
    if not body_html and not body_text:
        data = payload.get("body", {}).get("data", "")
        if data:
            body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return body_html, body_text


def _has_attachments(payload: dict) -> bool:
    """Check if message has file attachments."""
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("filename"):
            return True
        if part.get("parts"):
            if _has_attachments(part):
                return True
    return False


def _extract_attachments(payload: dict) -> list[dict]:
    """Extract attachment metadata (not the actual files)."""
    attachments = []
    parts = payload.get("parts", [])
    for part in parts:
        filename = part.get("filename", "")
        if filename:
            attachments.append({
                "filename": filename,
                "mime_type": part.get("mimeType", ""),
                "size": part.get("body", {}).get("size", 0),
                "attachment_id": part.get("body", {}).get("attachmentId", ""),
            })
        if part.get("parts"):
            attachments.extend(_extract_attachments(part))
    return attachments
