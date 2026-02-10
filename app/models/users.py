from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

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
    
    # Nouveaux champs demandés
    contract_acceptance_date = models.DateTimeField(null=True, blank=True, help_text="Date d'acceptation du contrat")
    is_dashboard_enabled = models.BooleanField(default=False, help_text="Accès au tableau de bord activé")

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
    phone = models.CharField(max_length=20, blank=True, null=True)  # Nouveau champ ajouté
    email = models.EmailField(blank=True, null=True)  # Nouveau champ ajouté
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
    
    # Contract & Dashboard Access
    contract_acceptance_date = models.DateTimeField(null=True, blank=True)
    contract_rejection_reason = models.TextField(null=True, blank=True)
    has_accepted_contract = models.BooleanField(default=False)
    is_dashboard_enabled = models.BooleanField(default=False)
    
    # Manual Blocking & Sanctions
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
    
    class Meta:
        db_table = 'app_interpreter'
    
    def __str__(self):
        """Retourne une représentation lisible de l'interprète"""
        if self.user:
            # Format: Nom Prénom - Email - Langues
            languages_str = ', '.join([lang.name for lang in self.languages.all()[:3]])
            if self.languages.count() > 3:
                languages_str += f" +{self.languages.count() - 3} autres"
                
            return f"{self.user.first_name} {self.user.last_name} ({self.user.email})"
        return f"Interprète #{self.id}"
        
    def get_full_details(self):
        """Retourne des détails complets pour l'affichage dans les formulaires administratifs"""
        languages = ', '.join([lang.name for lang in self.languages.all()])
        return f"{self.user.first_name} {self.user.last_name} - {languages} - {self.city}, {self.state}"
