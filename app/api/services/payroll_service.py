"""Payroll PDF generation using ReportLab."""
import io
import logging
import os
from decimal import Decimal
from pathlib import Path

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Company constants
# ---------------------------------------------------------------------------
COMPANY_NAME    = "JH Bridge Translation Services"
COMPANY_PLACE   = "Marketplace at Braintree"
COMPANY_ADDRESS = "500 Grossman Dr, Braintree, MA 02184, United States"
COMPANY_PHONE   = "+1 774-223-8771"
COMPANY_EMAIL   = "contact@jhbridgetranslation.com"
COMPANY_WEB     = "jhbridgetranslation.com"

# ---------------------------------------------------------------------------
# Logo: load from local static file
# ---------------------------------------------------------------------------
_LOGO_BUFFER = None
_LOGO_LOADED = False


def _get_logo_buffer():
    """Return a fresh BytesIO of the logo from local static files, or None."""
    global _LOGO_BUFFER, _LOGO_LOADED
    if _LOGO_LOADED:
        return io.BytesIO(_LOGO_BUFFER) if _LOGO_BUFFER is not None else None
    _LOGO_LOADED = True
    # Try local static file first, then collected staticfiles
    candidates = [
        Path(settings.BASE_DIR) / 'static' / 'images' / 'logo.png',
        Path(settings.STATIC_ROOT) / 'images' / 'logo.png' if settings.STATIC_ROOT else None,
    ]
    for path in candidates:
        if path and path.is_file():
            try:
                _LOGO_BUFFER = path.read_bytes()
                logger.info("Logo loaded from %s", path)
                return io.BytesIO(_LOGO_BUFFER)
            except Exception as exc:
                logger.warning("Could not read logo file %s: %s", path, exc)
    logger.warning("Company logo not found in static files")
    return None


NAVY   = colors.HexColor('#1a3c5e')
GOLD   = colors.HexColor('#c9a227')
LIGHT  = colors.HexColor('#f3f4f6')
WHITE  = colors.white
GREY   = colors.HexColor('#9ca3af')
GREEN  = colors.HexColor('#16a34a')
RED    = colors.HexColor('#dc2626')


def _build_header(elements, styles, doc_title, subtitle_lines=None):
    """Render a branded header block (logo + company info + doc title)."""
    # Try to load logo from module-level cache
    logo_loaded = False
    logo_buf = _get_logo_buffer()
    if logo_buf is not None:
        try:
            from reportlab.platypus import Image as RLImage
            logo = RLImage(logo_buf, width=1.4 * inch, height=0.46 * inch)
            logo_loaded = True
        except Exception:
            logo_loaded = False

    # Header table: logo left | company info right
    company_block = (
        f"<b>{COMPANY_NAME}</b><br/>"
        f"<font size='8' color='#6b7280'>{COMPANY_PLACE}</font><br/>"
        f"<font size='8' color='#6b7280'>{COMPANY_ADDRESS}</font><br/>"
        f"<font size='8' color='#6b7280'>{COMPANY_PHONE} &nbsp;·&nbsp; {COMPANY_EMAIL}</font><br/>"
        f"<font size='8' color='#6b7280'>{COMPANY_WEB}</font>"
    )
    company_para = Paragraph(company_block, ParagraphStyle(
        'CompanyBlock', parent=styles['Normal'], fontSize=10, leading=14,
    ))

    if logo_loaded:
        header_data = [[logo, company_para]]
        col_widths = [1.6 * inch, 5.3 * inch]
    else:
        header_data = [[company_para]]
        col_widths = [6.9 * inch]

    header_table = Table(header_data, colWidths=col_widths)
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width='100%', thickness=2, color=NAVY))
    elements.append(Spacer(1, 10))

    # Document title
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold',
        textColor=NAVY, spaceAfter=4,
    )
    elements.append(Paragraph(doc_title, title_style))
    if subtitle_lines:
        sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9, textColor=GREY, leading=13)
        for line in subtitle_lines:
            elements.append(Paragraph(line, sub_style))
    elements.append(Spacer(1, 12))


def _build_footer(elements, styles):
    """Render a branded footer block."""
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=GREY))
    elements.append(Spacer(1, 6))
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=7, textColor=GREY, alignment=1,
    )
    elements.append(Paragraph(
        f"{COMPANY_NAME} &nbsp;·&nbsp; {COMPANY_ADDRESS} &nbsp;·&nbsp; "
        f"{COMPANY_PHONE} &nbsp;·&nbsp; {COMPANY_EMAIL}",
        footer_style,
    ))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(
        "This document is confidential and intended solely for the named recipient.",
        footer_style,
    ))


