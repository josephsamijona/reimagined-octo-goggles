"""Payroll PDF generation using ReportLab."""
import io
import logging
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)


def generate_payroll_pdf(payroll_document):
    """Generate PDF for a payroll document using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=16, spaceAfter=12)
    elements.append(Paragraph("JH BRIDGE TRANSLATION SERVICES", title_style))
    elements.append(Paragraph("500 GROSSMAN DR, BRAINTREE, MA, 02184", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Document info
    elements.append(Paragraph(f"Pay Stub #{payroll_document.document_number}", styles['Heading2']))
    elements.append(Paragraph(f"Date: {payroll_document.document_date}", styles['Normal']))
    elements.append(Paragraph(f"Interpreter: {payroll_document.interpreter_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Services table
    services = payroll_document.services.all()
    if services.exists():
        data = [['Date', 'Client', 'Languages', 'Duration', 'Rate', 'Amount']]
        total_amount = Decimal('0')
        for svc in services:
            amount = svc.amount
            total_amount += amount
            data.append([
                str(svc.date or ''),
                svc.client,
                f"{svc.source_language} \u2192 {svc.target_language}",
                f"{svc.duration}h" if svc.duration else '',
                f"${svc.rate}" if svc.rate else '',
                f"${amount:.2f}",
            ])
        data.append(['', '', '', '', 'Subtotal:', f"${total_amount:.2f}"])

        table = Table(data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(table)

    # Reimbursements
    reimbursements = payroll_document.reimbursements.all()
    if reimbursements.exists():
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("Reimbursements", styles['Heading3']))
        reimb_total = sum(r.amount for r in reimbursements)
        reimb_data = [['Description', 'Type', 'Amount']]
        for r in reimbursements:
            reimb_data.append([r.description, r.get_reimbursement_type_display(), f"${r.amount:.2f}"])
        reimb_data.append(['', 'Total:', f"${reimb_total:.2f}"])
        table = Table(reimb_data, colWidths=[3*inch, 2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)

    # Deductions
    deductions = payroll_document.deductions.all()
    if deductions.exists():
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("Deductions", styles['Heading3']))
        ded_total = sum(d.amount for d in deductions)
        ded_data = [['Description', 'Type', 'Amount']]
        for d in deductions:
            ded_data.append([d.description, d.get_deduction_type_display(), f"${d.amount:.2f}"])
        ded_data.append(['', 'Total:', f"${ded_total:.2f}"])
        table = Table(ded_data, colWidths=[3*inch, 2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
