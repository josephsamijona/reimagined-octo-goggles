"""
Admin invoice maker: select client, pick assignments, add line items, generate PDF or email.
"""
import io
import json
import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable

from app.api.services.payroll_service import _build_header, _build_footer, NAVY, GOLD, LIGHT, WHITE, GREY
from app.api.services.reference_service import generate_unique_reference
from app.models.finance import Invoice
from app.models.services import Assignment
from app.models.users import Client

logger = logging.getLogger(__name__)
staff_required = [login_required, staff_member_required]


def generate_invoice_pdf(invoice_data):
    """Generate a modern corporate invoice PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    _build_header(elements, styles,
        doc_title=f"INVOICE  #{invoice_data['invoice_number']}",
        subtitle_lines=[
            f"Date: <b>{invoice_data['issued_date']}</b>  ·  Due: <b>{invoice_data['due_date']}</b>",
            f"Status: <b>{invoice_data.get('status', 'DRAFT')}</b>",
        ],
    )

    # Bill To section
    bill_to_style = ParagraphStyle('BillTo', parent=styles['Normal'], fontSize=9, leading=13)
    bill_to_header = ParagraphStyle('BillToH', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', textColor=NAVY)
    elements.append(Paragraph("BILL TO", bill_to_header))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f"<b>{invoice_data['client_name']}</b><br/>"
        f"{invoice_data.get('client_address', '')}<br/>"
        f"{invoice_data.get('client_email', '')}  ·  {invoice_data.get('client_phone', '')}",
        bill_to_style,
    ))
    if invoice_data.get('client_tax_id'):
        elements.append(Paragraph(f"Tax ID: {invoice_data['client_tax_id']}", bill_to_style))
    elements.append(Spacer(1, 16))

    # Line items table
    items = invoice_data.get('items', [])
    if items:
        table_data = [['#', 'Description', 'Date', 'Qty/Hrs', 'Rate', 'Amount']]
        for i, item in enumerate(items, 1):
            table_data.append([
                str(i),
                item.get('description', ''),
                item.get('date', ''),
                item.get('quantity', ''),
                f"${Decimal(str(item.get('rate', 0))):.2f}" if item.get('rate') else '',
                f"${Decimal(str(item.get('amount', 0))):.2f}",
            ])

        tbl = Table(table_data, colWidths=[0.35*inch, 2.8*inch, 0.85*inch, 0.65*inch, 0.75*inch, 0.95*inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR',     (0, 0), (-1, 0), WHITE),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1), 9),
            ('ALIGN',         (3, 0), (-1, -1), 'RIGHT'),
            ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT]),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(tbl)

    # Totals
    elements.append(Spacer(1, 16))
    subtotal = Decimal(str(invoice_data.get('subtotal', 0)))
    tax = Decimal(str(invoice_data.get('tax_amount', 0)))
    total = Decimal(str(invoice_data.get('total', 0)))

    totals_data = [
        ['', 'Subtotal:', f"${subtotal:.2f}"],
    ]
    if tax:
        totals_data.append(['', 'Tax:', f"${tax:.2f}"])
    totals_data.append(['', 'TOTAL DUE:', f"${total:.2f}"])

    totals_tbl = Table(totals_data, colWidths=[3.6*inch, 1.5*inch, 1.3*inch])
    totals_tbl.setStyle(TableStyle([
        ('FONTSIZE',      (0, 0), (-1, -1), 10),
        ('ALIGN',         (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, -1), (-1, -1), 13),
        ('TEXTCOLOR',     (0, -1), (-1, -1), NAVY),
        ('LINEABOVE',     (1, -1), (-1, -1), 2, NAVY),
        ('BACKGROUND',    (1, -1), (-1, -1), colors.HexColor('#dbeafe')),
    ]))
    elements.append(totals_tbl)

    # Notes
    if invoice_data.get('notes'):
        elements.append(Spacer(1, 16))
        note_style = ParagraphStyle('InvNote', parent=styles['Normal'], fontSize=9, textColor=GREY)
        elements.append(Paragraph(f"<b>Notes:</b> {invoice_data['notes']}", note_style))

    # Payment terms
    elements.append(Spacer(1, 12))
    terms_style = ParagraphStyle('Terms', parent=styles['Normal'], fontSize=8, textColor=GREY)
    elements.append(Paragraph(
        "Payment is due by the date indicated above. Please include the invoice number on your payment. "
        "For questions, contact us at contact@jhbridgetranslation.com or +1 (774) 223-8771.",
        terms_style,
    ))

    _build_footer(elements, styles)
    doc.build(elements)
    buffer.seek(0)
    return buffer


@method_decorator(staff_required, name='dispatch')
class InvoiceMakerView(View):
    """Main invoice maker page."""

    def get(self, request):
        clients = Client.objects.filter(active=True).select_related('user').order_by('company_name')
        return render(request, 'admin/invoice/maker.html', {
            'clients': clients,
            'title': 'Invoice Maker',
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid request data.'}, status=400)

        client_id = data.get('client_id')
        manual_client = data.get('manual_client')
        items = data.get('items', [])
        tax_rate = data.get('tax_rate', 0)
        notes = data.get('notes', '')
        action = data.get('action', 'download')
        due_days = data.get('due_days', 30)

        if not client_id and not manual_client:
            return JsonResponse({'error': 'Please select or enter a client.'}, status=400)
        if not items:
            return JsonResponse({'error': 'Add at least one line item.'}, status=400)

        # Resolve client info
        client = None
        if client_id:
            try:
                client = Client.objects.select_related('user').get(pk=client_id)
            except Client.DoesNotExist:
                return JsonResponse({'error': 'Client not found.'}, status=400)
        elif manual_client:
            if not manual_client.get('name', '').strip():
                return JsonResponse({'error': 'Client name is required.'}, status=400)

        # Calculate totals
        subtotal = Decimal('0')
        processed_items = []
        assignment_ids = []
        for item in items:
            try:
                amount = Decimal(str(item.get('amount', 0)))
            except (InvalidOperation, ValueError):
                amount = Decimal('0')
            subtotal += amount
            processed_items.append({
                'description': str(item.get('description', ''))[:255],
                'date': item.get('date', ''),
                'quantity': item.get('quantity', ''),
                'rate': item.get('rate', 0),
                'amount': float(amount),
            })
            if item.get('assignment_id'):
                assignment_ids.append(item['assignment_id'])

        try:
            tax_pct = Decimal(str(tax_rate))
        except (InvalidOperation, ValueError):
            tax_pct = Decimal('0')
        tax_amount = (subtotal * tax_pct / 100).quantize(Decimal('0.01'))
        total = subtotal + tax_amount

        inv_number = generate_unique_reference('INV', Invoice, 'invoice_number')
        today = date.today()
        due = today + timedelta(days=int(due_days))

        # Determine client display info
        if client:
            display_name = client.company_name
            billing_addr = ''
            if client.billing_address:
                billing_addr = f"{client.billing_address}, {client.billing_city or ''}, {client.billing_state or ''} {client.billing_zip_code or ''}"
            elif client.address:
                billing_addr = f"{client.address}, {client.city}, {client.state} {client.zip_code}"
            display_email = client.email or client.user.email
            display_phone = client.phone or ''
            display_tax_id = client.tax_id or ''
        else:
            display_name = manual_client['name']
            billing_addr = manual_client.get('address', '')
            display_email = manual_client.get('email', '')
            display_phone = manual_client.get('phone', '')
            display_tax_id = ''

        # Create Invoice record
        invoice = Invoice.objects.create(
            invoice_number=inv_number,
            client=client,
            client_name=display_name,
            client_email=display_email,
            client_address=billing_addr,
            client_phone=display_phone,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            status='DRAFT',
            issued_date=today,
            due_date=due,
            notes=notes,
            created_by=request.user,
        )
        if assignment_ids:
            invoice.assignments.set(assignment_ids)

        # Build PDF data
        pdf_data = {
            'invoice_number': inv_number,
            'issued_date': str(today),
            'due_date': str(due),
            'status': 'DRAFT',
            'client_name': display_name,
            'client_address': billing_addr,
            'client_email': display_email,
            'client_phone': display_phone,
            'client_tax_id': display_tax_id,
            'items': processed_items,
            'subtotal': float(subtotal),
            'tax_amount': float(tax_amount),
            'total': float(total),
            'notes': notes,
        }

        pdf_buffer = generate_invoice_pdf(pdf_data)
        pdf_bytes = pdf_buffer.read()

        if action == 'email':
            if not display_email:
                return JsonResponse({'error': 'No email address for this client.'}, status=400)
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=f'Invoice {inv_number} — JHBridge Translation Services',
                body=(
                    f'Dear {display_name},\n\n'
                    f'Please find attached invoice {inv_number} for ${total:.2f}.\n'
                    f'Payment is due by {due}.\n\n'
                    f'Thank you for your business.\n\n'
                    f'— JHBridge Translation Services'
                ),
                from_email='JHBridge Billing <billing@jhbridgetranslation.com>',
                to=[display_email],
            )
            email.attach(f'invoice-{inv_number}.pdf', pdf_bytes, 'application/pdf')
            try:
                email.send(fail_silently=False)
                invoice.status = 'SENT'
                invoice.save(update_fields=['status'])
                return JsonResponse({'ok': True, 'message': f'Invoice {inv_number} sent to {display_email}.'})
            except Exception as e:
                logger.exception("Failed to send invoice email")
                return JsonResponse({'error': f'Email failed: {str(e)}. Invoice was created as draft.'}, status=500)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice-{inv_number}.pdf"'
        return response


@method_decorator(staff_required, name='dispatch')
class FetchClientAssignmentsView(View):
    """AJAX: return completed assignments for a client."""

    def get(self, request):
        client_id = request.GET.get('client_id')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')

        if not client_id:
            return JsonResponse({'assignments': []})

        qs = Assignment.objects.filter(
            client_id=client_id,
            status='COMPLETED',
        ).select_related('interpreter', 'interpreter__user', 'source_language', 'target_language', 'service_type')

        if date_from:
            qs = qs.filter(start_time__date__gte=date_from)
        if date_to:
            qs = qs.filter(start_time__date__lte=date_to)

        qs = qs.order_by('-start_time')[:200]

        results = []
        for a in qs:
            duration = 0
            if a.start_time and a.end_time:
                duration = round((a.end_time - a.start_time).total_seconds() / 3600, 2)
            if a.minimum_hours and duration < a.minimum_hours:
                duration = a.minimum_hours

            interp_name = ''
            if a.interpreter and a.interpreter.user:
                interp_name = f"{a.interpreter.user.first_name} {a.interpreter.user.last_name}"

            rate = float(a.interpreter_rate) if a.interpreter_rate else 0
            amount = round(duration * rate, 2)

            results.append({
                'id': a.pk,
                'date': a.start_time.strftime('%m/%d/%Y') if a.start_time else '',
                'interpreter': interp_name,
                'service_type': a.service_type.name if a.service_type else '',
                'source_language': a.source_language.name if a.source_language else '',
                'target_language': a.target_language.name if a.target_language else '',
                'duration': duration,
                'rate': rate,
                'amount': amount,
                'location': a.location or '',
            })

        return JsonResponse({'assignments': results})
