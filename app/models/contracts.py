from django.db import models
from django.utils import timezone
import uuid
import random

class ContractInvitation(models.Model):
    """
    Tracks contract invitation lifecycle independent of signature.
    One invitation can have multiple tracking events.
    """
    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invitation_number = models.CharField(max_length=50, unique=True, editable=False)  # AUTO: INV-2026-XXXXX
    
    # Relationships
    interpreter = models.ForeignKey(
        'app.Interpreter', 
        on_delete=models.CASCADE, 
        related_name='contract_invitations'
    )
    contract_signature = models.OneToOneField(
        'app.InterpreterContractSignature', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='invitation'
    )
    created_by = models.ForeignKey(
        'app.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_invitations'
    )
    voided_by = models.ForeignKey(
        'app.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='voided_invitations'
    )
    
    # Status & Version
    STATUS_CHOICES = [
        ('SENT', 'Email Sent'),
        ('OPENED', 'Email Opened'),
        ('REVIEWING', 'Reviewing Contract'),
        ('SIGNED', 'Accepted & Signed'),
        ('VOIDED', 'Voided by Admin'),
        ('EXPIRED', 'Invitation Expired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SENT')
    version = models.IntegerField(default=1)  # Increments on resend
    
    # Tokens & Security
    token = models.CharField(max_length=100, unique=True, db_index=True)
    accept_token = models.CharField(max_length=100, unique=True, db_index=True)  # For direct accept
    review_token = models.CharField(max_length=100, unique=True, db_index=True)  # For wizard review
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(auto_now_add=True)
    email_opened_at = models.DateTimeField(null=True, blank=True)
    link_clicked_at = models.DateTimeField(null=True, blank=True)
    link_clicked_type = models.CharField(max_length=20, null=True, blank=True)  # 'ACCEPT' or 'REVIEW'
    signed_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()  # Default: 30 days from creation
    
    # Void details
    void_reason = models.TextField(null=True, blank=True)
    
    # PDF Storage
    pdf_s3_key = models.CharField(max_length=500, null=True, blank=True)  # S3 key for signed PDF
    
    class Meta:
        db_table = 'app_contract_invitation'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['accept_token']),
            models.Index(fields=['review_token']),
            models.Index(fields=['status']),
            models.Index(fields=['invitation_number']),
        ]
        
    def __str__(self):
        return f"{self.invitation_number} - {self.interpreter}"
        
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())
        if not self.accept_token:
            self.accept_token = str(uuid.uuid4())
        if not self.review_token:
            self.review_token = str(uuid.uuid4())
            
        if not self.invitation_number:
            self.invitation_number = self.generate_invitation_number()
            
        if not self.expires_at:
            # Default 30 days expiration
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
            
        super().save(*args, **kwargs)
        
    def generate_invitation_number(self):
        """Generates a unique invitation number format: INV-2026-XXXXX"""
        year = timezone.now().year
        while True:
            random_part = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            inv_num = f"INV-{year}-{random_part}"
            if not ContractInvitation.objects.filter(invitation_number=inv_num).exists():
                return inv_num
                
    def is_expired(self):
        """Checks if the invitation is expired"""
        return timezone.now() > self.expires_at


class ContractTrackingEvent(models.Model):
    """
    Timeline of all events related to a contract invitation.
    Provides audit trail and admin visibility.
    """
    invitation = models.ForeignKey(
        ContractInvitation, 
        on_delete=models.CASCADE, 
        related_name='tracking_events'
    )
    
    EVENT_TYPE_CHOICES = [
        ('EMAIL_SENT', 'Email Sent'),
        ('EMAIL_OPENED', 'Email Opened'),
        ('ACCEPT_LINK_CLICKED', 'Accept Link Clicked'),
        ('REVIEW_LINK_CLICKED', 'Review Link Clicked'),
        ('WIZARD_STARTED', 'Wizard Started'),
        ('WIZARD_COMPLETED', 'Wizard Completed'),
        ('CONTRACT_SIGNED', 'Contract Signed'),
        ('PDF_GENERATED', 'PDF Generated'),
        ('CONFIRMATION_EMAIL_SENT', 'Confirmation Email Sent'),
        ('VOIDED', 'Voided by Admin'),
        ('RESENT', 'Invitation Resent'),
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)  # IP, User Agent, admin user, etc.
    performed_by = models.ForeignKey(
        'app.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        db_table = 'app_contract_tracking_event'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.event_type} on {self.invitation.invitation_number}"
