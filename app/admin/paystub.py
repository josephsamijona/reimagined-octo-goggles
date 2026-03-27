"""
Admin paystub generator: select interpreter, pick assignments, add extras, generate PDF or email.
"""
import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from app.api.services.payroll_service import generate_payroll_pdf, COMPANY_ADDRESS, COMPANY_PHONE, COMPANY_EMAIL
from app.api.services.reference_service import generate_unique_reference
from app.models.finance import PayrollDocument, Service, Reimbursement, Deduction
from app.models.services import Assignment
from app.models.users import Interpreter

logger = logging.getLogger(__name__)

staff_required = [login_required, staff_member_required]


@method_decorator(staff_required, name='dispatch')
class PaystubGeneratorView(View):
    """Main paystub generator page."""

    def get(self, request):
        interpreters = (
            Interpreter.objects.filter(active=True)
            .select_related('user')
            .order_by('user__last_name', 'user__first_name')
        )
        return render(request, 'admin/paystub/generator.html', {
            'interpreters': interpreters,
            'title': 'Paystub Generator',
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid request data.'}, status=400)

        interpreter_id = data.get('interpreter_id')
        assignment_ids = data.get('assignment_ids', [])
        extras = data.get('extras', [])
        deductions_data = data.get('deductions', [])
        taxes_data = data.get('taxes', [])
        action = data.get('action', 'download')
        pay_period = data.get('pay_period', '')

        if not interpreter_id:
            return JsonResponse({'error': 'Please select an interpreter.'}, status=400)
        if not assignment_ids and not extras:
            return JsonResponse({'error': 'Select at least one assignment or add an earning.'}, status=400)

        try:
            interpreter = Interpreter.objects.select_related('user').get(pk=interpreter_id)
        except Interpreter.DoesNotExist:
            return JsonResponse({'error': 'Interpreter not found.'}, status=400)

        # Fetch selected assignments
        assignments = list(
            Assignment.objects.filter(pk__in=assignment_ids, interpreter=interpreter)
            .select_related('client', 'source_language', 'target_language', 'service_type')
        )

        # Create PayrollDocument
        doc_number = generate_unique_reference('PS', PayrollDocument, 'document_number')
        user = interpreter.user
        stub = PayrollDocument.objects.create(
            company_address=COMPANY_ADDRESS,
            company_phone=COMPANY_PHONE,
            company_email=COMPANY_EMAIL,
            interpreter_name=f"{user.first_name} {user.last_name}",
            interpreter_address=f"{interpreter.address or ''}, {interpreter.city or ''}, {interpreter.state or ''} {interpreter.zip_code or ''}".strip(', '),
            interpreter_phone=getattr(user, 'phone', '') or '',
            interpreter_email=user.email,
            document_number=doc_number,
            document_date=date.today(),
        )

        # Create Service records from assignments
        for assgn in assignments:
            duration_hours = Decimal('0')
            if assgn.start_time and assgn.end_time:
                delta = assgn.end_time - assgn.start_time
                duration_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))
            if assgn.minimum_hours and duration_hours < assgn.minimum_hours:
                duration_hours = Decimal(str(assgn.minimum_hours))

            client_name = ''
            if assgn.client:
                client_name = assgn.client.company_name or ''
            elif assgn.client_name:
                client_name = assgn.client_name

            Service.objects.create(
                payroll=stub,
                date=assgn.start_time.date() if assgn.start_time else None,
                client=client_name,
                source_language=assgn.source_language.name if assgn.source_language else '',
                target_language=assgn.target_language.name if assgn.target_language else '',
                duration=duration_hours,
                rate=assgn.interpreter_rate or Decimal('0'),
            )

        # Create Reimbursement records from extras (additional earnings)
        for extra in extras:
            desc = str(extra.get('description', '')).strip()[:255]
            try:
                amount = Decimal(str(extra.get('amount', '0')))
            except (InvalidOperation, ValueError):
                continue
            if desc and amount > 0:
                Reimbursement.objects.create(
                    payroll=stub,
                    date=date.today(),
                    description=desc,
                    reimbursement_type='OTHER',
                    amount=amount,
                )

        # Create Deduction records
        for ded in deductions_data:
            desc = str(ded.get('description', '')).strip()[:255]
            ded_type = str(ded.get('type', 'OTHER'))[:50]
            try:
                amount = Decimal(str(ded.get('amount', '0')))
            except (InvalidOperation, ValueError):
                continue
            if desc and amount > 0:
                Deduction.objects.create(
                    payroll=stub,
                    date=date.today(),
                    description=desc,
                    deduction_type=ded_type,
                    amount=amount,
                )

        # Create Deduction records for taxes
        for tax in taxes_data:
            desc = str(tax.get('description', '')).strip()[:255]
            try:
                amount = Decimal(str(tax.get('amount', '0')))
            except (InvalidOperation, ValueError):
                continue
            if desc and amount > 0:
                Deduction.objects.create(
                    payroll=stub,
                    date=date.today(),
                    description=desc,
                    deduction_type='TAX',
                    amount=amount,
                )

        # Generate PDF
        pdf_buffer = generate_payroll_pdf(stub)
        pdf_bytes = pdf_buffer.read()

        if action == 'email':
            from app.services.email_service import PayrollEmailService
            # Monkey-patch total_amount for the email template
            services_total = sum(s.amount for s in stub.services.all())
            reimb_total = sum(r.amount for r in stub.reimbursements.all())
            ded_total = sum(d.amount for d in stub.deductions.all())
            stub.total_amount = services_total + reimb_total - ded_total

            success = PayrollEmailService.send_stub(stub, pdf_bytes)
            if success:
                return JsonResponse({'ok': True, 'message': f'Paystub {doc_number} emailed to {user.email}.'})
            else:
                return JsonResponse({'error': 'Failed to send email. PDF was still generated.'}, status=500)

        # Default: download
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="paystub-{doc_number}.pdf"'
        return response


