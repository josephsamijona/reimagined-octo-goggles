from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'app_contactmessage'

class Notification(models.Model):
    class Type(models.TextChoices):
        QUOTE_REQUEST = 'QUOTE_REQUEST', _('Quote Request')
        QUOTE_READY = 'QUOTE_READY', _('Quote Ready')
        ASSIGNMENT_OFFER = 'ASSIGNMENT_OFFER', _('Assignment Offer')
        ASSIGNMENT_REMINDER = 'ASSIGNMENT_REMINDER', _('Assignment Reminder')
        PAYMENT_RECEIVED = 'PAYMENT_RECEIVED', _('Payment Received')
        SYSTEM = 'SYSTEM', _('System')

    recipient = models.ForeignKey('User', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=200)
    content = models.TextField()
    read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_notification'

class NotificationPreference(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email Notifications
    email_quote_updates = models.BooleanField(default=True, help_text="Receive email notifications about quote status updates")
    email_assignment_updates = models.BooleanField(default=True, help_text="Receive email notifications about assignment updates")
    email_payment_updates = models.BooleanField(default=True, help_text="Receive email notifications about payment status")
    
    # SMS Notifications
    sms_enabled = models.BooleanField(default=False, help_text="Enable SMS notifications")
    
    # In-App Notifications
    quote_notifications = models.BooleanField(default=True, help_text="Receive in-app notifications about quotes")
    assignment_notifications = models.BooleanField(default=True, help_text="Receive in-app notifications about assignments")
    payment_notifications = models.BooleanField(default=True, help_text="Receive in-app notifications about payments")
    system_notifications = models.BooleanField(default=True, help_text="Receive system notifications and updates")

    # Communication Preferences
    preferred_language = models.ForeignKey(
        'Language', 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        help_text="Preferred language for notifications"
    )
    
    # Notification Frequency
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest')
        ],
        default='immediate',
        help_text="How often to receive notifications"
    )

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
        db_table = 'app_notificationpreference'

    def __str__(self):
        return f"Notification preferences for {self.user.email}"

    def save(self, *args, **kwargs):
        # On vérifie si l'utilisateur est un client ou un interprète
        if not self.preferred_language:
            if hasattr(self.user, 'client_profile') and self.user.client_profile:
                self.preferred_language = self.user.client_profile.preferred_language
            elif hasattr(self.user, 'interpreter_profile') and self.user.interpreter_profile:
                self.preferred_language = None
        super().save(*args, **kwargs)

class AssignmentNotification(models.Model):
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, related_name='notifications')
    interpreter = models.ForeignKey('Interpreter', on_delete=models.CASCADE, related_name='assignment_notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['interpreter', 'is_read']),
            models.Index(fields=['created_at'])
        ]
        db_table = 'app_assignmentnotification'

    def __str__(self):
        return f"Notification for {self.assignment} - {self.interpreter}"

    @classmethod
    def create_for_new_assignment(cls, assignment):
        """
        Crée une notification pour un nouvel assignment
        """
        return cls.objects.create(
            assignment=assignment,
            interpreter=assignment.interpreter
        )

    @classmethod
    def get_unread_count(cls, interpreter):
        """
        Retourne le nombre de notifications non lues pour un interprète
        """
        return cls.objects.filter(
            interpreter=interpreter,
            is_read=False
        ).count()

    def mark_as_read(self):
        """
        Marque la notification comme lue
        """
        self.is_read = True
        self.save()

class AssignmentFeedback(models.Model):
    assignment = models.OneToOneField('Assignment', on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.PROTECT)

    class Meta:
        db_table = 'app_assignmentfeedback'
