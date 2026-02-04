from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

class ServiceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_hours = models.IntegerField(default=1)
    cancellation_policy = models.TextField()
    requires_certification = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'app_servicetype'

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

    client = models.ForeignKey('Client', on_delete=models.PROTECT)
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    requested_date = models.DateTimeField()
    duration = models.IntegerField(help_text="Durée en minutes")
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    source_language = models.ForeignKey('Language', on_delete=models.PROTECT, related_name='quote_requests_source')
    target_language = models.ForeignKey('Language', on_delete=models.PROTECT, related_name='quote_requests_target')
    special_requirements = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_quoterequest'

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
    created_by = models.ForeignKey('User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_quote'

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
        'Interpreter', 
        on_delete=models.SET_NULL,  # Au lieu de PROTECT
        null=True, 
        blank=True
    )
    
    # Client fields - all optional now
    client = models.ForeignKey('Client', on_delete=models.PROTECT, null=True, blank=True)  
    client_name = models.CharField(max_length=255, null=True, blank=True)  
    client_email = models.EmailField(null=True, blank=True)  
    client_phone = models.CharField(max_length=20, null=True, blank=True)  
    
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    source_language = models.ForeignKey('Language', on_delete=models.PROTECT, related_name='assignments_source')
    target_language = models.ForeignKey('Language', on_delete=models.PROTECT, related_name='assignments_target')
    
    # Champs temporels et localisation
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices)
    # Ajouter ce champ après les champs financiers existants:
    is_paid = models.BooleanField(null=True, blank=True, help_text="Indicates if the assignment has been paid")
    
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
        db_table = 'app_assignment'

    def __str__(self):
        if self.client:
            client_info = str(self.client)
        elif self.client_name:
            client_info = self.client_name
        else:
            client_info = "Unspecified Client"
        return f"Assignment {self.id} - {client_info} ({self.status})"

    # Modify save to no longer call clean()
    def save(self, *args, **kwargs):
        # self.clean()  # Remove this line
        
        # Clear manual fields if a client is selected
        if self.client:
            self.client_name = None
            self.client_email = None
            self.client_phone = None
            
        super().save(*args, **kwargs)

    def can_be_confirmed(self):
        """Vérifie si l'assignment peut être confirmé"""
        return self.status == self.Status.PENDING

    def can_be_started(self):
        """Vérifie si l'assignment peut être démarré"""
        return self.status == self.Status.CONFIRMED

    def can_be_completed(self):
       """Vérifie si l'assignment peut être marqué comme terminé"""
       return self.status in [self.Status.IN_PROGRESS, self.Status.CONFIRMED]

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
        elif self.client_name:
            return self.client_name
        return "Unspecified Client"

class PublicQuoteRequest(models.Model):
    # Contact Information
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100)
    
    # Service Details
    source_language = models.ForeignKey('Language', on_delete=models.PROTECT, related_name='public_quotes_source')
    target_language = models.ForeignKey('Language', on_delete=models.PROTECT, related_name='public_quotes_target')
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
    processed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'app_publicquoterequest'

    def __str__(self):
        return f"Quote Request from {self.full_name} ({self.company_name})"