@method_decorator(staff_required, name='dispatch')
class FetchAssignmentsView(View):
    """AJAX endpoint: return completed assignments for an interpreter."""

    def get(self, request):
        interpreter_id = request.GET.get('interpreter_id')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if not interpreter_id:
            return JsonResponse({'assignments': []})

        qs = Assignment.objects.filter(
            interpreter_id=interpreter_id,
            status='COMPLETED',
        ).select_related('client', 'source_language', 'target_language', 'service_type')

        if date_from:
            qs = qs.filter(start_time__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_time__date__lte=date_to)

        qs = qs.order_by('-start_time')[:200]

        results = []
        for a in qs:
            duration_hours = 0
            if a.start_time and a.end_time:
                delta = a.end_time - a.start_time
                duration_hours = round(delta.total_seconds() / 3600, 2)
            if a.minimum_hours and duration_hours < a.minimum_hours:
                duration_hours = a.minimum_hours

            client_name = ''
            if a.client:
                client_name = a.client.company_name or ''
            elif a.client_name:
                client_name = a.client_name

            rate = float(a.interpreter_rate) if a.interpreter_rate else 0
            amount = round(duration_hours * rate, 2)
            if a.total_interpreter_payment:
                amount = float(a.total_interpreter_payment)

            results.append({
                'id': a.pk,
                'date': a.start_time.strftime('%m/%d/%Y') if a.start_time else '',
                'start_time': a.start_time.strftime('%I:%M %p') if a.start_time else '',
                'end_time': a.end_time.strftime('%I:%M %p') if a.end_time else '',
                'client': client_name,
                'service_type': a.service_type.name if a.service_type else '',
                'source_language': a.source_language.name if a.source_language else '',
                'target_language': a.target_language.name if a.target_language else '',
                'duration': duration_hours,
                'rate': rate,
                'amount': amount,
                'is_paid': a.is_paid or False,
                'location': a.location or '',
            })

        return JsonResponse({'assignments': results})


# ─── BATCH PAYSTUB GENERATION ─────────────────────────────────────

