from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import decimal
from decimal import Decimal

class FinancialTransaction(models.Model):
    """Table principale pour tracer toutes les transactions financières"""
    class TransactionType(models.TextChoices):
        INCOME = 'INCOME', _('Income')
        EXPENSE = 'EXPENSE', _('Expense')
        INTERNAL = 'INTERNAL', _('Internal Transfer')

    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True)
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'app_financialtransaction'

class ClientPayment(models.Model):
    """Gestion des paiements reçus des clients"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
        CANCELLED = 'CANCELLED', _('Cancelled')
        DISPUTED = 'DISPUTED', _('Disputed')

    class PaymentMethod(models.TextChoices):
    # Méthodes bancaires traditionnelles
        CREDIT_CARD = 'CREDIT_CARD', _('Credit Card')
        DEBIT_CARD = 'DEBIT_CARD', _('Debit Card')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        ACH = 'ACH', _('ACH')
        CHECK = 'CHECK', _('Check')
        CASH = 'CASH', _('Cash')
        
        # Services de paiement numérique US
        ZELLE = 'ZELLE', _('Zelle')
        VENMO = 'VENMO', _('Venmo')
        CASH_APP = 'CASH_APP', _('Cash App')
        PAYPAL = 'PAYPAL', _('PayPal')
        
        # Portefeuilles mobiles
        APPLE_PAY = 'APPLE_PAY', _('Apple Pay')
        GOOGLE_PAY = 'GOOGLE_PAY', _('Google Pay')
        SAMSUNG_PAY = 'SAMSUNG_PAY', _('Samsung Pay')
        
        # Services de transfert internationaux
        WESTERN_UNION = 'WESTERN_UNION', _('Western Union')
        MONEY_GRAM = 'MONEY_GRAM', _('MoneyGram')
        TAPTP_SEND = 'TAPTP_SEND', _('Tap Tap Send')
        REMITLY = 'REMITLY', _('Remitly')
        WORLDREMIT = 'WORLDREMIT', _('WorldRemit')
        XOOM = 'XOOM', _('Xoom')
        WISE = 'WISE', _('Wise (TransferWise)')
        
        # Plateformes de paiement
        STRIPE = 'STRIPE', _('Stripe')
        SQUARE = 'SQUARE', _('Square')
        
        # Crypto-monnaies
        CRYPTO_BTC = 'CRYPTO_BTC', _('Bitcoin')
        CRYPTO_ETH = 'CRYPTO_ETH', _('Ethereum')
        CRYPTO_USDT = 'CRYPTO_USDT', _('USDT')
        
        # Autres
        OTHER = 'OTHER', _('Other')

    transaction = models.OneToOneField(FinancialTransaction, on_delete=models.PROTECT)
    client = models.ForeignKey('Client', on_delete=models.PROTECT)
    assignment = models.ForeignKey('Assignment', on_delete=models.PROTECT, null=True, blank=True)
    quote = models.ForeignKey('Quote', on_delete=models.PROTECT, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_method = models.CharField(max_length=50, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    
    payment_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    invoice_number = models.CharField(max_length=50, unique=True)
    payment_proof = models.FileField(upload_to='payment_proofs/', null=True, blank=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'app_clientpayment'

class InterpreterPayment(models.Model):
    """Gestion des paiements aux interprètes"""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    class PaymentMethod(models.TextChoices):
        # Méthodes bancaires traditionnelles
        CREDIT_CARD = 'CREDIT_CARD', _('Credit Card')
        DEBIT_CARD = 'DEBIT_CARD', _('Debit Card')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        ACH = 'ACH', _('ACH')
        CHECK = 'CHECK', _('Check')
        CASH = 'CASH', _('Cash')
        
        # Services de paiement numérique US
        ZELLE = 'ZELLE', _('Zelle')
        VENMO = 'VENMO', _('Venmo')
        CASH_APP = 'CASH_APP', _('Cash App')
        PAYPAL = 'PAYPAL', _('PayPal')
        
        # Portefeuilles mobiles
        APPLE_PAY = 'APPLE_PAY', _('Apple Pay')
        GOOGLE_PAY = 'GOOGLE_PAY', _('Google Pay')
        SAMSUNG_PAY = 'SAMSUNG_PAY', _('Samsung Pay')
        
        # Services de transfert internationaux
        WESTERN_UNION = 'WESTERN_UNION', _('Western Union')
        MONEY_GRAM = 'MONEY_GRAM', _('MoneyGram')
        TAPTP_SEND = 'TAPTP_SEND', _('Tap Tap Send')
        REMITLY = 'REMITLY', _('Remitly')
        WORLDREMIT = 'WORLDREMIT', _('WorldRemit')
        XOOM = 'XOOM', _('Xoom')
        WISE = 'WISE', _('Wise (TransferWise)')
        
        # Plateformes de paiement
        STRIPE = 'STRIPE', _('Stripe')
        SQUARE = 'SQUARE', _('Square')
        
        # Crypto-monnaies
        CRYPTO_BTC = 'CRYPTO_BTC', _('Bitcoin')
        CRYPTO_ETH = 'CRYPTO_ETH', _('Ethereum')
        CRYPTO_USDT = 'CRYPTO_USDT', _('USDT')
        
        # Autres
        OTHER = 'OTHER', _('Other')

    # Relations
    transaction = models.OneToOneField('FinancialTransaction', on_delete=models.PROTECT)
    interpreter = models.ForeignKey('Interpreter', on_delete=models.PROTECT)
    assignment = models.ForeignKey('Assignment', on_delete=models.PROTECT, null=True, blank=True)
    
    # Informations de paiement
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Dates
    scheduled_date = models.DateTimeField()
    processed_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)
    
    # Informations supplémentaires
    reference_number = models.CharField(max_length=50, unique=True)
    payment_proof = models.FileField(upload_to='interpreter_payment_proofs/', null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Interpreter Payment'
        verbose_name_plural = 'Interpreter Payments'
        indexes = [
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['interpreter', 'status']),
            models.Index(fields=['created_at']),
        ]
        db_table = 'app_interpreterpayment'

    def __str__(self):
        return f"Payment {self.reference_number} - {self.interpreter}"

    def clean(self):
        """Validation personnalisée"""
        if self.status == self.Status.COMPLETED and not self.processed_date:
            raise ValidationError({
                'processed_date': 'Processed date is required when status is completed'
            })

    def save(self, *args, **kwargs):
        """Surcharge de la méthode save pour validation"""
        self.clean()
        super().save(*args, **kwargs)

    def can_be_processed(self):
        """Vérifie si le paiement peut être traité"""
        return self.status == self.Status.PENDING

    def can_be_completed(self):
        """Vérifie si le paiement peut être marqué comme complété"""
        return self.status == self.Status.PROCESSING

    def mark_as_processing(self):
        """Marque le paiement comme en cours de traitement"""
        if self.can_be_processed():
            self.status = self.Status.PROCESSING
            self.save()
            return True
        return False

    def mark_as_completed(self):
        """Marque le paiement comme complété"""
        if self.can_be_completed():
            self.status = self.Status.COMPLETED
            self.processed_date = timezone.now()
            self.save()
            return True
        return False

    def mark_as_failed(self):
        """Marque le paiement comme échoué"""
        if self.status in [self.Status.PENDING, self.Status.PROCESSING]:
            self.status = self.Status.FAILED
            self.save()
            return True
        return False

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')

    class PaymentType(models.TextChoices):
        CLIENT_PAYMENT = 'CLIENT_PAYMENT', _('Client Payment')
        INTERPRETER_PAYMENT = 'INTERPRETER_PAYMENT', _('Interpreter Payment')


    quote = models.ForeignKey('Quote', on_delete=models.PROTECT, null=True, blank=True)
    assignment = models.ForeignKey('Assignment', on_delete=models.PROTECT)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    payment_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'app_payment'

class Expense(models.Model):
    """Gestion des dépenses de l'entreprise"""
    class ExpenseType(models.TextChoices):
        OPERATIONAL = 'OPERATIONAL', _('Operational')
        ADMINISTRATIVE = 'ADMINISTRATIVE', _('Administrative')
        MARKETING = 'MARKETING', _('Marketing')
        SALARY = 'SALARY', _('Salary')
        TAX = 'TAX', _('Tax')
        OTHER = 'OTHER', _('Other')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        PAID = 'PAID', _('Paid')
        REJECTED = 'REJECTED', _('Rejected')

    transaction = models.OneToOneField(FinancialTransaction, on_delete=models.PROTECT)
    expense_type = models.CharField(max_length=20, choices=ExpenseType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    
    status = models.CharField(max_length=20, choices=Status.choices)
    date_incurred = models.DateTimeField()
    date_paid = models.DateTimeField(null=True, blank=True)
    
    receipt = models.FileField(upload_to='expense_receipts/', null=True, blank=True)
    approved_by = models.ForeignKey('User', on_delete=models.PROTECT, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'app_expense'

class PayrollDocument(models.Model):
    # Company Information
    company_logo = models.ImageField(upload_to='company_logos/', blank=True)
    company_address = models.CharField(max_length=255, blank=True)
    company_phone = models.CharField(max_length=20, blank=True)
    company_email = models.EmailField(blank=True)

    # Interpreter Information
    interpreter_name = models.CharField(max_length=100, blank=True)
    interpreter_address = models.CharField(max_length=255, blank=True)
    interpreter_phone = models.CharField(max_length=20, blank=True)
    interpreter_email = models.EmailField(blank=True)

    # Document Information
    document_number = models.CharField(max_length=50, unique=True)
    document_date = models.DateField()

    # Payment Information (Optional)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    routing_number = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'app_payrolldocument'

    def __str__(self):
        return f"Payroll {self.document_number} - {self.interpreter_name}"

class Service(models.Model):
    payroll = models.ForeignKey(PayrollDocument, on_delete=models.CASCADE, related_name='services')
    date = models.DateField(blank=True, null=True)
    client = models.CharField(max_length=100, blank=True)
    source_language = models.CharField(max_length=50, blank=True)
    target_language = models.CharField(max_length=50, blank=True)
    duration = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    @property
    def amount(self):
        try:
            if self.duration is None or self.rate is None:
                return Decimal('0')
            return Decimal(str(self.duration)) * Decimal(str(self.rate))
        except (TypeError, ValueError, decimal.InvalidOperation):
            return Decimal('0')

    class Meta:
        db_table = 'app_service'

class Reimbursement(models.Model):
    REIMBURSEMENT_TYPES = [
        ('TRANSPORT', 'Transportation'),
        ('PARKING', 'Parking fees'),
        ('TOLL', 'Toll fees'),
        ('MEAL', 'Meals'),
        ('ACCOMMODATION', 'Accommodation'),
        ('EQUIPMENT', 'Interpretation equipment'),
        ('TRAINING', 'Professional training'),
        ('COMMUNICATION', 'Communication fees'),
        ('PRINTING', 'Document printing'),
        ('OTHER', 'Other reimbursable expense'),
    ]
    
    payroll = models.ForeignKey(PayrollDocument, on_delete=models.CASCADE, related_name='reimbursements')
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255)
    reimbursement_type = models.CharField(max_length=50, choices=REIMBURSEMENT_TYPES, default='OTHER')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    
    class Meta:
        db_table = 'app_reimbursement'

    def __str__(self):
        return f"{self.get_reimbursement_type_display()}: {self.description} - ${self.amount}"

class Deduction(models.Model):
    DEDUCTION_TYPES = [
        ('ADVANCE', 'Payment advance'),
        ('EQUIPMENT', 'Provided equipment'),
        ('CANCELLATION', 'Cancellation penalty'),
        ('LATE', 'Late penalty'),
        ('TAX', 'Tax withholding'),
        ('CONTRIBUTION', 'Social contributions'),
        ('ADMIN_FEE', 'Administrative fees'),
        ('ADJUSTMENT', 'Invoice adjustment'),
        ('OTHER', 'Other deduction'),
    ]
    
    payroll = models.ForeignKey(PayrollDocument, on_delete=models.CASCADE, related_name='deductions')
    date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=255)
    deduction_type = models.CharField(max_length=50, choices=DEDUCTION_TYPES, default='OTHER')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'app_deduction'

    def __str__(self):
        return f"{self.get_deduction_type_display()}: {self.description} - ${self.amount}"
