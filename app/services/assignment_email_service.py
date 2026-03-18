"""
Standalone assignment email service.

Extracted from AssignmentAdminMixin so the same email logic is shared by:
  - The Django admin (via AssignmentAdminMixin, which delegates here)
  - The DRF API viewsets (confirm / cancel / complete / reassign actions)

All public functions are stateless — they take model instances and config
values as arguments; no ``self`` or ``request`` required.

Token URLs:
  Admin context  → request.build_absolute_uri(reverse('dbdint:assignment-accept', ...))
  API context    → settings.SITE_URL + reverse('dbdint:assignment-accept', ...)
  Both use the same token format so tokens are interchangeable.
"""
import logging
import uuid
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.utils import make_msgid

import icalendar
import pytz
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import BadSignature, Signer
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from app.utils.timezone import get_interpreter_timezone, BOSTON_TZ

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def generate_assignment_token(assignment_id: int, action: str) -> str:
    """Generate a signed, timestamped token for interpreter accept/decline links.

    Args:
        assignment_id: Primary key of the Assignment.
        action: ``'accept'`` or ``'decline'``.

    Returns:
        A Django-signed token string safe for use in URLs.
    """
    signer = Signer()
    timestamp = timezone.now().timestamp()
    token_data = f"{assignment_id}:{action}:{timestamp}:{uuid.uuid4()}"
    return signer.sign(token_data)


def verify_assignment_token(token: str, expected_action: str) -> int | None:
    """Verify a signed assignment token and return the assignment ID.

    Checks signature, intended action, and 24-hour expiry.

    Args:
        token: The signed token string from the email link.
        expected_action: ``'accept'`` or ``'decline'``.

    Returns:
        Integer assignment ID on success, ``None`` on any failure.
    """
    signer = Signer()
    try:
        data = signer.unsign(token)
        assignment_id, action, timestamp, _ = data.split(':', 3)

        if action != expected_action:
            return None

        token_time = datetime.fromtimestamp(float(timestamp), tz=pytz.UTC)
        if timezone.now() - token_time > timedelta(hours=24):
            logger.warning("Assignment token expired for id=%s action=%s", assignment_id, action)
            return None

        return int(assignment_id)
    except (BadSignature, ValueError):
        return None


# ---------------------------------------------------------------------------
# ICS calendar attachment
# ---------------------------------------------------------------------------

def generate_ics_calendar(assignment) -> bytes:
    """Generate an iCalendar (.ics) bytes payload for an assignment.

    Uses the interpreter's state timezone (via get_interpreter_timezone) so
    the event shows in their local time — not always Boston/Eastern.

    Args:
        assignment: Assignment model instance with interpreter, service_type,
            source_language, target_language, location, city, state, zip_code,
            start_time, end_time, interpreter_rate, special_requirements, client.

    Returns:
        Raw bytes of the .ics file.
    """
    interp_tz = (
        get_interpreter_timezone(assignment.interpreter)
        if assignment.interpreter
        else BOSTON_TZ
    )

    cal = icalendar.Calendar()
    cal.add('prodid', '-//JHBRIDGE Assignment System//EN')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')

    event = icalendar.Event()
    event.add('summary', f"Interpretation Assignment - {assignment.service_type.name}")

    # Convert to interpreter's local timezone for the ICS
    start_time = assignment.start_time.astimezone(interp_tz)
    end_time = assignment.end_time.astimezone(interp_tz)
    event.add('dtstart', start_time)
    event.add('dtend', end_time)

    # DTSTAMP / CREATED must be UTC per RFC 5545
    event.add('dtstamp', timezone.now().astimezone(pytz.UTC))
    event.add('created', timezone.now().astimezone(pytz.UTC))

    event.add(
        'location',
        f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}",
    )

    client_name = (
        assignment.client.company_name if assignment.client else assignment.client_name
    )
    description = (
        f"Client: {client_name}\n"
        f"Service: {assignment.service_type.name}\n"
        f"Languages: {assignment.source_language.name} → {assignment.target_language.name}\n"
        f"Location: {assignment.location}, {assignment.city}, "
        f"{assignment.state} {assignment.zip_code}\n"
        f"Special Requirements: {assignment.special_requirements or 'None'}\n"
        f"Rate: ${assignment.interpreter_rate}/hour"
    )
    event.add('description', description)
    event.add('uid', f"assignment-{assignment.id}@jhbridge.com")

    organizer = icalendar.vCalAddress(f"MAILTO:{settings.DEFAULT_FROM_EMAIL}")
    organizer.params['CN'] = "JHBridge System"
    event['organizer'] = organizer

    if assignment.interpreter and assignment.interpreter.user.email:
        attendee = icalendar.vCalAddress(f"MAILTO:{assignment.interpreter.user.email}")
        attendee.params['CN'] = assignment.interpreter.user.get_full_name()
        attendee.params['RSVP'] = 'TRUE'
        event.add('attendee', attendee)

    cal.add_component(event)
    return cal.to_ical()


