"""Agent queue and audit models for the AI operations pipeline."""
from django.db import models
from django.utils import timezone


class AgentQueueItem(models.Model):
    class Category(models.TextChoices):
        INTERPRETATION = 'INTERPRETATION', 'Interpretation Request'
        QUOTE = 'QUOTE', 'Quote Request'
        HIRING = 'HIRING', 'Hiring / CV'
        INVOICE = 'INVOICE', 'Invoice Received'
        PAYSLIP = 'PAYSLIP', 'Payslip Received'
        PAYMENT = 'PAYMENT', 'Payment Confirmation'
        CONFIRMATION = 'CONFIRMATION', 'Confirmation'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        EXECUTING = 'EXECUTING', 'Executing'
        DONE = 'DONE', 'Done'
        FAILED = 'FAILED', 'Failed'

    class ActionType(models.TextChoices):
        CREATE_ASSIGNMENT = 'CREATE_ASSIGNMENT', 'Create Assignment'
        CREATE_QUOTE_REQUEST = 'CREATE_QUOTE_REQUEST', 'Create Quote Request'
        SEND_ONBOARDING = 'SEND_ONBOARDING', 'Send Onboarding Invitation'
        RECORD_INVOICE = 'RECORD_INVOICE', 'Record Payable Invoice'
        RECORD_PAYSLIP = 'RECORD_PAYSLIP', 'Record Payslip'
        MARK_INVOICE_PAID = 'MARK_INVOICE_PAID', 'Mark Invoice Paid'
        SEND_REPLY = 'SEND_REPLY', 'Send Email Reply'
        CREATE_CLIENT = 'CREATE_CLIENT', 'Create Client'
        MANUAL_REVIEW = 'MANUAL_REVIEW', 'Manual Review Required'

    # Email source
    gmail_id = models.CharField(max_length=100, blank=True, db_index=True)
    email_subject = models.CharField(max_length=500, blank=True)
    email_from = models.CharField(max_length=254, blank=True)

    # Classification
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    confidence = models.FloatField(default=0.0)

    # Extracted data and proposed action
    extracted_data = models.JSONField(default=dict)
    action_type = models.CharField(max_length=30, choices=ActionType.choices, default=ActionType.MANUAL_REVIEW)
    action_payload = models.JSONField(default=dict)
    ai_reasoning = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, db_index=True)

    # Approval
    approved_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_agent_items')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Execution result
    executed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Linked entities (set after successful execution)
    linked_assignment_id = models.BigIntegerField(null=True, blank=True)
    linked_client_id = models.BigIntegerField(null=True, blank=True)
    linked_onboarding_id = models.CharField(max_length=36, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent Queue Item'
        verbose_name_plural = 'Agent Queue Items'

    def __str__(self):
        return f"[{self.category}] {self.email_subject[:60]} — {self.status}"


class AgentAuditLog(models.Model):
    queue_item = models.ForeignKey(
        AgentQueueItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.CharField(max_length=50, blank=True)
    success = models.BooleanField(default=True)
    details = models.JSONField(default=dict)
    performed_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True, related_name='agent_audit_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent Audit Log'
        verbose_name_plural = 'Agent Audit Logs'

    def __str__(self):
        return f"{self.action} — {'OK' if self.success else 'FAIL'} — {self.created_at}"
