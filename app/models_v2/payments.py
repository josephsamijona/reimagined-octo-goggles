from django.db import models
from .users import AppClient, AppInterpreter
from .finance import AppQuote, AppFinancialtransaction
from .assignments import AppAssignment

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
    quote = models.ForeignKey(AppQuote, models.DO_NOTHING, blank=True, null=True)
    transaction = models.OneToOneField(AppFinancialtransaction, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'app_clientpayment'

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
