# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AppApikey(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=100)
    app_name = models.CharField(max_length=100)
    key = models.CharField(unique=True, max_length=64)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.IntegerField()
    last_used = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_apikey'


class AppAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    interpreter_rate = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_hours = models.IntegerField()
    total_interpreter_payment = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    special_requirements = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    client = models.ForeignKey('AppClient', models.DO_NOTHING, blank=True, null=True)
    interpreter = models.ForeignKey('AppInterpreter', models.DO_NOTHING, blank=True, null=True)
    source_language = models.ForeignKey('AppLanguage', models.DO_NOTHING)
    target_language = models.ForeignKey('AppLanguage', models.DO_NOTHING, related_name='appassignment_target_language_set')
    quote = models.OneToOneField('AppQuote', models.DO_NOTHING, blank=True, null=True)
    service_type = models.ForeignKey('AppServicetype', models.DO_NOTHING)
    client_email = models.CharField(max_length=254, blank=True, null=True)
    client_name = models.CharField(max_length=255, blank=True, null=True)
    client_phone = models.CharField(max_length=20, blank=True, null=True)
    is_paid = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_assignment'


class AppAssignmentfeedback(models.Model):
    id = models.BigAutoField(primary_key=True)
    rating = models.IntegerField()
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    assignment = models.OneToOneField(AppAssignment, models.DO_NOTHING)
    created_by = models.ForeignKey('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_assignmentfeedback'


class AppAssignmentnotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_read = models.IntegerField()
    created_at = models.DateTimeField()
    assignment = models.ForeignKey(AppAssignment, models.DO_NOTHING)
    interpreter = models.ForeignKey('AppInterpreter', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_assignmentnotification'


class AppAuditlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField()
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    timestamp = models.DateTimeField()
    user = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_auditlog'


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
    user = models.OneToOneField('AppUser', models.DO_NOTHING)
    preferred_language = models.ForeignKey('AppLanguage', models.DO_NOTHING, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_client'


class AppClientpayment(models.Model):
    id = models.BigAutoField(primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    payment_date = models.DateTimeField()
    due_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    invoice_number = models.CharField(unique=True, max_length=50)
    payment_proof = models.CharField(max_length=100, blank=True, null=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    assignment = models.ForeignKey(AppAssignment, models.DO_NOTHING, blank=True, null=True)
    client = models.ForeignKey(AppClient, models.DO_NOTHING)
    quote = models.ForeignKey('AppQuote', models.DO_NOTHING, blank=True, null=True)
    transaction = models.OneToOneField('AppFinancialtransaction', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_clientpayment'


class AppContactmessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField()
    processed = models.IntegerField()
    processed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_contactmessage'


class AppDeduction(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255)
    deduction_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payroll = models.ForeignKey('AppPayrolldocument', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_deduction'


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
    interpreter_contract = models.ForeignKey('AppInterpretercontractsignature', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)
    signing_key = models.ForeignKey('AppPgpkey', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_document'


class AppExpense(models.Model):
    id = models.BigAutoField(primary_key=True)
    expense_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    status = models.CharField(max_length=20)
    date_incurred = models.DateTimeField()
    date_paid = models.DateTimeField(blank=True, null=True)
    receipt = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)
    transaction = models.OneToOneField('AppFinancialtransaction', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_expense'


class AppFinancialtransaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    transaction_id = models.CharField(unique=True, max_length=32)
    type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_financialtransaction'


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
    user = models.OneToOneField('AppUser', models.DO_NOTHING)
    bio = models.TextField(blank=True, null=True)
    profile_image = models.CharField(max_length=100, blank=True, null=True)
    contract_acceptance_date = models.DateTimeField(blank=True, null=True)
    contract_rejection_reason = models.TextField(blank=True, null=True)
    has_accepted_contract = models.IntegerField()
    is_dashboard_enabled = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_interpreter'


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
    user = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)
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


class AppInterpreterlanguage(models.Model):
    id = models.BigAutoField(primary_key=True)
    proficiency = models.CharField(max_length=20)
    is_primary = models.IntegerField()
    certified = models.IntegerField()
    certification_details = models.TextField(blank=True, null=True)
    interpreter = models.ForeignKey(AppInterpreter, models.DO_NOTHING)
    language = models.ForeignKey('AppLanguage', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_interpreterlanguage'
        unique_together = (('interpreter', 'language'),)


class AppInterpreterpayment(models.Model):
    id = models.BigAutoField(primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    scheduled_date = models.DateTimeField()
    processed_date = models.DateTimeField(blank=True, null=True)
    reference_number = models.CharField(unique=True, max_length=50)
    payment_proof = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    assignment = models.ForeignKey(AppAssignment, models.DO_NOTHING, blank=True, null=True)
    interpreter = models.ForeignKey(AppInterpreter, models.DO_NOTHING)
    transaction = models.OneToOneField(AppFinancialtransaction, models.DO_NOTHING)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'app_interpreterpayment'


class AppLanguage(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    code = models.CharField(unique=True, max_length=10)
    is_active = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_language'


class AppLanguagee(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    code = models.CharField(unique=True, max_length=10)
    is_active = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_languagee'


class AppNotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    content = models.TextField()
    read = models.IntegerField()
    link = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField()
    recipient = models.ForeignKey('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_notification'


class AppNotificationpreference(models.Model):
    id = models.BigAutoField(primary_key=True)
    email_quote_updates = models.IntegerField()
    email_assignment_updates = models.IntegerField()
    email_payment_updates = models.IntegerField()
    sms_enabled = models.IntegerField()
    quote_notifications = models.IntegerField()
    assignment_notifications = models.IntegerField()
    payment_notifications = models.IntegerField()
    system_notifications = models.IntegerField()
    notification_frequency = models.CharField(max_length=20)
    preferred_language = models.ForeignKey(AppLanguage, models.DO_NOTHING, blank=True, null=True)
    user = models.OneToOneField('AppUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_notificationpreference'


class AppPayment(models.Model):
    id = models.BigAutoField(primary_key=True)
    payment_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(unique=True, max_length=100)
    status = models.CharField(max_length=20)
    payment_date = models.DateTimeField()
    last_updated = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    assignment = models.ForeignKey(AppAssignment, models.DO_NOTHING)
    quote = models.ForeignKey('AppQuote', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_payment'


class AppPayrolldocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    company_logo = models.CharField(max_length=100)
    company_address = models.CharField(max_length=255)
    company_phone = models.CharField(max_length=20)
    company_email = models.CharField(max_length=254)
    interpreter_name = models.CharField(max_length=100)
    interpreter_address = models.CharField(max_length=255)
    interpreter_phone = models.CharField(max_length=20)
    interpreter_email = models.CharField(max_length=254)
    document_number = models.CharField(unique=True, max_length=50)
    document_date = models.DateField()
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    routing_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'app_payrolldocument'


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


class AppPublicquoterequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    phone = models.CharField(max_length=20)
    company_name = models.CharField(max_length=100)
    requested_date = models.DateTimeField()
    duration = models.IntegerField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    special_requirements = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    processed = models.IntegerField()
    processed_at = models.DateTimeField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)
    service_type = models.ForeignKey('AppServicetype', models.DO_NOTHING)
    source_language = models.ForeignKey(AppLanguage, models.DO_NOTHING)
    target_language_id = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'app_publicquoterequest'


class AppQuote(models.Model):
    id = models.BigAutoField(primary_key=True)
    reference_number = models.CharField(unique=True, max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    valid_until = models.DateField()
    terms = models.TextField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey('AppUser', models.DO_NOTHING)
    quote_request = models.OneToOneField('AppQuoterequest', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_quote'


class AppQuoterequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    requested_date = models.DateTimeField()
    duration = models.IntegerField()
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    special_requirements = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    client = models.ForeignKey(AppClient, models.DO_NOTHING)
    source_language = models.ForeignKey(AppLanguage, models.DO_NOTHING)
    target_language = models.ForeignKey(AppLanguage, models.DO_NOTHING, related_name='appquoterequest_target_language_set')
    service_type = models.ForeignKey('AppServicetype', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_quoterequest'


class AppReimbursement(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255)
    reimbursement_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.CharField(max_length=100, blank=True, null=True)
    payroll = models.ForeignKey(AppPayrolldocument, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_reimbursement'


class AppService(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    client = models.CharField(max_length=100)
    source_language = models.CharField(max_length=50)
    target_language = models.CharField(max_length=50)
    duration = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payroll = models.ForeignKey(AppPayrolldocument, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_service'


class AppServicetype(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    base_rate = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_hours = models.IntegerField()
    cancellation_policy = models.TextField()
    requires_certification = models.IntegerField()
    active = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'app_servicetype'


class AppSigneddocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    original_document = models.CharField(max_length=100)
    signed_document = models.CharField(max_length=100, blank=True, null=True)
    signature_image = models.CharField(max_length=100, blank=True, null=True)
    signature_type = models.CharField(max_length=20)
    signature_position = models.JSONField()
    signature_metadata = models.JSONField()
    created_at = models.DateTimeField()
    user = models.ForeignKey('AppUser', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_signeddocument'


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


class AppUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AppUser, models.DO_NOTHING)
    group = models.ForeignKey('AuthGroup', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_user_groups'
        unique_together = (('user', 'group'),)


class AppUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AppUser, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_user_user_permissions'
        unique_together = (('user', 'permission'),)


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AppUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoApschedulerDjangojob(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    next_run_time = models.DateTimeField(blank=True, null=True)
    job_state = models.TextField()

    class Meta:
        managed = False
        db_table = 'django_apscheduler_djangojob'


class DjangoApschedulerDjangojobexecution(models.Model):
    id = models.BigAutoField(primary_key=True)
    status = models.CharField(max_length=50)
    run_time = models.DateTimeField()
    duration = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    finished = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    exception = models.CharField(max_length=1000, blank=True, null=True)
    traceback = models.TextField(blank=True, null=True)
    job = models.ForeignKey(DjangoApschedulerDjangojob, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_apscheduler_djangojobexecution'
        unique_together = (('job', 'run_time'),)


class DjangoCeleryBeatClockedschedule(models.Model):
    clocked_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_celery_beat_clockedschedule'


class DjangoCeleryBeatCrontabschedule(models.Model):
    minute = models.CharField(max_length=240)
    hour = models.CharField(max_length=96)
    day_of_week = models.CharField(max_length=64)
    day_of_month = models.CharField(max_length=124)
    month_of_year = models.CharField(max_length=64)
    timezone = models.CharField(max_length=63)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_crontabschedule'


class DjangoCeleryBeatIntervalschedule(models.Model):
    every = models.IntegerField()
    period = models.CharField(max_length=24)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_intervalschedule'


class DjangoCeleryBeatPeriodictask(models.Model):
    name = models.CharField(unique=True, max_length=200)
    task = models.CharField(max_length=200)
    args = models.TextField()
    kwargs = models.TextField()
    queue = models.CharField(max_length=200, blank=True, null=True)
    exchange = models.CharField(max_length=200, blank=True, null=True)
    routing_key = models.CharField(max_length=200, blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    enabled = models.IntegerField()
    last_run_at = models.DateTimeField(blank=True, null=True)
    total_run_count = models.PositiveIntegerField()
    date_changed = models.DateTimeField()
    description = models.TextField()
    crontab = models.ForeignKey(DjangoCeleryBeatCrontabschedule, models.DO_NOTHING, blank=True, null=True)
    interval = models.ForeignKey(DjangoCeleryBeatIntervalschedule, models.DO_NOTHING, blank=True, null=True)
    solar = models.ForeignKey('DjangoCeleryBeatSolarschedule', models.DO_NOTHING, blank=True, null=True)
    one_off = models.IntegerField()
    start_time = models.DateTimeField(blank=True, null=True)
    priority = models.PositiveIntegerField(blank=True, null=True)
    headers = models.TextField()
    clocked = models.ForeignKey(DjangoCeleryBeatClockedschedule, models.DO_NOTHING, blank=True, null=True)
    expire_seconds = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_periodictask'


class DjangoCeleryBeatPeriodictasks(models.Model):
    ident = models.SmallIntegerField(primary_key=True)
    last_update = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_celery_beat_periodictasks'


class DjangoCeleryBeatSolarschedule(models.Model):
    event = models.CharField(max_length=24)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_solarschedule'
        unique_together = (('event', 'latitude', 'longitude'),)


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class SocialAuthAssociation(models.Model):
    id = models.BigAutoField(primary_key=True)
    server_url = models.CharField(max_length=255)
    handle = models.CharField(max_length=255)
    secret = models.CharField(max_length=255)
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.CharField(max_length=64)

    class Meta:
        managed = False
        db_table = 'social_auth_association'
        unique_together = (('server_url', 'handle'),)


class SocialAuthCode(models.Model):
    id = models.BigAutoField(primary_key=True)
    email = models.CharField(max_length=254)
    code = models.CharField(max_length=32)
    verified = models.IntegerField()
    timestamp = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'social_auth_code'
        unique_together = (('email', 'code'),)


class SocialAuthNonce(models.Model):
    id = models.BigAutoField(primary_key=True)
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=65)

    class Meta:
        managed = False
        db_table = 'social_auth_nonce'
        unique_together = (('server_url', 'timestamp', 'salt'),)


class SocialAuthPartial(models.Model):
    id = models.BigAutoField(primary_key=True)
    token = models.CharField(max_length=32)
    next_step = models.PositiveSmallIntegerField()
    backend = models.CharField(max_length=32)
    timestamp = models.DateTimeField()
    data = models.JSONField()

    class Meta:
        managed = False
        db_table = 'social_auth_partial'


class SocialAuthUsersocialauth(models.Model):
    id = models.BigAutoField(primary_key=True)
    provider = models.CharField(max_length=32)
    uid = models.CharField(max_length=255)
    user = models.ForeignKey(AppUser, models.DO_NOTHING)
    created = models.DateTimeField()
    modified = models.DateTimeField()
    extra_data = models.JSONField()

    class Meta:
        managed = False
        db_table = 'social_auth_usersocialauth'
        unique_together = (('provider', 'uid'),)
