from django.db import models
from .users import AppUser, AppClient, AppInterpreter
from .core import AppLanguage, AppServicetype

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
    service_type = models.ForeignKey(AppServicetype, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_quoterequest'

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
    processed_by = models.ForeignKey(AppUser, models.DO_NOTHING, blank=True, null=True)
    service_type = models.ForeignKey(AppServicetype, models.DO_NOTHING)
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
    created_by = models.ForeignKey(AppUser, models.DO_NOTHING)
    quote_request = models.OneToOneField(AppQuoterequest, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_quote'

class AppFinancialtransaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    transaction_id = models.CharField(unique=True, max_length=32)
    type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(AppUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_financialtransaction'

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

class AppDeduction(models.Model):
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255)
    deduction_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payroll = models.ForeignKey(AppPayrolldocument, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_deduction'

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
    approved_by = models.ForeignKey(AppUser, models.DO_NOTHING, blank=True, null=True)
    transaction = models.OneToOneField(AppFinancialtransaction, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_expense'
