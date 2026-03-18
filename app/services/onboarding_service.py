"""
Standalone onboarding service.

Extracted from OnboardingInvitationAdmin and OnboardingViewSet so the same
onboarding logic is shared by:
  - The Django admin (save_model, bulk actions, send_invitation_view)
  - The DRF API viewset (create, resend, void, advance, extend)

Key design decision — resend creates a NEW invitation:
  Admin _resend_with_template() voids old + creates new with version+1.
  The API used to just resend the same invitation (inconsistency).
  Now both call resend_invitation() which always voids old + creates new.
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------

PHASE_ORDER = [
    'INVITED',
    'EMAIL_OPENED',
    'WELCOME_VIEWED',
    'ACCOUNT_CREATED',
    'PROFILE_COMPLETED',
    'CONTRACT_STARTED',
    'COMPLETED',
]

PHASE_TIMESTAMPS = {
    'EMAIL_OPENED': 'email_opened_at',
    'WELCOME_VIEWED': 'welcome_viewed_at',
    'ACCOUNT_CREATED': 'account_created_at',
    'PROFILE_COMPLETED': 'profile_completed_at',
    'CONTRACT_STARTED': 'contract_started_at',
    'COMPLETED': 'completed_at',
}

# Maps current phase to the most relevant resend template type.
# Used by the API resend action to pick the right "nudge" email.
PHASE_TEMPLATE_MAP = {
    'INVITED': 'RESEND_ISSUE',
    'EMAIL_OPENED': 'STUCK_OPENED',
    'WELCOME_VIEWED': 'STUCK_WELCOME',
    'ACCOUNT_CREATED': 'STUCK_ACCOUNT',
    'PROFILE_COMPLETED': 'STUCK_ACCOUNT',
    'CONTRACT_STARTED': 'STUCK_CONTRACT',
}

# Human-readable void reasons keyed by template type
_VOID_REASONS = {
    None: 'Voided for standard resending',
    'RESEND_ISSUE': 'Resent due to reported issue',
    'STUCK_WELCOME': 'Resent: Stuck in Welcome',
    'STUCK_ACCOUNT': 'Resent: Stuck in Account',
    'STUCK_CONTRACT': 'Resent: Stuck in Contract',
    'STUCK_OPENED': 'Resent: Stuck Email Opened',
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def create_invitation(first_name, last_name, email, phone, created_by, request=None):
    """Create a new onboarding invitation, link existing user, and send email.

    Args:
        first_name: Interpreter's first name.
        last_name: Interpreter's last name.
        email: Email address for the invitation.
        phone: Phone number (may be empty string).
        created_by: User instance (the admin who created the invitation).
        request: Django request object (optional, used for absolute URLs in email).

    Returns:
        The created OnboardingInvitation instance.
    """
    from app.models import OnboardingInvitation, OnboardingTrackingEvent, User
    from app.services.email_service import OnboardingEmailService

    invitation = OnboardingInvitation.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        created_by=created_by,
    )

    # Link to an existing user/interpreter if the email is already registered
    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        invitation.user = existing_user
        invitation.interpreter = getattr(existing_user, 'interpreter', None)
        invitation.save(update_fields=['user', 'interpreter'])

    # Send the invitation email
    sent = OnboardingEmailService.send_invitation_email(invitation, request)
    if sent:
        invitation.email_sent_at = timezone.now()
        invitation.save(update_fields=['email_sent_at'])
        OnboardingTrackingEvent.objects.create(
            invitation=invitation,
            event_type='EMAIL_SENT',
            performed_by=created_by,
            metadata={'source': 'onboarding_service.create'},
        )
    else:
        logger.warning(
            "Onboarding email failed to send for invitation %s",
            invitation.invitation_number,
        )

    return invitation


def resend_invitation(old_invitation, created_by, template_type=None, request=None):
    """Void old invitation and create a fresh one with the next version number.

    This is the canonical resend behaviour used by both admin and API.
    The old invitation is voided (unless already voided/expired) and a brand-new
    invitation is created with ``version = old.version + 1``.

    Args:
        old_invitation: The OnboardingInvitation to supersede.
        created_by: User instance performing the resend.
        template_type: One of ``None`` (standard), ``'RESEND_ISSUE'``,
            ``'STUCK_WELCOME'``, ``'STUCK_ACCOUNT'``, ``'STUCK_CONTRACT'``,
            ``'STUCK_OPENED'``.
        request: Django request object (optional).

    Returns:
        The newly created OnboardingInvitation instance.
    """
    from app.models import OnboardingInvitation, OnboardingTrackingEvent
    from app.services.email_service import OnboardingEmailService

    # Void the old invitation if it is still active
    if old_invitation.current_phase not in ('VOIDED', 'EXPIRED'):
        old_invitation.current_phase = 'VOIDED'
        old_invitation.voided_by = created_by
        old_invitation.voided_at = timezone.now()
        old_invitation.void_reason = _VOID_REASONS.get(template_type, 'Resent')
        old_invitation.save()

    new_inv = OnboardingInvitation.objects.create(
        email=old_invitation.email,
        first_name=old_invitation.first_name,
        last_name=old_invitation.last_name,
        phone=old_invitation.phone,
        created_by=created_by,
        version=old_invitation.version + 1,
    )

    OnboardingTrackingEvent.objects.create(
        invitation=new_inv,
        event_type='RESENT',
        performed_by=created_by,
        metadata={
            'original_invitation_id': str(old_invitation.id),
            'template_type': template_type or 'STANDARD',
        },
    )

    sent = OnboardingEmailService.send_invitation_email(new_inv, request, template_type=template_type)
    if sent:
        new_inv.email_sent_at = timezone.now()
        new_inv.save(update_fields=['email_sent_at'])
    else:
        logger.warning(
            "Resend email failed for new invitation %s (original: %s)",
            new_inv.invitation_number,
            old_invitation.invitation_number,
        )

    return new_inv


def void_invitation(invitation, voided_by, reason=''):
    """Void an onboarding invitation.

    Args:
        invitation: OnboardingInvitation instance to void.
        voided_by: User instance performing the void.
        reason: Optional text reason stored on the invitation.

    Returns:
        The updated OnboardingInvitation instance.

    Raises:
        ValueError: If the invitation is already COMPLETED or VOIDED.
    """
    from app.models import OnboardingTrackingEvent

    if invitation.current_phase in ('COMPLETED', 'VOIDED'):
        raise ValueError(f"Cannot void invitation in phase {invitation.current_phase}")

    invitation.current_phase = 'VOIDED'
    invitation.voided_at = timezone.now()
    invitation.voided_by = voided_by
    invitation.void_reason = reason
    invitation.save()

    OnboardingTrackingEvent.objects.create(
        invitation=invitation,
        event_type='VOIDED',
        performed_by=voided_by,
        metadata={'reason': reason},
    )

    return invitation


def advance_invitation(invitation):
    """Advance an invitation to the next phase and stamp the timestamp field.

    Args:
        invitation: OnboardingInvitation instance to advance.

    Returns:
        The updated OnboardingInvitation instance.

    Raises:
        ValueError: If the invitation cannot be advanced (terminal phase).
    """
    if invitation.current_phase in ('COMPLETED', 'VOIDED', 'EXPIRED'):
        raise ValueError(f"Cannot advance from phase {invitation.current_phase}")

    try:
        idx = PHASE_ORDER.index(invitation.current_phase)
        next_phase = PHASE_ORDER[idx + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError("Cannot determine next phase") from exc

    invitation.current_phase = next_phase
    ts_field = PHASE_TIMESTAMPS.get(next_phase)
    if ts_field:
        setattr(invitation, ts_field, timezone.now())
    invitation.save()

    return invitation


def extend_invitation(invitation, days=14):
    """Extend the expiration date of an invitation.

    Args:
        invitation: OnboardingInvitation instance.
        days: Number of days to add from now (default 14).

    Returns:
        The updated OnboardingInvitation instance.
    """
    invitation.expires_at = timezone.now() + timezone.timedelta(days=days)
    invitation.save(update_fields=['expires_at'])
    return invitation
