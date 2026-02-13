from django.db import models
from .users import AppClient, AppInterpreter, AppUser
from .core import AppLanguage, AppServicetype
from .finance import AppQuote, AppClientpayment, AppInterpreterpayment, AppFinancialtransaction  # Circular deps managed by structure

# Note: AppClientpayment and AppInterpreterpayment depend on AppAssignment which depends on AppQuote/Client/Interpreter.
# To avoid circular imports at module level, we might need string references or careful ordering.
# Since we are separating files, we will use string references for models in other files if needed, or import them.
# However, AppClientpayment needs AppAssignment. AppAssignment needs AppQuote. AppQuote needs Request.
# AppAssignment is the connector.

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
    client = models.ForeignKey(AppClient, models.DO_NOTHING, blank=True, null=True)
    interpreter = models.ForeignKey(AppInterpreter, models.DO_NOTHING, blank=True, null=True)
    source_language = models.ForeignKey(AppLanguage, models.DO_NOTHING)
    target_language = models.ForeignKey(AppLanguage, models.DO_NOTHING, related_name='appassignment_target_language_set')
    quote = models.OneToOneField(AppQuote, models.DO_NOTHING, blank=True, null=True)
    service_type = models.ForeignKey(AppServicetype, models.DO_NOTHING)
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
    created_by = models.ForeignKey(AppUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_assignmentfeedback'

class AppAssignmentnotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_read = models.IntegerField()
    created_at = models.DateTimeField()
    assignment = models.ForeignKey(AppAssignment, models.DO_NOTHING)
    interpreter = models.ForeignKey(AppInterpreter, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_assignmentnotification'

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
    quote = models.ForeignKey(AppQuote, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'app_payment'