@method_decorator(staff_required, name='dispatch')
class BatchPaystubView(View):
    """Batch paystub generation for multiple interpreters."""

    def get(self, request):
        interpreters = (
            Interpreter.objects.filter(active=True)
            .select_related('user')
            .order_by('user__last_name', 'user__first_name')
        )
        return render(request, 'admin/paystub/batch.html', {
            'interpreters': interpreters,
            'title': 'Batch Paystub Generator',
        })

    def post(self, request):
        import zipfile
        import io as _io

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid data.'}, status=400)

        interpreter_ids = data.get('interpreter_ids', [])
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        if not interpreter_ids:
            return JsonResponse({'error': 'Select at least one interpreter.'}, status=400)

        interpreters = Interpreter.objects.filter(pk__in=interpreter_ids).select_related('user')
        zip_buffer = _io.BytesIO()
        generated = 0

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for interpreter in interpreters:
                qs = Assignment.objects.filter(
                    interpreter=interpreter, status='COMPLETED'
                ).select_related('client', 'source_language', 'target_language', 'service_type')

                if date_from:
                    qs = qs.filter(start_time__date__gte=date_from)
                if date_to:
                    qs = qs.filter(start_time__date__lte=date_to)

                assignments = list(qs.order_by('start_time'))
                if not assignments:
                    continue

                # Create PayrollDocument
                from app.api.services.payroll_service import generate_payroll_pdf, COMPANY_ADDRESS, COMPANY_PHONE, COMPANY_EMAIL
                doc_number = generate_unique_reference('PS', PayrollDocument, 'document_number')
                user = interpreter.user
                stub = PayrollDocument.objects.create(
                    company_address=COMPANY_ADDRESS,
                    company_phone=COMPANY_PHONE,
                    company_email=COMPANY_EMAIL,
                    interpreter_name=f"{user.first_name} {user.last_name}",
                    interpreter_address=f"{interpreter.address or ''}, {interpreter.city or ''}, {interpreter.state or ''} {interpreter.zip_code or ''}".strip(', '),
                    interpreter_phone=getattr(user, 'phone', '') or '',
                    interpreter_email=user.email,
                    document_number=doc_number,
                    document_date=date.today(),
                )

                for assgn in assignments:
                    duration_hours = Decimal('0')
                    if assgn.start_time and assgn.end_time:
                        delta = assgn.end_time - assgn.start_time
                        duration_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))
                    if assgn.minimum_hours and duration_hours < assgn.minimum_hours:
                        duration_hours = Decimal(str(assgn.minimum_hours))

                    client_name = ''
                    if assgn.client:
                        client_name = assgn.client.company_name or ''
                    elif assgn.client_name:
                        client_name = assgn.client_name

                    Service.objects.create(
                        payroll=stub,
                        date=assgn.start_time.date() if assgn.start_time else None,
                        client=client_name,
                        source_language=assgn.source_language.name if assgn.source_language else '',
                        target_language=assgn.target_language.name if assgn.target_language else '',
                        duration=duration_hours,
                        rate=assgn.interpreter_rate or Decimal('0'),
                    )

                pdf_buffer = generate_payroll_pdf(stub)
                safe_name = f"{user.last_name}_{user.first_name}".replace(' ', '_')
                zf.writestr(f"paystub-{safe_name}-{doc_number}.pdf", pdf_buffer.read())
                generated += 1

        if generated == 0:
            return JsonResponse({'error': 'No completed assignments found for the selected interpreters.'}, status=400)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="paystubs-batch-{date.today()}.zip"'
        return response


# ─── TOTAL EARNINGS REPORT (TAX / 1099-NEC) ──────────────────────

