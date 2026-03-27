from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
import uuid

from shared.constants import ROLE_CLIENT, ROLE_INTERPRETER, ROLE_ADMIN

class User(AbstractUser):
    class Roles(models.TextChoices):
        CLIENT = ROLE_CLIENT, _('Client')
        INTERPRETER = ROLE_INTERPRETER, _('Interprète')
        ADMIN = ROLE_ADMIN, _('Administrateur')

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        related_name='custom_user_set'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        related_name='custom_user_set'
    )

    email = models.EmailField(unique=True)
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
    
    contract_acceptance_date = models.DateTimeField(null=True, blank=True, help_text="Date d'acceptation du contrat")
    is_dashboard_enabled = models.BooleanField(default=False, help_text="Accès au tableau de bord activé")

    admin_pin_hash = models.CharField(
        max_length=128, blank=True, default='',
        help_text="SHA-256 hash of the admin PIN for banking data access"
    )

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        db_table = 'app_user'

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=50, blank=True, null=True)
    billing_zip_code = models.CharField(max_length=20, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    preferred_language = models.ForeignKey('Language', on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'app_client'

class Interpreter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='interpreter_profile')
    languages = models.ManyToManyField('Language', through='InterpreterLanguage')
    profile_image = models.TextField(null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    certifications = models.JSONField(null=True, blank=True)
    specialties = models.JSONField(null=True, blank=True)
    availability = models.JSONField(null=True, blank=True)
    radius_of_service = models.IntegerField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True, blank=True)
    routing_number = models.CharField(max_length=255, null=True, blank=True)
    account_number = models.CharField(max_length=255, null=True, blank=True)
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
    
    date_of_birth = models.DateField(null=True, blank=True)
    years_of_experience = models.CharField(max_length=20, null=True, blank=True)

    assignment_types = models.JSONField(null=True, blank=True)
    preferred_assignment_type = models.CharField(max_length=20, null=True, blank=True)
    cities_willing_to_cover = models.JSONField(null=True, blank=True)

    contract_acceptance_date = models.DateTimeField(null=True, blank=True)
    contract_rejection_reason = models.TextField(null=True, blank=True)
    has_accepted_contract = models.BooleanField(default=False)
    is_dashboard_enabled = models.BooleanField(default=False)
    contract_invite_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    contract_invite_expires_at = models.DateTimeField(null=True, blank=True)

    signature_ip = models.CharField(max_length=45, null=True, blank=True)

    is_manually_blocked = models.BooleanField(default=False, help_text="Bloqué manuellement par un administrateur")
    blocked_reason = models.TextField(null=True, blank=True, help_text="Raison du blocage")
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='blocked_interpreters'
    )

    # --- AJOUT DES PROPRIÉTÉS POUR ÉVITER LES BUGS ---
    @property
    def phone(self):
        """Redirige vers le téléphone de l'utilisateur."""
        return self.user.phone if self.user else ""

    @property
    def email(self):
        """Redirige vers l'email de l'utilisateur."""
        return self.user.email if self.user else ""

    @property
    def first_name(self):
        return self.user.first_name if self.user else ""

    @property
    def last_name(self):
        return self.user.last_name if self.user else ""

    # --- SOLUTION MAGIQUE POUR TOUS LES AUTRES CHAMPS ---
    def __getattr__(self, name):
        """Récupère dynamiquement les attributs du User s'ils manquent sur l'Interpreter."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        try:
            return getattr(self.user, name)
        except (AttributeError, User.DoesNotExist):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    class Meta:
        db_table = 'app_interpreter'
    
    def __str__(self):
        if self.user:
            languages_str = ', '.join([lang.name for lang in self.languages.all()[:3]])
            if self.languages.count() > 3:
                languages_str += f" +{self.languages.count() - 3} autres"
            address_str = f"{self.address}, {self.city}, {self.state} {self.zip_code}" if self.address else "Pas d'adresse"
            return f"{self.user.first_name} {self.user.last_name} ({self.user.email}) - {address_str}"
        return f"Interprète #{self.id}"
        
    def get_full_details(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.city}, {self.state}"
    
    
# app/models/users.py — AJOUTER

class InterpreterLocation(models.Model):
    interpreter = models.ForeignKey('Interpreter', on_delete=models.CASCADE, related_name='locations')
    
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy = models.FloatField(null=True)  # Précision GPS en mètres
    
    is_on_mission = models.BooleanField(default=False)
    current_assignment = models.ForeignKey('Assignment', on_delete=models.SET_NULL, null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'app_interpreter_location'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['interpreter', '-timestamp']),
        ]
        # On ne garde que la dernière position
        # Les positions historiques sont purgées par un Celery task