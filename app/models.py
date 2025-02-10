from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # ISO code
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Languagee(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # ISO code
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class User(AbstractUser):
    class Roles(models.TextChoices):
        CLIENT = 'CLIENT', _('Client')
        INTERPRETER = 'INTERPRETER', _('Interprète')
        ADMIN = 'ADMIN', _('Administrateur')

    # Ajout des related_name pour éviter les conflits
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set'  # Ajout du related_name personnalisé
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set'  # Ajout du related_name personnalisé
    )

    email = models.EmailField(unique=True)
    # Dans models.py, classe User
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name=_('Phone number')
    )
    role = models.CharField(max_length=20, choices=Roles.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    registration_complete = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=50, blank=True, null=True)
    billing_zip_code = models.CharField(max_length=20, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    preferred_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

class InterpreterLanguage(models.Model):
    class Proficiency(models.TextChoices):
        NATIVE = 'NATIVE', _('Natif')
        FLUENT = 'FLUENT', _('Courant')
        PROFESSIONAL = 'PROFESSIONAL', _('Professionnel')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermédiaire')

    interpreter = models.ForeignKey('Interpreter', on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    proficiency = models.CharField(max_length=20, choices=Proficiency.choices)
    is_primary = models.BooleanField(default=False)
    certified = models.BooleanField(default=False)
    certification_details = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['interpreter', 'language']

class Interpreter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='interpreter_profile')
    languages = models.ManyToManyField(Language, through=InterpreterLanguage)
    profile_image = models.ImageField(upload_to='interpreter_profiles/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    certifications = models.JSONField(null=True, blank=True)  # Format: [{"name": "CCHI", "expiry_date": "2025-01-01"}]
    specialties = models.JSONField(null=True, blank=True)  # Format: ["Medical", "Legal"]
    availability = models.JSONField(null=True, blank=True)  # Format: {"monday": ["9:00-17:00"]}
    radius_of_service = models.IntegerField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    
    
    # Informations bancaires pour ACH
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True, blank=True)
    routing_number = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=100, null=True, blank=True)
    account_type = models.CharField(
        max_length=10, 
        choices=[('checking', 'Checking'), ('savings', 'Savings')],
        null=True,
        blank=True
    )
    
    background_check_date = models.DateField(null=True, blank=True)
    background_check_status = models.BooleanField(default=False)
    w9_on_file = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

