from rest_framework import serializers

from app.models import (
    Invoice, ClientPayment, InterpreterPayment, Expense,
    FinancialTransaction, PayrollDocument, Service,
    Reimbursement, Deduction,
    Assignment, Client, User,
)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight invoice for table views."""

    client_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            'id', 'invoice_number', 'client', 'client_name',
            'subtotal', 'tax_amount', 'total',
            'status', 'issued_date', 'due_date', 'paid_date',
            'reminder_count', 'created_at',
        )

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or str(obj.client)
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('client')


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Full invoice with nested assignments."""

    client_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            'id', 'invoice_number',
            'client', 'client_name',
            'assignments',
            'subtotal', 'tax_amount', 'total',
            'status', 'issued_date', 'due_date', 'paid_date',
            'payment_method', 'notes', 'pdf_file',
            'created_by', 'created_by_name',
            'last_reminder_sent', 'reminder_count',
            'created_at', 'updated_at',
        )

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or str(obj.client)
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_assignments(self, obj):
        from app.api.serializers.assignments import AssignmentListSerializer
        return AssignmentListSerializer(obj.assignments.all(), many=True).data

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('client', 'created_by').prefetch_related(
            'assignments__interpreter__user',
            'assignments__service_type',
            'assignments__source_language',
            'assignments__target_language',
            'assignments__client',
        )


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Create / update an invoice."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    assignments = serializers.PrimaryKeyRelatedField(
        queryset=Assignment.objects.all(), many=True, required=False
    )
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    class Meta:
        model = Invoice
        fields = (
            'id', 'invoice_number', 'client', 'assignments',
            'subtotal', 'tax_amount', 'total',
            'status', 'issued_date', 'due_date',
            'payment_method', 'notes',
            'created_by',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        subtotal = data.get('subtotal', 0)
        tax = data.get('tax_amount', 0)
        total = data.get('total')
        if total is None:
            data['total'] = subtotal + tax
        return data


# ---------------------------------------------------------------------------
# ClientPayment
# ---------------------------------------------------------------------------

class ClientPaymentSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()

    class Meta:
        model = ClientPayment
        fields = (
            'id',
            'transaction', 'client', 'client_name',
            'assignment', 'quote',
            'amount', 'tax_amount', 'total_amount',
            'payment_method', 'status',
            'payment_date', 'due_date', 'completed_date',
            'invoice_number', 'external_reference', 'notes',
        )
        read_only_fields = ('id',)

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or str(obj.client)
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('client', 'transaction')


# ---------------------------------------------------------------------------
# InterpreterPayment
# ---------------------------------------------------------------------------

class InterpreterPaymentListSerializer(serializers.ModelSerializer):
    interpreter_name = serializers.SerializerMethodField()
    assignment_info  = serializers.SerializerMethodField()

    class Meta:
        model = InterpreterPayment
        fields = (
            'id', 'reference_number',
            'interpreter', 'interpreter_name',
            'assignment', 'assignment_info', 'amount',
            'payment_method', 'status',
            'scheduled_date', 'processed_date',
            'created_at',
        )

    def get_interpreter_name(self, obj):
        if obj.interpreter and obj.interpreter.user:
            u = obj.interpreter.user
            return f"{u.first_name} {u.last_name}".strip()
        return None

    def get_assignment_info(self, obj):
        a = obj.assignment
        if not a:
            return None
        return {
            'id': a.id,
            'city': a.city,
            'state': a.state,
            'start_time': a.start_time,
            'rate': str(a.interpreter_rate) if a.interpreter_rate else None,
            'source_language': a.source_language.name if a.source_language else '',
            'target_language': a.target_language.name if a.target_language else '',
            'client': a.client.company_name if a.client else (a.client_name or ''),
            'is_paid': a.is_paid,
        }

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'interpreter__user', 'transaction',
            'assignment__client',
            'assignment__source_language',
            'assignment__target_language',
        )


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------

class ExpenseListSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = (
            'id', 'expense_type', 'amount', 'description',
            'status', 'date_incurred', 'date_paid',
            'approved_by', 'approved_by_name', 'notes',
        )

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('approved_by', 'transaction')


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """Full expense detail (same fields as list + receipt)."""
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = (
            'id', 'transaction', 'expense_type', 'amount', 'description',
            'status', 'date_incurred', 'date_paid',
            'receipt', 'approved_by', 'approved_by_name', 'notes',
        )

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('approved_by', 'transaction')


class ExpenseCreateSerializer(serializers.ModelSerializer):
    transaction = serializers.PrimaryKeyRelatedField(
        queryset=FinancialTransaction.objects.all(),
        required=False,
        allow_null=True,
    )
    approved_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Expense
        fields = (
            'id', 'transaction', 'expense_type', 'amount',
            'description', 'status', 'date_incurred', 'date_paid',
            'receipt', 'approved_by', 'notes',
        )
        read_only_fields = ('id',)


# ---------------------------------------------------------------------------
# Financial Summary (non-model serializer for dashboard / reports)
# ---------------------------------------------------------------------------

class FinancialSummarySerializer(serializers.Serializer):
    """Aggregated financial summary returned by the summary endpoint."""

    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_interpreter_payments = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_invoices = serializers.IntegerField()
    outstanding_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    overdue_invoices = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

class ServiceSerializer(serializers.ModelSerializer):
    """Payroll service line item."""

    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Service
        fields = (
            'id', 'payroll', 'date', 'client',
            'source_language', 'target_language',
            'duration', 'rate', 'amount',
        )
        read_only_fields = ('id', 'amount')


class ReimbursementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reimbursement
        fields = (
            'id', 'payroll', 'date', 'description',
            'reimbursement_type', 'amount', 'receipt',
        )
        read_only_fields = ('id',)


class DeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deduction
        fields = (
            'id', 'payroll', 'date', 'description',
            'deduction_type', 'amount',
        )
        read_only_fields = ('id',)


class PayrollDocumentSerializer(serializers.ModelSerializer):
    """Full payroll document with nested line items."""

    services = ServiceSerializer(many=True, read_only=True)
    reimbursements = ReimbursementSerializer(many=True, read_only=True)
    deductions = DeductionSerializer(many=True, read_only=True)

    total_services = serializers.SerializerMethodField()
    total_reimbursements = serializers.SerializerMethodField()
    total_deductions = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = PayrollDocument
        fields = (
            'id',
            'company_logo', 'company_address', 'company_phone', 'company_email',
            'interpreter_name', 'interpreter_address',
            'interpreter_phone', 'interpreter_email',
            'document_number', 'document_date',
            'bank_name', 'account_number', 'routing_number',
            'services', 'reimbursements', 'deductions',
            'total_services', 'total_reimbursements',
            'total_deductions', 'grand_total',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_total_services(self, obj):
        return sum(s.amount for s in obj.services.all())

    def get_total_reimbursements(self, obj):
        return sum(r.amount for r in obj.reimbursements.all())

    def get_total_deductions(self, obj):
        return sum(d.amount for d in obj.deductions.all())

    def get_grand_total(self, obj):
        services = sum(s.amount for s in obj.services.all())
        reimbursements = sum(r.amount for r in obj.reimbursements.all())
        deductions = sum(d.amount for d in obj.deductions.all())
        return services + reimbursements - deductions

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.prefetch_related('services', 'reimbursements', 'deductions')


class PayrollDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight payroll document for table views."""

    class Meta:
        model = PayrollDocument
        fields = (
            'id', 'document_number', 'document_date',
            'interpreter_name', 'interpreter_email',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


# Detail re-uses the full serializer
PayrollDocumentDetailSerializer = PayrollDocumentSerializer


class PayrollDocumentCreateSerializer(serializers.ModelSerializer):
    """Create a payroll document (header only; services added separately)."""

    class Meta:
        model = PayrollDocument
        fields = (
            'id',
            'interpreter_name', 'interpreter_address',
            'interpreter_phone', 'interpreter_email',
            'document_number', 'document_date',
            'company_address', 'company_phone', 'company_email',
            'bank_name', 'account_number', 'routing_number',
        )
        read_only_fields = ('id',)
