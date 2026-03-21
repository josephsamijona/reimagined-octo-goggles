"""Payroll viewset: payment listing, stub generation, PDF export, and email."""
import logging
from decimal import Decimal

from django.core.mail import EmailMessage
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
from app.api.services.payroll_service import (
    generate_payroll_pdf, generate_earnings_summary_pdf,
    COMPANY_ADDRESS, COMPANY_EMAIL, COMPANY_PHONE,
)
from app.api.services.reference_service import generate_unique_reference
from app.models import (
    InterpreterPayment, PayrollDocument, Service, Interpreter, Assignment,
    Reimbursement, Deduction,
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
        """Transition a PENDING interpreter payment → PROCESSING."""
        try:
            payment = InterpreterPayment.objects.select_related('interpreter__user').get(pk=payment_id)
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
            'interpreter_name': (
                f"{payment.interpreter.user.first_name} {payment.interpreter.user.last_name}".strip()
                if payment.interpreter and payment.interpreter.user else ''
            ),
        })

    @action(detail=False, methods=['post'], url_path=r'payments/(?P<payment_id>\d+)/complete')
    def complete_payment(self, request, payment_id=None):
        """Transition a PROCESSING interpreter payment → COMPLETED (marks assignment as paid)."""
        try:
            payment = InterpreterPayment.objects.select_related('interpreter__user', 'assignment').get(pk=payment_id)
        except InterpreterPayment.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not payment.can_be_completed():
            return Response(
                {'detail': f'Cannot complete payment in status {payment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.mark_as_completed()  # also sets assignment.is_paid = True via model method

        return Response({
            'id': payment.id,
            'reference_number': payment.reference_number,
            'status': payment.status,
            'processed_date': payment.processed_date,
            'assignment_paid': payment.assignment.is_paid if payment.assignment else None,
            'interpreter_name': (
                f"{payment.interpreter.user.first_name} {payment.interpreter.user.last_name}".strip()
                if payment.interpreter and payment.interpreter.user else ''
            ),
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
            doc_num = generate_unique_reference('PS', PayrollDocument, 'document_number')

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

    # ------------------------------------------------------------------
    # Generate stubs from selected payment IDs (grouped by interpreter)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='stubs/from-payments')
    def stubs_from_payments(self, request):
        """
        Create one PayrollDocument per interpreter from a list of payment IDs.
        Each payment's linked assignment is added as a Service line item.
        """
        payment_ids = request.data.get('payment_ids', [])
        if not payment_ids:
            return Response({'detail': 'payment_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)

        payments = (
            InterpreterPayment.objects
            .filter(id__in=payment_ids)
            .select_related(
                'interpreter__user',
                'assignment__client',
                'assignment__source_language',
                'assignment__target_language',
            )
        )

        # Group by interpreter
        by_interpreter: dict = {}
        for p in payments:
            key = p.interpreter_id
            if key not in by_interpreter:
                by_interpreter[key] = {'interpreter': p.interpreter, 'payments': []}
            by_interpreter[key]['payments'].append(p)

        created = []
        for interp_id, info in by_interpreter.items():
            interp = info['interpreter']
            doc_num = generate_unique_reference('PS', PayrollDocument, 'document_number')
            stub = PayrollDocument.objects.create(
                interpreter_name=f"{interp.user.first_name} {interp.user.last_name}".strip(),
                interpreter_email=interp.user.email,
                interpreter_phone=getattr(interp.user, 'phone', '') or '',
                interpreter_address=f"{interp.address}, {interp.city}, {interp.state} {interp.zip_code}".strip(', '),
                document_number=doc_num,
                document_date=timezone.now().date(),
                company_address=COMPANY_ADDRESS,
                company_email=COMPANY_EMAIL,
                company_phone=COMPANY_PHONE,
            )

            for p in info['payments']:
                a = p.assignment
                if a:
                    duration_h = Decimal('0')
                    if a.end_time and a.start_time:
                        duration_h = round(Decimal(str((a.end_time - a.start_time).total_seconds() / 3600)), 2)
                    Service.objects.create(
                        payroll=stub,
                        date=a.start_time.date(),
                        client=a.client.company_name if a.client else (a.client_name or ''),
                        source_language=a.source_language.name if a.source_language else '',
                        target_language=a.target_language.name if a.target_language else '',
                        duration=duration_h,
                        rate=a.interpreter_rate or Decimal('0'),
                    )
                else:
                    # Payment without assignment — use amount as flat fee
                    Service.objects.create(
                        payroll=stub,
                        date=p.scheduled_date.date() if p.scheduled_date else timezone.now().date(),
                        client=f"Ref: {p.reference_number}",
                        source_language='', target_language='',
                        duration=Decimal('1'),
                        rate=p.amount,
                    )

            created.append({
                'id': stub.id,
                'document_number': stub.document_number,
                'interpreter_name': stub.interpreter_name,
            })

        return Response(created, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Manual stub for non-registered payees
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='stubs/manual')
    def manual_stub(self, request):
        """
        Create a pay stub for any payee (not necessarily a registered user).
        Accepts: payee info + services + optional reimbursements/deductions.
        Optional: send_now=true to email the stub immediately.
        """
        payee_name    = (request.data.get('payee_name') or '').strip()
        payee_email   = (request.data.get('payee_email') or '').strip()
        payee_phone   = (request.data.get('payee_phone') or '').strip()
        payee_address = (request.data.get('payee_address') or '').strip()
        services_data      = request.data.get('services', [])
        reimbursements_data = request.data.get('reimbursements', [])
        deductions_data    = request.data.get('deductions', [])
        send_now = request.data.get('send_now', False)

        if not payee_name:
            return Response({'detail': 'payee_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        doc_num = generate_unique_reference('PS', PayrollDocument, 'document_number')
        stub = PayrollDocument.objects.create(
            interpreter_name=payee_name,
            interpreter_email=payee_email,
            interpreter_phone=payee_phone,
            interpreter_address=payee_address,
            document_number=doc_num,
            document_date=timezone.now().date(),
            company_address=COMPANY_ADDRESS,
            company_email=COMPANY_EMAIL,
            company_phone=COMPANY_PHONE,
        )

        for svc in services_data:
            try:
                Service.objects.create(
                    payroll=stub,
                    date=svc.get('date') or timezone.now().date(),
                    client=svc.get('client', ''),
                    source_language=svc.get('source_language', ''),
                    target_language=svc.get('target_language', ''),
                    duration=Decimal(str(svc.get('duration') or 0)),
                    rate=Decimal(str(svc.get('rate') or 0)),
                )
            except Exception:
                pass

        for r in reimbursements_data:
            try:
                Reimbursement.objects.create(
                    payroll=stub,
                    date=r.get('date') or timezone.now().date(),
                    description=r.get('description', ''),
                    reimbursement_type=r.get('reimbursement_type', 'OTHER'),
                    amount=Decimal(str(r.get('amount') or 0)),
                )
            except Exception:
                pass

        for d in deductions_data:
            try:
                Deduction.objects.create(
                    payroll=stub,
                    date=d.get('date') or timezone.now().date(),
                    description=d.get('description', ''),
                    deduction_type=d.get('deduction_type', 'OTHER'),
                    amount=Decimal(str(d.get('amount') or 0)),
                )
            except Exception:
                pass

        if send_now and payee_email:
            try:
                from app.services.email_service import PayrollEmailService
                pdf_buf = generate_payroll_pdf(stub)
                PayrollEmailService.send_stub(stub, pdf_buf.getvalue())
            except Exception as e:
                logger.warning(f"manual_stub: email send failed: {e}")

        return Response(
            PayrollDocumentDetailSerializer(stub).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Earnings Summary (for tax purposes)
    # ------------------------------------------------------------------
    def _build_earnings_data(self, request):
        """Shared helper: parse params, query assignments, return summary dict."""
        interpreter_id = request.query_params.get('interpreter_id') or request.data.get('interpreter_id')
        year = request.query_params.get('year') or request.data.get('year')
        period_start_str = request.query_params.get('period_start') or request.data.get('period_start')
        period_end_str = request.query_params.get('period_end') or request.data.get('period_end')

        if not interpreter_id:
            return None, Response({'detail': 'interpreter_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            interpreter = Interpreter.objects.select_related('user').get(pk=interpreter_id)
        except Interpreter.DoesNotExist:
            return None, Response({'detail': 'Interpreter not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = Assignment.objects.filter(
            interpreter=interpreter,
            status='COMPLETED',
        ).select_related('client', 'source_language', 'target_language').order_by('start_time')

        if year:
            qs = qs.filter(start_time__year=int(year))
            period_label = f"Year {year}"
        elif period_start_str or period_end_str:
            if period_start_str:
                qs = qs.filter(start_time__date__gte=period_start_str)
            if period_end_str:
                qs = qs.filter(start_time__date__lte=period_end_str)
            period_label = f"{period_start_str or '—'} to {period_end_str or '—'}"
        else:
            current_year = timezone.now().year
            qs = qs.filter(start_time__year=current_year)
            period_label = f"Year {current_year}"

        assignments_data = []
        total = Decimal('0')
        for a in qs:
            duration_hours = Decimal('0')
            if a.end_time and a.start_time:
                duration_hours = round(Decimal(str((a.end_time - a.start_time).total_seconds() / 3600)), 2)
            rate = a.interpreter_rate or Decimal('0')
            amount = duration_hours * rate
            total += amount
            assignments_data.append({
                'id': a.id,
                'date': str(a.start_time.date()),
                'client': a.client.company_name if a.client else (a.client_name or ''),
                'source_language': a.source_language.name if a.source_language else '',
                'target_language': a.target_language.name if a.target_language else '',
                'duration': str(duration_hours),
                'rate': str(rate),
                'amount': str(amount),
            })

        data = {
            'interpreter_id': interpreter.id,
            'interpreter_name': f"{interpreter.user.first_name} {interpreter.user.last_name}".strip(),
            'interpreter_email': interpreter.user.email,
            'period_label': period_label,
            'assignments': assignments_data,
            'total_assignments': len(assignments_data),
            'total_earnings': str(total),
        }
        return data, None

    @action(detail=False, methods=['get'], url_path='earnings-summary')
    def earnings_summary(self, request):
        """Return earnings summary JSON for an interpreter (for tax purposes)."""
        data, err = self._build_earnings_data(request)
        if err:
            return err
        return Response(data)

    @action(detail=False, methods=['get'], url_path='earnings-summary-pdf')
    def earnings_summary_pdf(self, request):
        """Download earnings summary as a PDF."""
        data, err = self._build_earnings_data(request)
        if err:
            return err
        try:
            pdf_buffer = generate_earnings_summary_pdf(data)
            safe_name = data['interpreter_name'].replace(' ', '_')
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="earnings-summary-{safe_name}-{data["period_label"]}.pdf"'
            )
            return response
        except Exception as e:
            logger.error(f"Failed to generate earnings summary PDF: {e}")
            return Response({'detail': 'Failed to generate PDF.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='earnings-summary-send')
    def earnings_summary_send(self, request):
        """Email the earnings summary PDF to the interpreter."""
        data, err = self._build_earnings_data(request)
        if err:
            return err
        if not data['interpreter_email']:
            return Response({'detail': 'No email address for this interpreter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pdf_buffer = generate_earnings_summary_pdf(data)
            safe_name = data['interpreter_name'].replace(' ', '_')
            filename = f"earnings-summary-{safe_name}-{data['period_label']}.pdf"
            email = EmailMessage(
                subject=f"Earnings Summary {data['period_label']} — JHBridge Translation",
                body=(
                    f"Dear {data['interpreter_name']},\n\n"
                    f"Please find attached your earnings summary for {data['period_label']}.\n"
                    f"Total earnings: ${data['total_earnings']}\n\n"
                    f"This document is for your records and tax purposes.\n\n"
                    f"JHBridge Translation\npayroll@jhbridgetranslation.com"
                ),
                from_email='payroll@jhbridgetranslation.com',
                to=[data['interpreter_email']],
            )
            email.attach(filename, pdf_buffer.getvalue(), 'application/pdf')
            email.send(fail_silently=False)
            return Response({'detail': f"Earnings summary sent to {data['interpreter_email']}."})
        except Exception as e:
            logger.error(f"Failed to send earnings summary: {e}")
            return Response({'detail': 'Failed to send email.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
