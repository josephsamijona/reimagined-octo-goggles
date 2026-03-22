"""
Document parsing tools for the ADK agent.
Handles PDF extraction from Gmail attachments and text parsing.
"""
import base64
import logging

logger = logging.getLogger(__name__)

_gmail_client = None


def set_gmail_client(client):
    global _gmail_client
    _gmail_client = client


def get_email_attachments(email_id: str) -> dict:
    """List all attachments for a specific email.

    Args:
        email_id: Gmail message ID

    Returns:
        List of attachments with filename, mime_type, size, and attachment_id
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not available"}
    try:
        attachments = _gmail_client.list_attachments_sync(email_id)
        return {"status": "success", "count": len(attachments), "attachments": attachments}
    except Exception as e:
        logger.error(f"get_email_attachments error: {e}")
        return {"status": "error", "error_message": str(e)}


def download_attachment_text(email_id: str, attachment_id: str, filename: str = "") -> dict:
    """Download an email attachment and extract its text content.
    Supports PDF files (extracts text using pdfplumber) and plain text files.

    Args:
        email_id: Gmail message ID
        attachment_id: Attachment ID from Gmail
        filename: Original filename (used to detect file type)
    """
    if not _gmail_client:
        return {"status": "error", "error_message": "Gmail client not available"}
    try:
        data = _gmail_client.download_attachment_sync(email_id, attachment_id)
        if not data:
            return {"status": "error", "error_message": "Attachment download failed"}

        raw_bytes = base64.urlsafe_b64decode(data + "==")
        text = ""

        if filename.lower().endswith(".pdf") or data[:5] == "JVBER":
            try:
                import io
                import pdfplumber
                with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                text = "\n".join(pages).strip()
            except ImportError:
                text = f"[PDF - pdfplumber not installed. Filename: {filename}, size: {len(raw_bytes)} bytes]"
            except Exception as e:
                logger.error(f"PDF extraction error: {e}")
                text = f"[PDF extraction failed: {e}]"
        else:
            try:
                text = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                text = f"[Binary file: {filename}]"

        return {
            "status": "success",
            "filename": filename,
            "text": text[:8000],  # cap at 8000 chars for LLM context
            "char_count": len(text),
        }

    except Exception as e:
        logger.error(f"download_attachment_text error: {e}")
        return {"status": "error", "error_message": str(e)}


def parse_invoice_fields(text: str) -> dict:
    """Extract structured invoice fields from raw text using keyword heuristics.
    Returns best-effort parsed fields — the LLM should validate and correct.

    Args:
        text: Raw text content from an invoice PDF
    """
    import re

    def find(patterns, default=""):
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return default

    invoice_number = find([
        r"invoice\s*#?\s*:?\s*([A-Z0-9\-]+)",
        r"inv[.\s]*no[.\s]*:?\s*([A-Z0-9\-]+)",
    ])
    amount = find([
        r"total\s*(?:due|amount)?\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"amount\s*due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"balance\s*due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ])
    due_date = find([
        r"due\s*date\s*:?\s*(\w+\s+\d+,?\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"payment\s*due\s*:?\s*(\w+\s+\d+,?\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ])
    company = find([
        r"from\s*:?\s*([A-Z][A-Za-z\s,\.]+(?:LLC|Inc|Corp|Ltd|Services|Group)?)",
        r"bill\s*from\s*:?\s*(.+)",
    ])

    return {
        "invoice_number": invoice_number,
        "amount": amount.replace(",", "") if amount else "",
        "due_date": due_date,
        "company": company,
        "raw_text_preview": text[:500],
    }


def parse_payslip_fields(text: str) -> dict:
    """Extract structured payslip fields from raw text.

    Args:
        text: Raw text content from a payslip PDF
    """
    import re

    def find(patterns, default=""):
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return default

    employee_name = find([
        r"employee\s*name\s*:?\s*([A-Za-z\s]+)",
        r"pay\s*to\s*:?\s*([A-Za-z\s]+)",
        r"name\s*:?\s*([A-Za-z\s]+)",
    ])
    gross_pay = find([
        r"gross\s*(?:pay|earnings)\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"total\s*earnings\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ])
    net_pay = find([
        r"net\s*pay\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"take\s*home\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ])
    period = find([
        r"pay\s*period\s*:?\s*(.+)",
        r"period\s*ending\s*:?\s*(.+)",
        r"period\s*:?\s*(.+)",
    ])

    return {
        "employee_name": employee_name,
        "gross_pay": gross_pay.replace(",", "") if gross_pay else "",
        "net_pay": net_pay.replace(",", "") if net_pay else "",
        "period": period,
        "raw_text_preview": text[:500],
    }