@method_decorator(staff_required, name='dispatch')
class EarningsReportView(View):
    """Generate total earnings report for an interpreter for tax purposes."""

    def get(self, request):
        interpreters = (
            Interpreter.objects.filter(active=True)
            .select_related('user')
            .order_by('user__last_name', 'user__first_name')
        )
        current_year = timezone.now().year
        years = list(range(current_year, current_year - 5, -1))
        return render(request, 'admin/paystub/earnings_report.html', {
            'interpreters': interpreters,
            'years': years,
            'title': 'Earnings Report (Tax)',
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid data.'}, status=400)

        interpreter_id = data.get('interpreter_id')
        year = data.get('year')

        if not interpreter_id or not year:
            return JsonResponse({'error': 'Select an interpreter and year.'}, status=400)

        try:
            interpreter = Interpreter.objects.select_related('user').get(pk=interpreter_id)
        except Interpreter.DoesNotExist:
            return JsonResponse({'error': 'Interpreter not found.'}, status=400)

        assignments = list(
            Assignment.objects.filter(
                interpreter=interpreter,
                status='COMPLETED',
                start_time__year=int(year),
            ).select_related('client', 'source_language', 'target_language')
            .order_by('start_time')
        )

        # Build assignment data for PDF
        assignment_data = []
        total_earnings = Decimal('0')
        for a in assignments:
            duration = Decimal('0')
            if a.start_time and a.end_time:
                duration = Decimal(str(round((a.end_time - a.start_time).total_seconds() / 3600, 2)))
            if a.minimum_hours and duration < a.minimum_hours:
                duration = Decimal(str(a.minimum_hours))

            rate = a.interpreter_rate or Decimal('0')
            amount = duration * rate
            if a.total_interpreter_payment:
                amount = a.total_interpreter_payment
            total_earnings += amount

            client_name = ''
            if a.client:
                client_name = a.client.company_name or ''
            elif a.client_name:
                client_name = a.client_name

            assignment_data.append({
                'date': a.start_time.strftime('%m/%d/%Y') if a.start_time else '',
                'client': client_name,
                'location': a.location or '',
                'source_language': a.source_language.name if a.source_language else '',
                'target_language': a.target_language.name if a.target_language else '',
                'duration': float(duration),
                'rate': float(rate),
                'amount': f"{amount:.2f}",
            })

        user = interpreter.user
        from app.api.services.payroll_service import generate_earnings_summary_pdf
        pdf_data = {
            'interpreter_name': f"{user.first_name} {user.last_name}",
            'interpreter_email': user.email,
            'period_label': f"January 1 – December 31, {year}",
            'assignments': assignment_data,
            'total_earnings': str(total_earnings),
        }

        pdf_buffer = generate_earnings_summary_pdf(pdf_data)
        pdf_bytes = pdf_buffer.read()

        action = data.get('action', 'download')
        if action == 'email':
            from django.core.mail import EmailMessage as DjangoEmail
            email = DjangoEmail(
                subject=f'Earnings Summary {year} — JHBridge Translation',
                body=(
                    f'Hello {user.first_name},\n\n'
                    f'Please find attached your earnings summary for {year} '
                    f'for tax reporting purposes (1099-NEC).\n\n'
                    f'Total Earnings: ${total_earnings:.2f}\n\n'
                    f'— JHBridge Translation Services'
                ),
                from_email='JHBridge Payroll <payroll@jhbridgetranslation.com>',
                to=[user.email],
            )
            safe_name = f"{user.last_name}_{user.first_name}".replace(' ', '_')
            email.attach(f'earnings-{safe_name}-{year}.pdf', pdf_bytes, 'application/pdf')
            try:
                email.send(fail_silently=False)
                return JsonResponse({'ok': True, 'message': f'Earnings report sent to {user.email}.'})
            except Exception as e:
                return JsonResponse({'error': f'Email failed: {str(e)}'}, status=500)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        safe_name = f"{user.last_name}_{user.first_name}".replace(' ', '_')
        response['Content-Disposition'] = f'attachment; filename="earnings-{safe_name}-{year}.pdf"'
        return response


@method_decorator(staff_required, name='dispatch')
class EarningsPreviewView(View):
    """AJAX: return earnings summary for an interpreter + year."""

    def get(self, request):
        interpreter_id = request.GET.get('interpreter_id')
        year = request.GET.get('year')

        if not interpreter_id or not year:
            return JsonResponse({'total': 0, 'count': 0})

        assignments = Assignment.objects.filter(
            interpreter_id=interpreter_id,
            status='COMPLETED',
            start_time__year=int(year),
        )

        total = Decimal('0')
        count = 0
        for a in assignments:
            duration = Decimal('0')
            if a.start_time and a.end_time:
                duration = Decimal(str(round((a.end_time - a.start_time).total_seconds() / 3600, 2)))
            if a.minimum_hours and duration < a.minimum_hours:
                duration = Decimal(str(a.minimum_hours))
            rate = a.interpreter_rate or Decimal('0')
            amount = duration * rate
            if a.total_interpreter_payment:
                amount = a.total_interpreter_payment
            total += amount
            count += 1

        return JsonResponse({'total': float(total), 'count': count})
