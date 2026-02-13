from django.db import models
from .core import AppLanguage

class AppUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.IntegerField()
    date_joined = models.DateTimeField()
    email = models.CharField(unique=True, max_length=254)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20)
    is_active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    last_login_ip = models.CharField(max_length=39, blank=True, null=True)
    registration_complete = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_user'

class AppApikey(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=100)
    app_name = models.CharField(max_length=100)
    key = models.CharField(unique=True, max_length=64)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.IntegerField()
    last_used = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(AppUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_apikey'

class AppPgpkey(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=255)
    key_id = models.CharField(unique=True, max_length=100)
    fingerprint = models.CharField(max_length=255, blank=True, null=True)
    public_key = models.TextField()
    private_key_reference = models.CharField(max_length=255)
    is_active = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    expires_at = models.DateTimeField(blank=True, null=True)
    algorithm = models.CharField(max_length=50, blank=True, null=True)
    key_size = models.PositiveIntegerField(blank=True, null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    user_email = models.CharField(max_length=254, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_pgpkey'

class AppClient(models.Model):
    id = models.BigAutoField(primary_key=True)
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
    notes = models.TextField(blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.IntegerField()
    user = models.OneToOneField(AppUser, models.DO_NOTHING)
    preferred_language = models.ForeignKey(AppLanguage, models.DO_NOTHING, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_client'

class AppInterpreter(models.Model):
    id = models.BigAutoField(primary_key=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    certifications = models.JSONField(blank=True, null=True)
    specialties = models.JSONField(blank=True, null=True)
    availability = models.JSONField(blank=True, null=True)
    radius_of_service = models.IntegerField(blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_holder_name = models.CharField(max_length=100, blank=True, null=True)
    routing_number = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    account_type = models.CharField(max_length=10, blank=True, null=True)
    background_check_date = models.DateField(blank=True, null=True)
    background_check_status = models.IntegerField()
    w9_on_file = models.IntegerField()
    active = models.IntegerField()
    user = models.OneToOneField(AppUser, models.DO_NOTHING)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.CharField(max_length=100, blank=True, null=True)
    contract_acceptance_date = models.DateTimeField(blank=True, null=True)
    contract_rejection_reason = models.TextField(blank=True, null=True)
    has_accepted_contract = models.IntegerField()
    is_dashboard_enabled = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_interpreter'

class AppInterpreterlanguage(models.Model):
    id = models.BigAutoField(primary_key=True)
    proficiency = models.CharField(max_length=20)
    is_primary = models.IntegerField()
    certified = models.IntegerField()
    certification_details = models.TextField(blank=True, null=True)
    interpreter = models.ForeignKey(AppInterpreter, models.DO_NOTHING)
    language = models.ForeignKey(AppLanguage, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_interpreterlanguage'
        unique_together = (('interpreter', 'language'),)
