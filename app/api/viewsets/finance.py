"""Finance viewset: invoices, expenses, revenue analytics, and summary."""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.api.filters import InvoiceFilter, ExpenseFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.finance import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    ExpenseCreateSerializer,
)
from app.api.services.invoice_service import generate_invoice_number
from app.models import (
    Invoice, Expense, ClientPayment, InterpreterPayment,
    FinancialTransaction, Assignment,
)

logger = logging.getLogger(__name__)


class FinanceViewSet(ViewSet):
    """
    Financial overview, invoice CRUD, expense CRUD, and revenue analytics.

    Endpoints:
        GET  /finance/summary/
        GET  /finance/invoices/
        POST /finance/invoices/
        GET  /finance/invoices/{id}/
        POST /finance/invoices/{id}/send/
        POST /finance/invoices/{id}/mark-paid/
        POST /finance/invoices/{id}/remind/
        GET  /finance/expenses/
        POST /finance/expenses/
        POST /finance/expenses/{id}/approve/
        POST /finance/expenses/{id}/pay/
        GET  /finance/analytics/revenue-by-service/
        GET  /finance/analytics/revenue-by-client/
        GET  /finance/analytics/revenue-by-language/
        GET  /finance/analytics/pnl/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """High-level financial summary."""
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_revenue = ClientPayment.objects.filter(
            status='COMPLETED',
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        mtd_revenue = ClientPayment.objects.filter(
            status='COMPLETED', payment_date__gte=month_start,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_expenses = Expense.objects.filter(
            status__in=['APPROVED', 'PAID'],
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        mtd_expenses = Expense.objects.filter(
            status__in=['APPROVED', 'PAID'], date_incurred__gte=month_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        outstanding_invoices = Invoice.objects.filter(
            status__in=['SENT', 'OVERDUE'],
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        pending_payments = InterpreterPayment.objects.filter(
            status='PENDING',
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return Response({
            'total_revenue': str(total_revenue),
            'mtd_revenue': str(mtd_revenue),
            'total_expenses': str(total_expenses),
            'mtd_expenses': str(mtd_expenses),
            'outstanding_invoices': str(outstanding_invoices),
            'pending_interpreter_payments': str(pending_payments),
            'net_profit': str(total_revenue - total_expenses),
        })

    # ------------------------------------------------------------------
    # Invoices CRUD
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get', 'post'], url_path='invoices')
    def invoices(self, request):
        """List or create invoices."""
        if request.method == 'POST':
            return self._create_invoice(request)
        return self._list_invoices(request)

    def _list_invoices(self, request):
        qs = Invoice.objects.select_related('client__user', 'created_by').all()

        # Apply filters manually since ViewSet doesn't have filter_queryset
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        client_filter = request.query_params.get('client')
        if client_filter:
            qs = qs.filter(client_id=client_filter)

        qs = qs.order_by('-created_at')

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = InvoiceListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def _create_invoice(self, request):
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = serializer.save(
            invoice_number=generate_invoice_number(),
            created_by=request.user,
        )

        return Response(
            InvoiceDetailSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path=r'invoices/(?P<invoice_id>\d+)')
    def invoice_detail(self, request, invoice_id=None):
        """Retrieve a single invoice."""
        try:
            invoice = Invoice.objects.select_related('client__user', 'created_by').get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvoiceDetailSerializer(invoice).data)

    @action(detail=False, methods=['post'], url_path=r'invoices/(?P<invoice_id>\d+)/send')
    def send_invoice(self, request, invoice_id=None):
        """Mark invoice as SENT and set issued_date."""
        try:
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.status not in ['DRAFT']:
            return Response(
                {'detail': f'Cannot send invoice in status {invoice.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = Invoice.Status.SENT
        invoice.issued_date = timezone.now().date()
        invoice.save()

        return Response({'id': invoice.id, 'status': invoice.status, 'issued_date': str(invoice.issued_date)})

    @action(detail=False, methods=['post'], url_path=r'invoices/(?P<invoice_id>\d+)/mark-paid')
    def mark_paid(self, request, invoice_id=None):
        """Mark invoice as paid."""
        try:
            invoice = Invoice.objects.get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.status not in ['SENT', 'OVERDUE']:
            return Response(
                {'detail': f'Cannot mark as paid from status {invoice.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.status = Invoice.Status.PAID
        invoice.paid_date = timezone.now().date()
        invoice.payment_method = request.data.get('payment_method', '')
        invoice.save()

        return Response({'id': invoice.id, 'status': invoice.status, 'paid_date': str(invoice.paid_date)})

    @action(detail=False, methods=['post'], url_path=r'invoices/(?P<invoice_id>\d+)/remind')
    def remind_invoice(self, request, invoice_id=None):
        """Send a payment reminder for an invoice."""
        try:
            invoice = Invoice.objects.select_related('client__user').get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if invoice.status not in ['SENT', 'OVERDUE']:
            return Response(
                {'detail': 'Can only remind for SENT or OVERDUE invoices.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.last_reminder_sent = timezone.now()
        invoice.reminder_count = (invoice.reminder_count or 0) + 1
        invoice.save(update_fields=['last_reminder_sent', 'reminder_count'])

        # Create notification for client
        try:
            from app.models import Notification
            Notification.objects.create(
                recipient=invoice.client.user,
                type='PAYMENT_REMINDER',
                title=f'Payment Reminder: Invoice {invoice.invoice_number}',
                content=f'Reminder: Invoice {invoice.invoice_number} for ${invoice.total} is due on {invoice.due_date}.',
            )
        except Exception as e:
            logger.error(f"Failed to create reminder notification: {e}")

        return Response({
            'id': invoice.id,
            'reminder_count': invoice.reminder_count,
            'last_reminder_sent': invoice.last_reminder_sent,
        })

    # ------------------------------------------------------------------
    # Expenses CRUD
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get', 'post'], url_path='expenses')
    def expenses(self, request):
        """List or create expenses."""
        if request.method == 'POST':
            return self._create_expense(request)
        return self._list_expenses(request)

    def _list_expenses(self, request):
        qs = Expense.objects.select_related('transaction', 'approved_by').all()

        expense_type = request.query_params.get('expense_type')
        if expense_type:
            qs = qs.filter(expense_type=expense_type)

        expense_status = request.query_params.get('status')
        if expense_status:
            qs = qs.filter(status=expense_status)

        qs = qs.order_by('-date_incurred')

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ExpenseListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def _create_expense(self, request):
        serializer = ExpenseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create financial transaction first
        transaction = FinancialTransaction.objects.create(
            type='EXPENSE',
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data['description'],
            created_by=request.user,
        )

        expense = serializer.save(transaction=transaction)
        return Response(
            ExpenseDetailSerializer(expense).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path=r'expenses/(?P<expense_id>\d+)/approve')
    def approve_expense(self, request, expense_id=None):
        """Approve a pending expense."""
        try:
            expense = Expense.objects.get(pk=expense_id)
        except Expense.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if expense.status != 'PENDING':
            return Response(
                {'detail': f'Cannot approve expense in status {expense.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = 'APPROVED'
        expense.approved_by = request.user
        expense.save()

        return Response({'id': expense.id, 'status': expense.status})

    @action(detail=False, methods=['post'], url_path=r'expenses/(?P<expense_id>\d+)/pay')
    def pay_expense(self, request, expense_id=None):
        """Mark an approved expense as paid."""
        try:
            expense = Expense.objects.get(pk=expense_id)
        except Expense.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if expense.status != 'APPROVED':
            return Response(
                {'detail': f'Cannot pay expense in status {expense.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = 'PAID'
        expense.date_paid = timezone.now()
        expense.save()

        return Response({'id': expense.id, 'status': expense.status, 'date_paid': expense.date_paid})

    # ------------------------------------------------------------------
    # Revenue Analytics
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='analytics/revenue-by-service')
    def revenue_by_service(self, request):
        """Revenue breakdown by service type."""
        data = (
            Assignment.objects
            .filter(status='COMPLETED', is_paid=True)
            .values('service_type__name')
            .annotate(
                count=Count('id'),
                total_revenue=Sum('total_interpreter_payment'),
            )
            .order_by('-total_revenue')
        )
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='analytics/revenue-by-client')
    def revenue_by_client(self, request):
        """Revenue breakdown by client."""
        data = (
            ClientPayment.objects
            .filter(status='COMPLETED')
            .values('client__company_name')
            .annotate(
                count=Count('id'),
                total_revenue=Sum('total_amount'),
            )
            .order_by('-total_revenue')[:20]
        )
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='analytics/revenue-by-language')
    def revenue_by_language(self, request):
        """Revenue breakdown by language pair."""
        data = (
            Assignment.objects
            .filter(status='COMPLETED')
            .values('source_language__name', 'target_language__name')
            .annotate(
                count=Count('id'),
                total_revenue=Sum('total_interpreter_payment'),
            )
            .order_by('-total_revenue')[:20]
        )
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='analytics/pnl')
    def pnl(self, request):
        """Profit and loss summary (monthly for last 12 months)."""
        now = timezone.now()
        twelve_months_ago = now - timedelta(days=365)

        revenue = (
            ClientPayment.objects
            .filter(status='COMPLETED', payment_date__gte=twelve_months_ago)
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum('total_amount'))
            .order_by('month')
        )

        expenses = (
            Expense.objects
            .filter(status__in=['APPROVED', 'PAID'], date_incurred__gte=twelve_months_ago)
            .annotate(month=TruncMonth('date_incurred'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

        rev_map = {r['month'].strftime('%Y-%m'): r['total'] for r in revenue}
        exp_map = {e['month'].strftime('%Y-%m'): e['total'] for e in expenses}
        months = sorted(set(list(rev_map.keys()) + list(exp_map.keys())))

        data = []
        for m in months:
            rev = rev_map.get(m, Decimal('0'))
            exp = exp_map.get(m, Decimal('0'))
            data.append({
                'month': m,
                'revenue': str(rev),
                'expenses': str(exp),
                'profit': str(rev - exp),
            })

        return Response(data)