# ---------------------------------------------------------------------------
# Template config
# ---------------------------------------------------------------------------

def get_email_template_config(email_type: str, assignment_id: int | None = None) -> dict:
    """Return subject, template path, and ICS flag for *email_type*.

    A unique ID is appended to every subject to prevent email client threading.

    Args:
        email_type: One of ``'new'``, ``'confirmed'``, ``'cancelled'``,
            ``'completed'``, ``'no_show'``.
        assignment_id: Optional assignment PK, included in the subject line.

    Returns:
        Dict with keys ``subject``, ``template``, ``include_calendar``.
    """
    unique_id = f"ID-{uuid.uuid4().hex[:8].upper()}"
    ref = f"#{assignment_id}" if assignment_id else ""

    configs = {
        'new': {
            'subject': _('New Assignment Available {0} - Action Required [{1}]').format(ref, unique_id),
            'template': 'emails/assignments/assignment_new.html',
            'include_calendar': False,
        },
        'confirmed': {
            'subject': _('Assignment Confirmation {0} [{1}]').format(ref, unique_id),
            'template': 'emails/assignments/assignment_confirmed.html',
            'include_calendar': True,
        },
        'cancelled': {
            'subject': _('Assignment Cancelled {0} [{1}]').format(ref, unique_id),
            'template': 'emails/assignments/assignment_cancelled.html',
            'include_calendar': False,
        },
        'completed': {
            'subject': _('Assignment Completed {0} [{1}]').format(ref, unique_id),
            'template': 'emails/assignments/assignment_completed.html',
            'include_calendar': False,
        },
        'no_show': {
            'subject': _('Assignment No-Show {0} [{1}]').format(ref, unique_id),
            'template': 'emails/assignments/assignment_no_show.html',
            'include_calendar': False,
        },
    }

    return configs.get(email_type, {
        'subject': _('Assignment Update {0} [{1}]').format(ref, unique_id),
        'template': 'emails/assignments/assignment_generic.html',
        'include_calendar': False,
    })


# ---------------------------------------------------------------------------
# Email context builder
# ---------------------------------------------------------------------------

def build_email_context(assignment, email_type: str, site_url: str) -> dict:
    """Build the template context dict for an assignment email.

    For the ``'new'`` type, accept/decline token URLs are generated using
    *site_url* as the base (works in both admin and API contexts).

    Args:
        assignment: Assignment model instance.
        email_type: Email type string (``'new'``, ``'confirmed'``, etc.).
        site_url: Base URL of the site, e.g. ``'https://portal.jhbridgetranslation.com'``.
            Used to build accept/decline links.

    Returns:
        Dict ready to pass to ``render_to_string``.
    """
    client_name = (
        assignment.client.company_name if assignment.client else assignment.client_name
    )
    client_phone = (
        assignment.client.user.phone
        if assignment.client and hasattr(assignment.client, 'user') and assignment.client.user.phone
        else assignment.client_phone
        if hasattr(assignment, 'client_phone') and assignment.client_phone
        else "Not provided"
    )

    context = {
        'interpreter_name': (
            f"{assignment.interpreter.user.first_name} {assignment.interpreter.user.last_name}"
        ),
        'assignment': assignment,
        'start_time': assignment.start_time,
        'end_time': assignment.end_time,
        'client_name': client_name,
        'client_phone': client_phone,
        'service_type': assignment.service_type.name,
        'location': (
            f"{assignment.location}, {assignment.city}, "
            f"{assignment.state} {assignment.zip_code}"
        ),
        'special_requirements': assignment.special_requirements or "None",
        'rate': assignment.interpreter_rate,
        'source_language': assignment.source_language.name,
        'target_language': assignment.target_language.name,
        'site_url': site_url.rstrip('/'),
    }

    if email_type == 'new':
        accept_token = generate_assignment_token(assignment.id, 'accept')
        decline_token = generate_assignment_token(assignment.id, 'decline')
        base = site_url.rstrip('/')
        context['accept_url'] = (
            base + reverse('dbdint:assignment-accept', args=[accept_token])
        )
        context['decline_url'] = (
            base + reverse('dbdint:assignment-decline', args=[decline_token])
        )

    return context