# models.py
class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_hours = models.IntegerField(default=1)
    cancellation_policy = models.TextField()
    requires_certification = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class QuoteRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        QUOTED = 'QUOTED', _('Quoted')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')
        EXPIRED = 'EXPIRED', _('Expired')

    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    requested_date = models.DateTimeField()
    duration = models.IntegerField(help_text="Durée en minutes")
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    source_language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name='quote_requests_source')
    target_language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name='quote_requests_target')
    special_requirements = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SENT = 'SENT', _('Sent')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        REJECTED = 'REJECTED', _('Rejected')
        EXPIRED = 'EXPIRED', _('Expired')
        CANCELLED = 'CANCELLED', _('Cancelled')

    quote_request = models.OneToOneField(QuoteRequest, on_delete=models.PROTECT)
    reference_number = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_until = models.DateField()
    terms = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Assignment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')  # Assigné à un interprète, en attente de confirmation
        CONFIRMED = 'CONFIRMED', _('Confirmed')  # Accepté par l'interprète
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')  # Mission en cours
        COMPLETED = 'COMPLETED', _('Completed')  # Mission terminée
        CANCELLED = 'CANCELLED', _('Cancelled')  # Refusé par l'interprète
        NO_SHOW = 'NO_SHOW', _('No Show')  # Client ou interprète absent

    # Relations existantes
    quote = models.OneToOneField(Quote, on_delete=models.PROTECT, null=True, blank=True)
    interpreter = models.ForeignKey(
        Interpreter, 
        on_delete=models.SET_NULL,  # Au lieu de PROTECT
        null=True, 
        blank=True
    )
    
    # Modification du champ client pour permettre les deux options
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)  # Client existant
    client_name = models.CharField(max_length=255, null=True, blank=True)  # Nouveau client (manuel)
    client_email = models.EmailField(null=True, blank=True)  # Email du nouveau client
    client_phone = models.CharField(max_length=20, null=True, blank=True)  # Téléphone du nouveau client
    
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    source_language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name='assignments_source')
    target_language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name='assignments_target')
    
    # Champs temporels et localisation
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices)
    
    # Informations financières
    interpreter_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Taux horaire de l'interprète")
    minimum_hours = models.IntegerField(default=2)
    total_interpreter_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Informations additionnelles
    notes = models.TextField(blank=True, null=True)
    special_requirements = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'interpreter', 'start_time']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        if self.client:
            client_info = str(self.client)
        else:
            client_info = self.client_name or "Nouveau client"
        return f"Assignment {self.id} - {client_info} ({self.status})"

    def clean(self):
        """Validation personnalisée pour s'assurer qu'il y a soit un client existant, soit les informations d'un nouveau client"""
        if not self.client and not (self.client_name and self.client_email):
            raise ValidationError({
                'client': 'Vous devez soit sélectionner un client existant, soit fournir les informations pour un nouveau client'
            })
        if self.client and (self.client_name or self.client_email or self.client_phone):
            raise ValidationError({
                'client': 'Vous ne pouvez pas à la fois sélectionner un client existant et fournir des informations pour un nouveau client'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def can_be_confirmed(self):
        """Vérifie si l'assignment peut être confirmé"""
        return self.status == self.Status.PENDING

    def can_be_started(self):
        """Vérifie si l'assignment peut être démarré"""
        return self.status == self.Status.CONFIRMED

    def can_be_completed(self):
        """Vérifie si l'assignment peut être marqué comme terminé"""
        return self.status == self.Status.IN_PROGRESS

    def can_be_cancelled(self):
        """Vérifie si l'assignment peut être annulé"""
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]

    def confirm(self):
        """Confirme l'assignment"""
        if self.can_be_confirmed():
            self.status = self.Status.CONFIRMED
            self.save()
            return True
        return False

    def start(self):
        """Démarre l'assignment"""
        if self.can_be_started():
            self.status = self.Status.IN_PROGRESS
            self.save()
            return True
        return False

    def complete(self):
        """Marque l'assignment comme terminé"""
        if self.can_be_completed():
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
            self.save()
            return True
        return False

    def cancel(self):
        """Annule l'assignment"""
        if self.can_be_cancelled():
            self.status = self.Status.CANCELLED
            old_interpreter = self.interpreter
            self.interpreter = None  # Désassociation de l'interprète
            self.save()
            return old_interpreter  # Retourne l'ancien interprète pour la notification
        return None

    def get_client_display(self):
        """Retourne les informations du client à afficher"""
        if self.client:
            return str(self.client)
        return f"{self.client_name} (Nouveau client)"

class AssignmentFeedback(models.Model):
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')

    class PaymentType(models.TextChoices):
        CLIENT_PAYMENT = 'CLIENT_PAYMENT', _('Client Payment')
        INTERPRETER_PAYMENT = 'INTERPRETER_PAYMENT', _('Interpreter Payment')


    quote = models.ForeignKey(Quote, on_delete=models.PROTECT, null=True, blank=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    payment_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

class Notification(models.Model):
    class Type(models.TextChoices):
        QUOTE_REQUEST = 'QUOTE_REQUEST', _('Quote Request')
        QUOTE_READY = 'QUOTE_READY', _('Quote Ready')
        ASSIGNMENT_OFFER = 'ASSIGNMENT_OFFER', _('Assignment Offer')
        ASSIGNMENT_REMINDER = 'ASSIGNMENT_REMINDER', _('Assignment Reminder')
        PAYMENT_RECEIVED = 'PAYMENT_RECEIVED', _('Payment Received')
        SYSTEM = 'SYSTEM', _('System')

    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=200)
    content = models.TextField()
    read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    
class PublicQuoteRequest(models.Model):
    # Contact Information
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100)
    
    # Service Details
    source_language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name='public_quotes_source')
    target_language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name='public_quotes_target')
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    requested_date = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    
    # Location
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    
    # Additional Information
    special_requirements = models.TextField(blank=True, null=True)
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Quote Request from {self.full_name} ({self.company_name})"

# models.py

class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
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
        Language, 
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
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='notifications')
    interpreter = models.ForeignKey(Interpreter, on_delete=models.CASCADE, related_name='assignment_notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['interpreter', 'is_read']),
            models.Index(fields=['created_at'])
        ]

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