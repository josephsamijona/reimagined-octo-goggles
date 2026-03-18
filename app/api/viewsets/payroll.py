"""Payroll viewset: payment listing, stub generation, PDF export, and email."""
import logging
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.api.filters import InterpreterPaymentFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.finance import (
    InterpreterPaymentListSerializer,
    PayrollDocumentListSerializer,
    PayrollDocumentDetailSerializer,
    PayrollDocumentCreateSerializer,
)
from app.api.services.payroll_service import generate_payroll_pdf
from app.models import (
    InterpreterPayment, PayrollDocument, Service, Interpreter,
)

logger = logging.getLogger(__name__)


class PayrollViewSet(ViewSet):
    """
    Payroll management endpoints.

    Endpoints:
        GET  /payroll/payments/              - list interpreter payments
        POST /payroll/payments/{id}/process/ - process a pending payment
        GET  /payroll/stubs/                 - list pay stubs
        POST /payroll/stubs/                 - generate a pay stub
        POST /payroll/stubs/batch/           - batch generate stubs
        GET  /payroll/stubs/{id}/            - stub detail
        GET  /payroll/stubs/{id}/pdf/        - export stub as PDF
        POST /payroll/stubs/{id}/send/       - email stub to interpreter
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='payments')
    def payments(self, request):
        """List interpreter payments with filters."""
        qs = (
            InterpreterPayment.objects
            .select_related('interpreter__user', 'assignment', 'transaction')
            .all()
        )

        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        interpreter_filter = request.query_params.get('interpreter')
        if interpreter_filter:
            qs = qs.filter(interpreter_id=interpreter_filter)

        qs = qs.order_by('-created_at')

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = InterpreterPaymentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['post'], url_path=r'payments/(?P<payment_id>\d+)/process')
    def process_payment(self, request, payment_id=None):
        """Process a pending interpreter payment."""
        try:
            payment = InterpreterPayment.objects.get(pk=payment_id)
        except InterpreterPayment.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not payment.can_be_processed():
            return Response(
                {'detail': f'Cannot process payment in status {payment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.mark_as_processing()

        return Response({
            'id': payment.id,
            'reference_number': payment.reference_number,
            'status': payment.status,
        })

    # ------------------------------------------------------------------
    # Pay Stubs
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get', 'post'], url_path='stubs')
    def stubs(self, request):
        """List or create pay stubs."""
        if request.method == 'POST':
            return self._create_stub(request)
        return self._list_stubs(request)

    def _list_stubs(self, request):
        qs = PayrollDocument.objects.all().order_by('-created_at')

        interpreter_name = request.query_params.get('interpreter_name')
        if interpreter_name:
            qs = qs.filter(interpreter_name__icontains=interpreter_name)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PayrollDocumentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def _create_stub(self, request):
        serializer = PayrollDocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stub = serializer.save()
        return Response(
            PayrollDocumentDetailSerializer(stub).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='stubs/batch')
    def batch_stubs(self, request):
        """Batch generate pay stubs for multiple interpreters."""
        interpreter_ids = request.data.get('interpreter_ids', [])
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')

        if not interpreter_ids:
            return Response(
                {'detail': 'interpreter_ids is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        interpreters = Interpreter.objects.filter(
            id__in=interpreter_ids,
        ).select_related('user')

        created_stubs = []
        for interp in interpreters:
            import random
            year = timezone.now().year
            doc_num = f"PS-{year}-{random.randint(10000, 99999)}"

            stub = PayrollDocument.objects.create(
                interpreter_name=f"{interp.user.first_name} {interp.user.last_name}",
                interpreter_email=interp.user.email,
                interpreter_phone=interp.user.phone or '',
                interpreter_address=f"{interp.address}, {interp.city}, {interp.state} {interp.zip_code}",
                document_number=doc_num,
                document_date=timezone.now().date(),
                company_address='500 GROSSMAN DR, BRAINTREE, MA, 02184',
                company_email='info@jhbridgetranslation.com',
            )

            # Populate services from completed assignments in the period
            from app.models import Assignment
            assignments_qs = Assignment.objects.filter(
                interpreter=interp,
                status='COMPLETED',
            )
            if period_start:
                assignments_qs = assignments_qs.filter(start_time__date__gte=period_start)
            if period_end:
                assignments_qs = assignments_qs.filter(start_time__date__lte=period_end)

            for a in assignments_qs.select_related('client', 'source_language', 'target_language'):
                duration_hours = (a.end_time - a.start_time).total_seconds() / 3600
                client_name = a.client.company_name if a.client else (a.client_name or '')
                Service.objects.create(
                    payroll=stub,
                    date=a.start_time.date(),
                    client=client_name,
                    source_language=a.source_language.name if a.source_language else '',
                    target_language=a.target_language.name if a.target_language else '',
                    duration=round(Decimal(str(duration_hours)), 2),
                    rate=a.interpreter_rate,
                )

            created_stubs.append({
                'id': stub.id,
                'document_number': stub.document_number,
                'interpreter_name': stub.interpreter_name,
            })

        return Response(created_stubs, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path=r'stubs/(?P<stub_id>\d+)')
    def stub_detail(self, request, stub_id=None):
        """Retrieve a single pay stub with services, reimbursements, deductions."""
        try:
            stub = (
                PayrollDocument.objects
                .prefetch_related('services', 'reimbursements', 'deductions')
                .get(pk=stub_id)
            )
        except PayrollDocument.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(PayrollDocumentDetailSerializer(stub).data)

    @action(detail=False, methods=['get'], url_path=r'stubs/(?P<stub_id>\d+)/pdf')
    def stub_pdf(self, request, stub_id=None):
        """Export pay stub as PDF."""
        try:
            stub = (
                PayrollDocument.objects
                .prefetch_related('services', 'reimbursements', 'deductions')
                .get(pk=stub_id)
            )
        except PayrollDocument.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            pdf_buffer = generate_payroll_pdf(stub)
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="paystub-{stub.document_number}.pdf"'
            return response
        except Exception as e:
            logger.error(f"Failed to generate PDF for stub {stub_id}: {e}")
            return Response(
                {'detail': 'Failed to generate PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], url_path=r'stubs/(?P<stub_id>\d+)/send')
    def send_stub(self, request, stub_id=None):
        """Email the pay stub PDF to the interpreter."""
        try:
            stub = (
                PayrollDocument.objects
                .prefetch_related('services', 'reimbursements', 'deductions')
                .get(pk=stub_id)
            )
        except PayrollDocument.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not stub.interpreter_email:
            return Response(
                {'detail': 'No interpreter email on this stub.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from app.services.email_service import PayrollEmailService
            pdf_buffer = generate_payroll_pdf(stub)
            ok = PayrollEmailService.send_stub(stub, pdf_buffer.getvalue())
            if not ok:
                return Response(
                    {'detail': 'Failed to send email.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response({'detail': f'Pay stub emailed to {stub.interpreter_email}.'})
        except Exception as e:
            logger.error(f"Failed to email stub {stub_id}: {e}")
            return Response(
                {'detail': 'Failed to send email.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