# ---------------------------------------------------------------------------
# Audit log helper
# ---------------------------------------------------------------------------

def log_email_sent(assignment, email_type: str) -> None:
    """Write an AuditLog entry for a sent assignment email.

    Args:
        assignment: Assignment model instance.
        email_type: Email type string (e.g. ``'confirmed'``).
    """
    from app.models import AuditLog

    AuditLog.objects.create(
        user=assignment.interpreter.user if assignment.interpreter else None,
        action=f"EMAIL_SENT_{email_type.upper()}",
        model_name='Assignment',
        object_id=str(assignment.id),
        changes={'email_type': email_type},
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def send_assignment_email(
    assignment,
    email_type: str = 'new',
    site_url: str = '',
) -> bool:
    """Send an assignment notification email to the assigned interpreter.

    Builds a multipart HTML email with optional ICS calendar attachment.
    Anti-threading headers prevent email clients from grouping multiple
    assignment emails into one thread.

    Args:
        assignment: Assignment model instance.
        email_type: One of ``'new'``, ``'confirmed'``, ``'cancelled'``,
            ``'completed'``, ``'no_show'``.
        site_url: Base URL used for building accept/decline token links in
            ``'new'`` emails.  Falls back to ``settings.SITE_URL``.

    Returns:
        ``True`` on successful send, ``False`` on any error.
    """
    if not assignment.interpreter or not assignment.interpreter.user.email:
        logger.warning(
            "send_assignment_email skipped: no interpreter or email on assignment %s",
            assignment.id,
        )
        return False

    if not site_url:
        site_url = getattr(settings, 'SITE_URL', 'https://portal.jhbridgetranslation.com')

    try:
        context = build_email_context(assignment, email_type, site_url)
        template_config = get_email_template_config(email_type, assignment.id)

        html_message = render_to_string(template_config['template'], context)
        plain_message = strip_tags(html_message)

        unique_msg_id = make_msgid(domain="jhbridge.com")
        unique_ref = f"assignment-{assignment.id}-{uuid.uuid4().hex}"

        headers = {
            'Message-ID': unique_msg_id,
            'X-Entity-Ref-ID': unique_ref,
            'Thread-Topic': (
                f"Assignment {assignment.id} {email_type} {uuid.uuid4().hex[:6]}"
            ),
            'Thread-Index': uuid.uuid4().hex,
            'X-No-Threading': 'true',
        }

        email = EmailMultiAlternatives(
            subject=template_config['subject'],
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[assignment.interpreter.user.email],
            headers=headers,
        )
        email.attach_alternative(html_message, "text/html")

        if template_config.get('include_calendar', False):
            ics_data = generate_ics_calendar(assignment)
            ical_part = MIMEBase('text', 'calendar', method='REQUEST', name='invite.ics')
            ical_part.set_payload(ics_data)
            encoders.encode_base64(ical_part)
            ical_part.add_header('Content-Disposition', 'attachment; filename="assignment.ics"')
            ical_part.add_header('Content-class', 'urn:content-classes:calendarmessage')
            email.attach(ical_part)

        email.send(fail_silently=False)
        log_email_sent(assignment, email_type)
        logger.info("Assignment email '%s' sent for assignment %s", email_type, assignment.id)
        return True

    except Exception as exc:
        logger.error(
            "Error sending '%s' email for assignment %s: %s",
            email_type, assignment.id, exc, exc_info=True,
        )
        return False
