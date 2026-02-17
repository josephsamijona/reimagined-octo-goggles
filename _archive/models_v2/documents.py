from django.db import models
from .users import AppUser, AppInterpreter, AppPgpkey

class AppInterpretercontractsignature(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    interpreter_name = models.CharField(max_length=255)
    interpreter_email = models.CharField(max_length=254)
    interpreter_phone = models.CharField(max_length=20)
    interpreter_address = models.TextField()
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_type = models.CharField(max_length=20, blank=True, null=True)
    encrypted_account_number = models.TextField(blank=True, null=True)
    encrypted_routing_number = models.TextField(blank=True, null=True)
    encrypted_swift_code = models.TextField(blank=True, null=True)
    contract_document = models.CharField(max_length=100, blank=True, null=True)
    contract_version = models.CharField(max_length=20)
    signature_type = models.CharField(max_length=20, blank=True, null=True)
    signature_image = models.CharField(max_length=100, blank=True, null=True)
    signature_typography_text = models.CharField(max_length=100, blank=True, null=True)
    signature_manual_data = models.TextField(blank=True, null=True)
    signed_at = models.DateTimeField(blank=True, null=True)
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    signature_hash = models.CharField(max_length=64, blank=True, null=True)
    company_representative_name = models.CharField(max_length=255)
    company_representative_signature = models.TextField(blank=True, null=True)
    company_signed_at = models.DateTimeField(blank=True, null=True)
    is_fully_signed = models.IntegerField()
    is_active = models.IntegerField()
    user = models.ForeignKey(AppUser, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    interpreter = models.ForeignKey(AppInterpreter, models.DO_NOTHING, blank=True, null=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    status = models.CharField(max_length=20)
    token = models.CharField(unique=True, max_length=100, blank=True, null=True)
    signature_typography_font = models.CharField(max_length=50, blank=True, null=True)
    signature_converted_url = models.CharField(max_length=500, blank=True, null=True)
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    last_reminder_sent_at = models.DateTimeField(blank=True, null=True)
    modal_viewed_at = models.DateTimeField(blank=True, null=True)
    reminder_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_interpretercontractsignature'

class AppDocument(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    document_number = models.CharField(unique=True, max_length=50, blank=True, null=True)
    agreement_id = models.CharField(max_length=50, blank=True, null=True)
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    file = models.CharField(max_length=100, blank=True, null=True)
    file_hash = models.CharField(max_length=128, blank=True, null=True)
    pgp_signature = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    signed_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField()
    interpreter_contract = models.ForeignKey(AppInterpretercontractsignature, models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AppUser, models.DO_NOTHING, blank=True, null=True)
    signing_key = models.ForeignKey(AppPgpkey, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_document'

class AppSigneddocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    original_document = models.CharField(max_length=100)
    signed_document = models.CharField(max_length=100, blank=True, null=True)
    signature_image = models.CharField(max_length=100, blank=True, null=True)
    signature_type = models.CharField(max_length=20)
    signature_position = models.JSONField()
    signature_metadata = models.JSONField()
    created_at = models.DateTimeField()
    user = models.ForeignKey(AppUser, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_signeddocument'
