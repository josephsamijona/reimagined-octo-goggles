"""
Assignment and onboarding tools for the ADK agent.
Write operations go through Django DRF API to preserve signals/business logic.
"""
import logging

import httpx

from services.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_admin_headers() -> dict:
    """Return auth headers for calling Django DRF API."""
    return {
        "Authorization": f"Bearer {settings.DJANGO_ADMIN_TOKEN}",
        "Content-Type": "application/json",
    }


def create_assignment(
    client_id: int,
    interpreter_id: int,
    service_type_id: int,
    source_language_id: int,
    target_language_id: int,
    date: str,
    start_time: str,
    end_time: str,
    location: str,
    city: str,
    state: str,
    zip_code: str,
    rate: float,
    notes: str = "",
) -> dict:
    """Create a new interpretation assignment and notify the interpreter.
    This will create the assignment in the database and trigger an email
    with calendar invitation to the interpreter.

    Args:
        client_id: The client's database ID
        interpreter_id: The interpreter's database ID
        service_type_id: Service type ID (from database)
        source_language_id: Source language ID
        target_language_id: Target language ID
        date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        location: Street address
        city: City name
        state: US state code
        zip_code: ZIP code
        rate: Hourly rate in USD
        notes: Special requirements or notes
    """
    try:
        payload = {
            "client": client_id,
            "interpreter": interpreter_id,
            "service_type": service_type_id,
            "source_language": source_language_id,
            "target_language": target_language_id,
            "start_time": f"{date}T{start_time}:00",
            "end_time": f"{date}T{end_time}:00",
            "location": location,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "interpreter_rate": rate,
            "minimum_hours": 2,
            "status": "PENDING",
            "notes": notes,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{settings.DJANGO_API_URL}/assignments/",
                json=payload,
                headers=_get_admin_headers(),
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {"status": "success", "assignment_id": data.get("id"), "details": data}
        else:
            return {"status": "error", "error_message": f"API returned {resp.status_code}: {resp.text}"}

    except Exception as e:
        logger.error(f"Create assignment error: {e}")
        return {"status": "error", "error_message": str(e)}


def create_quote_estimate(
    service_type: str,
    language: str,
    duration_hours: float,
    rate_per_hour: float,
    is_medical_legal: bool = False,
    is_weekend: bool = False,
    is_urgent: bool = False,
    travel_miles: float = 0,
) -> dict:
    """Generate a quote estimate for interpretation services.
    Uses the JHBridge rate card and pricing rules.

    Args:
        service_type: Type of service (Medical, Legal, Conference, etc.)
        language: Language pair description (e.g., 'Portuguese to English')
        duration_hours: Estimated duration in hours
        rate_per_hour: Base rate per hour in USD
        is_medical_legal: Whether this is a medical or legal assignment (10% premium)
        is_weekend: Whether this is on a weekend/holiday (25% surcharge)
        is_urgent: Whether this is same-day/urgent request (50% surcharge)
        travel_miles: Miles beyond 30-mile radius (mileage reimbursement at $0.67/mile)
    """
    minimum_hours = 2.0
    billable_hours = max(duration_hours, minimum_hours)
    subtotal = billable_hours * rate_per_hour

    premiums = {}
    total_surcharge = 0

    if is_medical_legal:
        premium = subtotal * 0.10
        premiums["medical_legal_premium"] = round(premium, 2)
        total_surcharge += premium

    if is_weekend:
        surcharge = subtotal * 0.25
        premiums["weekend_surcharge"] = round(surcharge, 2)
        total_surcharge += surcharge

    if is_urgent:
        surcharge = subtotal * 0.50
        premiums["urgent_surcharge"] = round(surcharge, 2)
        total_surcharge += surcharge

    if travel_miles > 0:
        mileage = travel_miles * 0.67
        premiums["mileage_reimbursement"] = round(mileage, 2)
        total_surcharge += mileage

    total = subtotal + total_surcharge

    return {
        "status": "success",
        "estimate": {
            "service_type": service_type,
            "language": language,
            "base_rate_per_hour": rate_per_hour,
            "billable_hours": billable_hours,
            "minimum_hours_applied": duration_hours < minimum_hours,
            "subtotal": round(subtotal, 2),
            "premiums": premiums,
            "total": round(total, 2),
            "valid_for_days": 30,
            "notes": f"Estimate for {language} {service_type} interpretation. "
                     f"Minimum charge: {minimum_hours}h. Valid for 30 days.",
        },
    }


def create_onboarding_invitation(
    email: str,
    first_name: str,
    last_name: str,
    phone: str = "",
) -> dict:
    """Send an onboarding invitation to a new interpreter candidate.
    This creates the invitation and automatically sends the welcome email
    with the onboarding link.

    Args:
        email: Candidate's email address
        first_name: First name
        last_name: Last name
        phone: Phone number (optional)
    """
    try:
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{settings.DJANGO_API_URL}/onboarding/invitations/",
                json=payload,
                headers=_get_admin_headers(),
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "status": "success",
                "invitation_id": data.get("id"),
                "invitation_number": data.get("invitation_number"),
                "message": f"Onboarding invitation sent to {email}",
            }
        else:
            return {"status": "error", "error_message": f"API returned {resp.status_code}: {resp.text}"}

    except Exception as e:
        logger.error(f"Create onboarding invitation error: {e}")
        return {"status": "error", "error_message": str(e)}