# ---------------------------------------------------------------------------
# Earnings Summary PDF (for tax purposes)
# ---------------------------------------------------------------------------
def generate_earnings_summary_pdf(data):
    """
    Generate an earnings summary PDF for tax purposes.

    data dict keys:
        interpreter_name, interpreter_email, period_label,
        assignments: [{ date, client, source_language, target_language, duration, rate, amount }],
        total_earnings
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    _build_header(elements, styles,
        doc_title="EARNINGS SUMMARY — FOR TAX PURPOSES",
        subtitle_lines=[
            f"Period: <b>{data['period_label']}</b>",
            f"Interpreter: <b>{data['interpreter_name']}</b>  ·  {data['interpreter_email']}",
        ],
    )

    assignments = data.get('assignments', [])
    if assignments:
        table_data = [['Date', 'Client', 'Location', 'Languages', 'Hrs', 'Rate/hr', 'Amount']]
        for a in assignments:
            table_data.append([
                a.get('date', ''),
                a.get('client', ''),
                a.get('location', ''),
                f"{a.get('source_language', '')} → {a.get('target_language', '')}",
                f"{float(a.get('duration', 0)):.1f}",
                f"${a.get('rate', '')}",
                f"${Decimal(a.get('amount', '0')):.2f}",
            ])
        total = Decimal(data.get('total_earnings', '0'))
        table_data.append(['', '', '', '', '', 'TOTAL', f"${total:.2f}"])

        tbl = Table(
            table_data,
            colWidths=[0.85*inch, 1.25*inch, 0.9*inch, 1.5*inch, 0.45*inch, 0.7*inch, 0.85*inch],
        )
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),   NAVY),
            ('TEXTCOLOR',     (0, 0), (-1, 0),   WHITE),
            ('FONTNAME',      (0, 0), (-1, 0),   'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1),  8),
            ('ALIGN',         (4, 0), (-1, -1),  'RIGHT'),
            ('GRID',          (0, 0), (-1, -1),  0.4, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, LIGHT]),
            ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
            ('TOPPADDING',    (0, 0), (-1, -1),  4),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  4),
        ]))
        elements.append(tbl)
        elements.append(Spacer(1, 16))

        # Grand total box
        total_style = ParagraphStyle(
            'GrandTotal', parent=styles['Normal'], fontSize=13,
            fontName='Helvetica-Bold', textColor=NAVY,
        )
        elements.append(Paragraph(f"Total Earnings: ${total:.2f}", total_style))
        elements.append(Spacer(1, 6))
        note_style = ParagraphStyle('Note', parent=styles['Normal'], fontSize=8, textColor=GREY)
        elements.append(Paragraph(
            "JHBridge interpreters are independent contractors. This document is provided for "
            "your records and tax reporting purposes (1099-NEC).",
            note_style,
        ))
    else:
        elements.append(Paragraph(
            "No completed assignments found for this period.", styles['Normal'],
        ))

    _build_footer(elements, styles)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Pay Stub PDF
# ---------------------------------------------------------------------------
def generate_payroll_pdf(payroll_document):
    """Generate PDF for a payroll document using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    elements = []

    _build_header(elements, styles,
        doc_title=f"PAY STUB  #{payroll_document.document_number}",
        subtitle_lines=[
            f"Date: <b>{payroll_document.document_date}</b>",
            f"Interpreter: <b>{payroll_document.interpreter_name}</b>  ·  {payroll_document.interpreter_email or ''}",
            f"Phone: {payroll_document.interpreter_phone or '—'}  ·  {payroll_document.interpreter_address or '—'}",
        ],
    )

    # ---- Services ----
    services = payroll_document.services.all()
    if services.exists():
        data = [['Date', 'Client', 'Languages', 'Duration', 'Rate/hr', 'Amount']]
        total_amount = Decimal('0')
        for svc in services:
            amount = svc.amount
            total_amount += amount
            data.append([
                str(svc.date or ''),
                svc.client,
                f"{svc.source_language} → {svc.target_language}",
                f"{svc.duration}h" if svc.duration else '',
                f"${svc.rate}/hr" if svc.rate else '',
                f"${amount:.2f}",
            ])
        data.append(['', '', '', '', 'Services Total:', f"${total_amount:.2f}"])

        tbl = Table(data, colWidths=[0.85*inch, 1.4*inch, 1.6*inch, 0.75*inch, 0.85*inch, 0.95*inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),   NAVY),
            ('TEXTCOLOR',     (0, 0), (-1, 0),   WHITE),
            ('FONTNAME',      (0, 0), (-1, 0),   'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1),  8),
            ('ALIGN',         (3, 0), (-1, -1),  'RIGHT'),
            ('GRID',          (0, 0), (-1, -1),  0.4, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, LIGHT]),
            ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND',    (0, -1), (-1, -1), LIGHT),
            ('TOPPADDING',    (0, 0), (-1, -1),  4),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  4),
        ]))
        elements.append(tbl)

    # ---- Reimbursements ----
    reimbursements = payroll_document.reimbursements.all()
    if reimbursements.exists():
        elements.append(Spacer(1, 12))
        section_style = ParagraphStyle(
            'Section', parent=styles['Normal'], fontSize=10,
            fontName='Helvetica-Bold', textColor=GREEN,
        )
        elements.append(Paragraph("Reimbursements", section_style))
        elements.append(Spacer(1, 4))
        reimb_total = sum(r.amount for r in reimbursements)
        reimb_data = [['Description', 'Type', 'Amount']]
        for r in reimbursements:
            reimb_data.append([r.description, r.get_reimbursement_type_display(), f"+${r.amount:.2f}"])
        reimb_data.append(['', 'Reimbursements Total:', f"+${reimb_total:.2f}"])
        tbl = Table(reimb_data, colWidths=[3.2*inch, 2.2*inch, 1*inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),   colors.HexColor('#16a34a')),
            ('TEXTCOLOR',     (0, 0), (-1, 0),   WHITE),
            ('FONTNAME',      (0, 0), (-1, 0),   'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1),  8),
            ('ALIGN',         (-1, 0), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR',     (-1, 1), (-1, -1), GREEN),
            ('GRID',          (0, 0), (-1, -1),  0.4, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, colors.HexColor('#f0fdf4')]),
            ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING',    (0, 0), (-1, -1),  4),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  4),
        ]))
        elements.append(tbl)

    # ---- Deductions ----
    deductions = payroll_document.deductions.all()
    if deductions.exists():
        elements.append(Spacer(1, 12))
        section_style = ParagraphStyle(
            'SectionRed', parent=styles['Normal'], fontSize=10,
            fontName='Helvetica-Bold', textColor=RED,
        )
        elements.append(Paragraph("Deductions", section_style))
        elements.append(Spacer(1, 4))
        ded_total = sum(d.amount for d in deductions)
        ded_data = [['Description', 'Type', 'Amount']]
        for d in deductions:
            ded_data.append([d.description, d.get_deduction_type_display(), f"-${d.amount:.2f}"])
        ded_data.append(['', 'Deductions Total:', f"-${ded_total:.2f}"])
        tbl = Table(ded_data, colWidths=[3.2*inch, 2.2*inch, 1*inch])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),   colors.HexColor('#dc2626')),
            ('TEXTCOLOR',     (0, 0), (-1, 0),   WHITE),
            ('FONTNAME',      (0, 0), (-1, 0),   'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1),  8),
            ('ALIGN',         (-1, 0), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR',     (-1, 1), (-1, -1), RED),
            ('GRID',          (0, 0), (-1, -1),  0.4, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, colors.HexColor('#fef2f2')]),
            ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING',    (0, 0), (-1, -1),  4),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  4),
        ]))
        elements.append(tbl)

    # ---- Net Pay Summary ----
    elements.append(Spacer(1, 16))

    svc_total = sum(s.amount for s in services) if services.exists() else Decimal('0')
    reimb_total = sum(r.amount for r in reimbursements) if reimbursements.exists() else Decimal('0')
    ded_total_val = sum(d.amount for d in deductions) if deductions.exists() else Decimal('0')
    net_pay = svc_total + reimb_total - ded_total_val

    summary_data = [
        ['Gross Earnings (Services)', f"${svc_total:.2f}"],
    ]
    if reimb_total:
        summary_data.append(['+ Reimbursements', f"+${reimb_total:.2f}"])
    if ded_total_val:
        summary_data.append(['- Deductions & Taxes', f"-${ded_total_val:.2f}"])
    summary_data.append(['NET PAY', f"${net_pay:.2f}"])

    summary_tbl = Table(summary_data, colWidths=[4.8 * inch, 1.6 * inch])
    summary_tbl.setStyle(TableStyle([
        ('FONTSIZE',      (0, 0), (-1, -1), 10),
        ('ALIGN',         (-1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR',     (0, -1), (-1, -1), NAVY),
        ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, -1), (-1, -1), 14),
        ('LINEABOVE',     (0, -1), (-1, -1), 2, NAVY),
        ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
    ]))
    elements.append(summary_tbl)

    _build_footer(elements, styles)
    doc.build(elements)
    buffer.seek(0)
    return buffer
