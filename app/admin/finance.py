from django.contrib import admin
from app import models
from .utils import format_boston_datetime

@admin.register(models.FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'type', 'amount', 'created_by', 'date')
    list_filter = ('type', 'date')
    search_fields = ('transaction_id', 'description', 'notes')
    readonly_fields = ('transaction_id', 'date')
    
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'type',
                'amount',
                'description',
                'created_by'
            )
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                ('transaction_id', 'date')
            ),
            'classes': ('collapse',)
        }),
    )

@admin.register(models.ClientPayment)
class ClientPaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client', 'amount', 'payment_method', 'status', 'formatted_payment_date')
    list_filter = ('status', 'payment_method', 'payment_date')
    search_fields = ('invoice_number', 'client__company_name', 'external_reference')
    raw_id_fields = ('transaction', 'client', 'assignment', 'quote')
    readonly_fields = ('payment_date', 'completed_date')

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'transaction',
                ('client', 'assignment', 'quote'),
                ('amount', 'tax_amount', 'total_amount'),
                ('payment_method', 'status')
            )
        }),
        ('Dates', {
            'fields': (
                ('payment_date', 'due_date', 'completed_date'),
            )
        }),
        ('Reference Information', {
            'fields': (
                'invoice_number',
                'external_reference',
                'payment_proof'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def formatted_payment_date(self, obj):
        return format_boston_datetime(obj.payment_date)
    formatted_payment_date.short_description = "Payment Date (Boston)"

@admin.register(models.InterpreterPayment)
class InterpreterPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'interpreter', 'amount', 'payment_method', 'status', 'formatted_scheduled_date')
    list_filter = ('status', 'payment_method', 'scheduled_date')
    search_fields = ('reference_number', 'interpreter__user__first_name', 'interpreter__user__last_name')
    raw_id_fields = ('transaction', 'interpreter', 'assignment')
    readonly_fields = ('processed_date',)

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'transaction',
                ('interpreter', 'assignment'),
                'amount',
                ('payment_method', 'status')
            )
        }),
        ('Scheduling', {
            'fields': (
                ('scheduled_date', 'processed_date'),
            )
        }),
        ('Reference Information', {
            'fields': (
                'reference_number',
                'payment_proof'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def formatted_scheduled_date(self, obj):
        return format_boston_datetime(obj.scheduled_date)
    formatted_scheduled_date.short_description = "Scheduled Date (Boston)"

@admin.register(models.Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'expense_type', 'amount', 'status', 'formatted_date_incurred')
    list_filter = ('status', 'expense_type', 'date_incurred')
    search_fields = ('description', 'notes')
    raw_id_fields = ('transaction', 'approved_by')
    readonly_fields = ('date_paid',)

    fieldsets = (
        ('Expense Information', {
            'fields': (
                'transaction',
                ('expense_type', 'amount'),
                'description',
                'status'
            )
        }),
        ('Dates', {
            'fields': (
                ('date_incurred', 'date_paid'),
            )
        }),
        ('Approval', {
            'fields': (
                'approved_by',
                'receipt'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def formatted_date_incurred(self, obj):
        return format_boston_datetime(obj.date_incurred)
    formatted_date_incurred.short_description = "Date Incurred (Boston)"

    def transaction_id(self, obj):
        return obj.transaction.transaction_id if obj.transaction else '-'
    transaction_id.short_description = "Transaction ID"

class ServiceInline(admin.TabularInline):
    model = models.Service
    extra = 1

class ReimbursementInline(admin.TabularInline):
    model = models.Reimbursement
    extra = 0

class DeductionInline(admin.TabularInline):
    model = models.Deduction
    extra = 0

@admin.register(models.PayrollDocument)
class PayrollDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_number', 'interpreter_name', 'document_date', 'created_at')
    search_fields = ('document_number', 'interpreter_name', 'interpreter_email')
    list_filter = ('document_date', 'created_at')
    date_hierarchy = 'document_date'
    inlines = [ServiceInline, ReimbursementInline, DeductionInline]
    fieldsets = (
        ('Company Information', {
            'fields': ('company_logo', 'company_address', 'company_phone', 'company_email')
        }),
        ('Interpreter Information', {
            'fields': ('interpreter_name', 'interpreter_address', 'interpreter_phone', 'interpreter_email')
        }),
        ('Document Information', {
            'fields': ('document_number', 'document_date')
        }),
        ('Payment Information', {
            'fields': ('bank_name', 'account_number', 'routing_number'),
            'classes': ('collapse',)
        }),
    )

@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('payroll', 'date', 'client', 'source_language', 'target_language', 'duration', 'rate', 'amount')
    list_filter = ('date',)
    search_fields = ('client', 'source_language', 'target_language')

@admin.register(models.Reimbursement)
class ReimbursementAdmin(admin.ModelAdmin):
    list_display = ('payroll', 'date', 'reimbursement_type', 'description', 'amount')
    list_filter = ('date', 'reimbursement_type')
    search_fields = ('description',)

@admin.register(models.Deduction)
class DeductionAdmin(admin.ModelAdmin):
    list_display = ('payroll', 'date', 'deduction_type', 'description', 'amount')
    list_filter = ('date', 'deduction_type')
    search_fields = ('description',)

@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'payment_type', 'amount', 'status', 'formatted_payment_date')
    list_filter = ('status', 'payment_type', 'payment_date')
    search_fields = ('transaction_id', 'assignment__client__company_name')
    readonly_fields = ('payment_date', 'last_updated')
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_type', 'amount', 'payment_method')
        }),
        ('Related Records', {
            'fields': ('quote', 'assignment')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'status', 'notes')
        }),
        ('System Information', {
            'fields': ('payment_date', 'last_updated'), 
            'classes': ('collapse',)
        }),
    )
    def formatted_payment_date(self, obj):
        return format_boston_datetime(obj.payment_date)
    formatted_payment_date.short_description = "Payment Date (Boston)"
