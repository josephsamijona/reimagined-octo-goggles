from django.db import models
from django.utils import timezone
import uuid

class ContractReminder(models.Model):
    """
    Tracks reminders sent to interpreters regarding contract signing.
    Supports 3 levels of automated/manual reminders.
    """
    LEVEL_CHOICES = [
        (1, 'Level 1 - Initial Reminder (3 days)'),
        (2, 'Level 2 - Urgent Reminder (7 days)'),
        (3, 'Level 3 - Final Notice & Block (14 days)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    interpreter = models.ForeignKey(
        'app.Interpreter', 
        on_delete=models.CASCADE, 
        related_name='contract_reminders'
    )
    
    invitation = models.ForeignKey(
        'app.ContractInvitation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reminders'
    )
    
    level = models.IntegerField(choices=LEVEL_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        'app.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who triggered the reminder (null if automated)"
    )
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'app_contract_reminder'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['interpreter', 'level']),
            models.Index(fields=['sent_at']),
        ]
        
    def __str__(self):
        return f"Level {self.level} reminder for {self.interpreter} at {self.sent_at}"
