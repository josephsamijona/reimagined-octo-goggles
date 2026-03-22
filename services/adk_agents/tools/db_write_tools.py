"""
Write-operation tools for the ADK agent.
All writes go through Django DRF API to preserve signals and business logic.
"""
import logging

import httpx

from services.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.DJANGO_ADMIN_TOKEN}",
        "Content-Type": "application/json",
    }


def _post(path: str, payload: dict) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{settings.DJANGO_API_URL}{path}", json=payload, headers=_headers())
        if resp.status_code in (200, 201):
            return {"status": "success", "data": resp.json()}
        return {"status": "error", "error_message": f"API {resp.status_code}: {resp.text[:300]}"}
    except Exception as e:
        logger.error(f"HTTP POST {path} error: {e}")
        return {"status": "error", "error_message": str(e)}


def _patch(path: str, payload: dict) -> dict:
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.patch(f"{settings.DJANGO_API_URL}{path}", json=payload, headers=_headers())
        if resp.status_code in (200, 201):
            return {"status": "success", "data": resp.json()}
        return {"status": "error", "error_message": f"API {resp.status_code}: {resp.text[:300]}"}
    except Exception as e:
        logger.error(f"HTTP PATCH {path} error: {e}")
        return {"status": "error", "error_message": str(e)}


def create_client(
    email: str,
    first_name: str,
    last_name: str,
    company_name: str,
    phone: str = "",
    city: str = "",
    state: str = "",
) -> dict:
    """Create a new client account in the system.
    This creates both the User and Client records in one call.

    Args:
        email: Client's email address (required)
        first_name: First name of primary contact
        last_name: Last name of primary contact
        company_name: Company or organization name
        phone: Phone number (optional)
        city: City (optional)
        state: US state code, e.g. MA (optional)
    """
    return _post("/clients/", {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "company_name": company_name,
        "phone": phone,
        "city": city,
        "state": state,
    })


def create_quote_request(
    client_id: int,
    service_type_id: int,
    source_language_id: int,
    target_language_id: int,
    requested_date: str,
    location: str,
    city: str,
    state: str,
    duration_hours: int = 2,
    notes: str = "",
) -> dict:
    """Create a quote request for a client.

    Args:
        client_id: Client's database ID
        service_type_id: Service type ID
        source_language_id: Source language ID
        target_language_id: Target language ID
        requested_date: ISO datetime string e.g. '2026-03-25T09:00:00'
        location: Street address
        city: City
        state: US state code
        duration_hours: Estimated duration in hours (default 2)
        notes: Special requirements
    """
    return _post("/quote-requests/", {
        "client": client_id,
        "service_type": service_type_id,
        "source_language": source_language_id,
        "target_language": target_language_id,
        "requested_date": requested_date,
        "location": location,
        "city": city,
        "state": state,
        "duration": duration_hours,
        "special_requirements": notes,
    })


def enqueue_agent_action(
    gmail_id: str,
    email_subject: str,
    email_from: str,
    category: str,
    confidence: float,
    extracted_data: dict,
    action_type: str,
    action_payload: dict,
    ai_reasoning: str = "",
) -> dict:
    """Create an agent queue item pending admin approval.
    Use this after extracting data from an email to propose an action
    that requires admin confirmation before execution.

    Args:
        gmail_id: Gmail message ID of the source email
        email_subject: Subject line of the email
        email_from: Sender email address
        category: Email category (INTERPRETATION/QUOTE/HIRING/INVOICE/PAYSLIP/PAYMENT/OTHER)
        confidence: AI confidence score 0.0-1.0
        extracted_data: Structured data extracted from the email
        action_type: Proposed action (CREATE_ASSIGNMENT/SEND_ONBOARDING/RECORD_INVOICE/etc.)
        action_payload: Exact parameters for the proposed action
        ai_reasoning: Explanation of why this action is recommended
    """
    return _post("/agent-queue/", {
        "gmail_id": gmail_id,
        "email_subject": email_subject,
        "email_from": email_from,
        "category": category,
        "confidence": confidence,
        "extracted_data": extracted_data,
        "action_type": action_type,
        "action_payload": action_payload,
        "ai_reasoning": ai_reasoning,
    })


def update_assignment_status(assignment_id: int, new_status: str) -> dict:
    """Update an assignment's status.

    Args:
        assignment_id: The assignment's database ID
        new_status: New status (PENDING/CONFIRMED/IN_PROGRESS/COMPLETED/CANCELLED)
    """
    return _patch(f"/assignments/{assignment_id}/", {"status": new_status})


def mark_email_log_processed(gmail_id: str, linked_entity_type: str = "", linked_entity_id: int = 0) -> dict:
    """Mark an EmailLog record as processed after the agent has handled it.

    Args:
        gmail_id: The Gmail message ID
        linked_entity_type: Type of entity created (assignment/quote_request/onboarding/etc.)
        linked_entity_id: ID of the created entity
    """
    payload: dict = {"is_processed": True}
    if linked_entity_type == "assignment":
        payload["linked_assignment_id"] = linked_entity_id
    elif linked_entity_type == "quote_request":
        payload["linked_quote_request_id"] = linked_entity_id
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.patch(
                f"{settings.DJANGO_API_URL.replace('/api/v1', '')}/gmail/messages/{gmail_id}/processed",
                json=payload,
                headers=_headers(),
            )
        if resp.status_code == 200:
            return {"status": "success"}
        return {"status": "error", "error_message": f"{resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
