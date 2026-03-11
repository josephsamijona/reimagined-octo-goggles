from django.db import models
from django.utils import timezone
import uuid
import random


class OnboardingInvitation(models.Model):
    """
    Tracks the full onboarding lifecycle for interpreters invited by admin.
    Exists independently of User/Interpreter since those are created during onboarding.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invitation_number = models.CharField(max_length=50, unique=True, editable=False)  # ONB-2026-XXXXX

    # Pre-registration data (known before account creation)
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, default='')

    # Post-registration links (set during Phase 2)
    user = models.ForeignKey(
        'app.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='onboarding_invitations'
    )
    interpreter = models.ForeignKey(
        'app.Interpreter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='onboarding_invitations'
    )
    contract_invitation = models.OneToOneField(
        'app.ContractInvitation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='onboarding'
    )

    # Admin
    created_by = models.ForeignKey(
        'app.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_onboarding_invitations'
    )
    voided_by = models.ForeignKey(
        'app.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voided_onboarding_invitations'
    )

    # Status lifecycle
    PHASE_CHOICES = [
        ('INVITED', 'Invitation Sent'),
        ('EMAIL_OPENED', 'Email Opened'),
        ('WELCOME_VIEWED', 'Welcome Viewed'),
        ('ACCOUNT_CREATED', 'Account Created'),
        ('PROFILE_COMPLETED', 'Profile Completed'),
        ('CONTRACT_STARTED', 'Contract Started'),
        ('COMPLETED', 'Fully Completed'),
        ('VOIDED', 'Voided'),
        ('EXPIRED', 'Expired'),
    ]
    current_phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='INVITED')
    version = models.IntegerField(default=1)

    # Token
    token = models.CharField(max_length=100, unique=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_opened_at = models.DateTimeField(null=True, blank=True)
    welcome_viewed_at = models.DateTimeField(null=True, blank=True)
    account_created_at = models.DateTimeField(null=True, blank=True)
    profile_completed_at = models.DateTimeField(null=True, blank=True)
    contract_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    void_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'app_onboarding_invitation'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email']),
            models.Index(fields=['current_phase']),
        ]

    def __str__(self):
        return f"{self.invitation_number} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())
        if not self.invitation_number:
            self.invitation_number = self.generate_invitation_number()
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=14)
        super().save(*args, **kwargs)

    def generate_invitation_number(self):
        year = timezone.now().year
        while True:
            random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            inv_num = f"ONB-{year}-{random_part}"
            if not OnboardingInvitation.objects.filter(invitation_number=inv_num).exists():
                return inv_num

    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class OnboardingTrackingEvent(models.Model):
    """Audit trail for all onboarding events."""
    invitation = models.ForeignKey(
        OnboardingInvitation,
        on_delete=models.CASCADE,
        related_name='tracking_events'
    )

    EVENT_TYPE_CHOICES = [
        ('EMAIL_SENT', 'Invitation Email Sent'),
        ('EMAIL_OPENED', 'Email Opened'),
        ('LINK_CLICKED', 'Onboarding Link Clicked'),
        ('WELCOME_COMPLETED', 'Welcome Phase Completed'),
        ('ACCOUNT_CREATED', 'Account Created'),
        ('PROFILE_SAVED', 'Profile Saved'),
        ('CONTRACT_STARTED', 'Contract Wizard Started'),
        ('CONTRACT_SIGNED', 'Contract Signed'),
        ('ONBOARDING_COMPLETED', 'Onboarding Fully Completed'),
        ('VOIDED', 'Voided by Admin'),
        ('RESENT', 'Invitation Resent'),
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
    performed_by = models.ForeignKey(
        'app.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'app_onboarding_tracking_event'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type} on {self.invitation.invitation_number}"
