import os
import io
import hashlib
import uuid
import requests
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image as RLImage, PageBreak
)
from reportlab.pdfgen import canvas
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from custom_storages import ContractStorage
from app.models import ContractTrackingEvent
import logging

logger = logging.getLogger(__name__)

# ─── Brand Colors ───────────────────────────────────────────────
BRAND_NAVY     = HexColor('#1B3558')
BRAND_GOLD     = HexColor('#C49A3C')
BRAND_LIGHT_BG = HexColor('#F7F8FA')
BRAND_DARK_GRAY = HexColor('#333333')
BRAND_MED_GRAY  = HexColor('#888888')
BRAND_GREEN    = HexColor('#2E7D32')
BRAND_RED      = HexColor('#C62828')


class ContractPDFGenerator:
    """
    Generates modern, branded contract PDFs with security features.
    Uses ReportLab SimpleDocTemplate for proper multi-page support
    with consistent headers, footers, sidebar, and watermark.
    """

    CONTRACT_TEXT = """\
1. Independent Contractor Relationship

Interpreter is engaged as an independent contractor and not as an employee of the Company. Nothing in this Agreement shall be construed to create an employer-employee relationship, partnership, or joint venture. Interpreter is responsible for all federal, state, and local taxes, insurance, licenses, and expenses related to services provided.

2. Scope of Services

Interpreter agrees to provide professional interpretation and/or translation services as requested by the Company, including but not limited to on-site and remote assignments for courts, hospitals, legal offices, government agencies, and private institutions.

Interpreter shall perform all services in a professional, ethical, and timely manner and in accordance with applicable laws and professional standards.

3. Compensation

Interpreter shall be compensated according to rates agreed upon per assignment or schedule. Compensation is issued only for completed assignments and approved no-show compensation as outlined in this Agreement.

Interpreter acknowledges that payment timelines may vary depending on client payment cycles.

4. Scheduling, Cancellations, and No-Shows

Interpreters are required to arrive on-site at least fifteen (15) minutes prior to the scheduled start time of any assignment unless otherwise instructed.

If an appointment is canceled by the client or results in a no-show after the Interpreter has arrived on-site and remained on-site, the Interpreter must report the no-show to the Company or its designated dispatcher no earlier than fifteen (15) minutes after the scheduled appointment start time.

Failure to report a no-show in accordance with this policy, or failure to be physically present on-site at the scheduled appointment location, shall result in the appointment being considered canceled, and no no-show compensation shall be owed.

When properly reported and confirmed, the Interpreter shall be compensated for one (1) hour of work only, unless otherwise approved in advance by the Company or its designated dispatcher.

Payment beyond one (1) hour for a no-show or late cancellation may be authorized only at the discretion of the Company, based on factors such as distance traveled, prior notice, or specific client agreements.

Repeated no-shows or late cancellations may result in reduced assignment opportunities or removal from the Company's active interpreter roster.

5. Attendance, Punctuality, and Reliability

Interpreters are expected to maintain professional reliability, including punctual arrival and adherence to confirmed assignments.

Late cancellations, defined as cancellations made less than forty-eight (48) hours prior to the scheduled appointment without Company approval, and tardiness, defined as failure to arrive on-site at least fifteen (15) minutes before the scheduled start time, are considered performance issues.

The Company reserves the right to take progressive corrective action, including but not limited to verbal or written warnings, reduced assignment priority, temporary suspension from assignments, and removal from the Company's active interpreter roster.

The determination of corrective action shall be at the sole discretion of the Company and may be based on frequency, impact on clients, and prior performance history.

6. Confidentiality

Interpreter agrees to maintain strict confidentiality regarding all client information, case details, medical information, legal matters, and proprietary Company information in compliance with applicable privacy laws, including HIPAA where applicable.

This obligation survives termination of this Agreement.

7. Term and Termination

This Agreement shall commence on the Effective Date, defined as the date on which this Agreement is executed by both parties, and shall continue until terminated by either party upon thirty (30) days written notice.

The Company may terminate this Agreement immediately, without notice, in the event of breach of this Agreement, misconduct, violation of Company policies, repeated performance issues, or failure to meet professional standards.

8. Compliance with Laws and Standards

Interpreter agrees to comply with all applicable federal, state, and local laws, court rules, ethical guidelines, and professional interpretation standards relevant to assigned services.

9. Equipment and Expenses

Interpreter is responsible for providing their own transportation, equipment, internet access, and any tools required to perform services unless otherwise agreed in writing.

10. Assignment Acceptance

Interpreter is not guaranteed a minimum number of assignments. Acceptance of assignments is voluntary; however, repeated declines, cancellations, or unreliability may affect future assignment availability.

11. Non-Solicitation of Clients

During the term of this Agreement and for a period of twenty-four (24) months following termination, the Interpreter agrees not to directly or indirectly solicit, contract with, or provide interpretation services to any client, customer, court, hospital, agency, or institution introduced to the Interpreter through the Company, except through the Company.

This restriction applies regardless of whether the client initiates contact with the Interpreter.

Violation of this provision may result in immediate termination of this Agreement and may subject the Interpreter to legal and financial remedies available under applicable law.

12. Dispute Resolution

Any dispute arising out of or relating to this Agreement shall first be addressed through good-faith mediation. If the dispute is not resolved, it shall be submitted to binding arbitration in the Commonwealth of Massachusetts.

13. Governing Law

This Agreement shall be governed by and construed in accordance with the laws of the Commonwealth of Massachusetts.

14. Entire Agreement

This Agreement constitutes the entire agreement between the parties and supersedes all prior agreements or understandings, whether written or oral. Any modification must be in writing and signed by both parties.

15. Severability

If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.

16. Acknowledgment

By signing below, Interpreter acknowledges that they have read, understood, and agree to be bound by the terms of this Agreement."""

    def __init__(self, invitation):
        self.invitation = invitation
        self.contract_text = self.CONTRACT_TEXT
        self.logo_url = 'https://jhbridgetranslation.com/images/logo.png'  # dont touch that at all keep it as it is
        self.doc_uuid = str(uuid.uuid4())[:12].upper()
        self._logo_image = None
        self._qr_image = None
        self._load_logo()

    # ─── Helpers ────────────────────────────────────────────────

    def _load_logo(self):
        """Pre-fetch logo so we can reuse on every page."""
        try:
            resp = requests.get(self.logo_url, timeout=5)
            if resp.status_code == 200:
                self._logo_image = ImageReader(io.BytesIO(resp.content))
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")

    def _compute_hash(self):
        """SHA-256 fingerprint of document content (first 16 hex chars)."""
        content = (
            f"{self.invitation.invitation_number}|"
            f"{self.invitation.interpreter.user.get_full_name()}|"
            f"{self.contract_text}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16].upper()

    def generate_qr_code(self, request):
        """Generate QR code for contract verification."""
        from django.urls import reverse
        verification_url = request.build_absolute_uri(
            reverse('dbdint:contract_public_verify',
                    kwargs={'invitation_number': self.invitation.invitation_number})
        )
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10, border=1)
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    # ─── Page decoration callbacks ──────────────────────────────

    def _draw_common(self, c, doc):
        """Elements that repeat on EVERY page: sidebar, watermark, footer, frame."""
        c.saveState()
        w, h = letter

        # ── Left sidebar band ──
        c.setFillColor(BRAND_NAVY)
        c.rect(0, 0, 8, h, fill=1, stroke=0)
        # Thin gold accent inside sidebar
        c.setFillColor(BRAND_GOLD)
        c.rect(8, 0, 2, h, fill=1, stroke=0)

        # ── Watermark ──
        c.saveState()
        c.setFillColor(Color(0.11, 0.21, 0.34, alpha=0.035))
        c.setFont("Helvetica-Bold", 54)
        c.translate(w / 2, h / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "JHBRIDGE")
        c.restoreState()

        # ── Content frame border ──
        c.setStrokeColor(HexColor('#E0E0E0'))
        c.setLineWidth(0.5)
        c.rect(45, 55, w - 90, h - 110, fill=0, stroke=1)

        # ── Footer ──
        c.setStrokeColor(BRAND_GOLD)
        c.setLineWidth(1)
        c.line(50, 52, w - 50, 52)

        c.setFont("Helvetica", 6.5)
        c.setFillColor(BRAND_MED_GRAY)
        # Left – agreement id
        c.drawString(55, 41, f"Agreement: {self.invitation.invitation_number}")
        # Center – page
        c.drawCentredString(w / 2, 41, f"Page {doc.page}")
        # Right – date
        signed = self.invitation.signed_at
        date_str = signed.strftime('%Y-%m-%d %H:%M %Z') if signed else "PENDING"
        c.drawRightString(w - 55, 41, f"Date: {date_str}")

        # Second footer line – legal + hash
        c.setFont("Helvetica-Oblique", 5.5)
        c.drawCentredString(
            w / 2, 31,
            "This document was generated electronically by JHBridge Translation Services and is legally binding."
        )
        c.drawCentredString(
            w / 2, 23,
            f"Document ID: {self.doc_uuid}  |  SHA-256 Fingerprint: {self._compute_hash()}"
        )

        c.restoreState()

    def _on_first_page(self, c, doc):
        """First page: header with logo, status badge, metadata box + common."""
        self._draw_common(c, doc)
        c.saveState()
        w, h = letter

        # ── Logo ──
        if self._logo_image:
            c.drawImage(self._logo_image, 55, h - 72, width=140, height=36,
                        preserveAspectRatio=True, mask='auto')
        else:
            c.setFont("Helvetica-Bold", 15)
            c.setFillColor(BRAND_NAVY)
            c.drawString(55, h - 62, "JHBridge Translation")

        # ── Status badge (top-right) ──
        bx = w - 195
        by = h - 52
        if self.invitation.status == 'SIGNED':
            c.setFillColor(BRAND_GREEN)
            c.roundRect(bx, by, 140, 22, 4, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(bx + 70, by + 7, "DIGITALLY SIGNED")
        else:
            c.setFillColor(BRAND_RED)
            c.roundRect(bx, by, 140, 22, 4, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(bx + 70, by + 7, "DRAFT")

        # ── Metadata box ──
        mx = w - 195
        my = h - 100
        c.setFillColor(BRAND_NAVY)
        c.roundRect(mx, my, 140, 40, 3, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(mx + 8, my + 27, "AGREEMENT ID")
        c.setFont("Helvetica", 7.5)
        c.drawString(mx + 8, my + 16, self.invitation.invitation_number)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(mx + 8, my + 5, f"UUID: {self.doc_uuid}")

        # ── Gold line under header ──
        c.setStrokeColor(BRAND_GOLD)
        c.setLineWidth(2)
        c.line(50, h - 108, w - 50, h - 108)

        c.restoreState()

    def _on_later_pages(self, c, doc):
        """Continuation pages: lighter header + common."""
        self._draw_common(c, doc)
        c.saveState()
        w, h = letter

        # Mini header
        if self._logo_image:
            c.drawImage(self._logo_image, 55, h - 48, width=80, height=20,
                        preserveAspectRatio=True, mask='auto')
        c.setFont("Helvetica", 7)
        c.setFillColor(BRAND_MED_GRAY)
        c.drawRightString(w - 55, h - 40,
                          f"Agreement {self.invitation.invitation_number}  —  continued")

        # Gold accent
        c.setStrokeColor(BRAND_GOLD)
        c.setLineWidth(1)
        c.line(50, h - 52, w - 50, h - 52)

        c.restoreState()

    # ─── Build the flowable story ───────────────────────────────

    def _get_styles(self):
        """Return all custom ParagraphStyles."""
        base = getSampleStyleSheet()

        title = ParagraphStyle(
            'CTitle', parent=base['Title'],
            fontSize=15, leading=19, textColor=BRAND_NAVY,
            fontName='Helvetica-Bold', alignment=TA_CENTER,
            spaceAfter=6
        )
        subtitle = ParagraphStyle(
            'CSubtitle', parent=base['Normal'],
            fontSize=9, leading=12, textColor=BRAND_MED_GRAY,
            alignment=TA_CENTER, spaceAfter=14
        )
        section = ParagraphStyle(
            'CSection', parent=base['Heading2'],
            fontSize=10.5, leading=15, textColor=white,
            fontName='Helvetica-Bold', backColor=BRAND_NAVY,
            borderPadding=(5, 8, 5, 8), spaceBefore=14, spaceAfter=6,
            borderWidth=0, borderColor=BRAND_NAVY, borderRadius=3
        )
        body = ParagraphStyle(
            'CBody', parent=base['Normal'],
            fontSize=9, leading=12.5, textColor=BRAND_DARK_GRAY,
            alignment=TA_JUSTIFY, spaceAfter=5
        )
        bullet = ParagraphStyle(
            'CBullet', parent=body,
            leftIndent=18, bulletIndent=8, spaceAfter=3
        )
        sig_label = ParagraphStyle(
            'CSigLabel', parent=base['Normal'],
            fontSize=9, leading=12, fontName='Helvetica-Bold',
            textColor=BRAND_NAVY
        )
        sig_value = ParagraphStyle(
            'CSigValue', parent=base['Normal'],
            fontSize=8, leading=11, textColor=BRAND_DARK_GRAY
        )
        return {
            'title': title, 'subtitle': subtitle, 'section': section,
            'body': body, 'bullet': bullet,
            'sig_label': sig_label, 'sig_value': sig_value
        }

    def _build_story(self, request):
        """Assemble the full document content as a list of Flowables."""
        s = self._get_styles()
        story = []

        # ── Title block ──
        story.append(Spacer(1, 10))
        story.append(Paragraph("INDEPENDENT CONTRACTOR", s['title']))
        story.append(Paragraph("INTERPRETER AGREEMENT", s['title']))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="60%", thickness=1.5, color=BRAND_GOLD,
                                spaceAfter=6, hAlign='CENTER'))

        interpreter_name = self.invitation.interpreter.user.get_full_name()
        story.append(Paragraph(
            f'Between <b>JHBridge Translation Services</b> ("Company") '
            f'and <b>{interpreter_name}</b> ("Interpreter")',
            s['subtitle']
        ))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#E0E0E0'),
                                spaceAfter=12))

        # ── Contract sections ──
        for line in self.contract_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # Detect section headings: lines starting with "1. " .. "16. "
            is_heading = False
            if len(line) > 3 and line[0].isdigit():
                dot_pos = line.find('. ')
                if 0 < dot_pos <= 3:
                    num_part = line[:dot_pos]
                    title_part = line[dot_pos + 2:]
                    if num_part.isdigit() and len(title_part) < 80:
                        heading_text = f"&nbsp;&nbsp;{num_part}. {title_part}&nbsp;&nbsp;"
                        story.append(Paragraph(heading_text, s['section']))
                        is_heading = True

            if is_heading:
                continue

            # Bullet points
            if line.startswith('\u2022') or line.startswith('- '):
                clean = line.lstrip('\u2022- ').strip()
                story.append(Paragraph(f"\u2022 {clean}", s['bullet']))
                continue

            # Normal paragraph
            story.append(Paragraph(line, s['body']))

        # ── Signature section ──
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_GOLD, spaceAfter=10))
        story.append(Paragraph(
            "&nbsp;&nbsp;SIGNATURES&nbsp;&nbsp;",
            ParagraphStyle('SigTitle', parent=s['section'], fontSize=11,
                           spaceBefore=0, spaceAfter=12)
        ))

        signed_at = self.invitation.signed_at
        date_str = signed_at.strftime('%Y-%m-%d %H:%M:%S %Z') if signed_at else ''

        # Build signature table
        interp_data = [
            [Paragraph("<b>INTERPRETER</b>", s['sig_label']), ''],
            [Paragraph("____________________________", s['sig_value']), ''],
            [Paragraph(f"Name: {interpreter_name}", s['sig_value']), ''],
            [Paragraph(f"Date: {date_str}", s['sig_value']), ''],
        ]
        if self.invitation.status == 'SIGNED':
            interp_data.insert(1, [
                Paragraph(
                    '<font color="#2E7D32"><b>DIGITALLY SIGNED</b></font>',
                    s['sig_value']
                ), ''
            ])

        company_data = [
            [Paragraph("<b>JHBRIDGE TRANSLATION</b>", s['sig_label']), ''],
            [Paragraph("____________________________", s['sig_value']), ''],
            [Paragraph(
                '<font color="#2E7D32"><b>Digitally Signed</b></font>',
                s['sig_value']
            ), ''],
            [Paragraph("Name: Marc-Henry Valme", s['sig_value']), ''],
            [Paragraph("Title: Company Representative", s['sig_value']), ''],
        ]

        # Two-column table for signatures
        sig_table_data = []
        max_rows = max(len(interp_data), len(company_data))
        for i in range(max_rows):
            left = interp_data[i][0] if i < len(interp_data) else ''
            right = company_data[i][0] if i < len(company_data) else ''
            sig_table_data.append([left, right])

        sig_table = Table(sig_table_data, colWidths=[240, 240])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        story.append(KeepTogether([sig_table]))

        # ── QR Code & verification block ──
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#E0E0E0'),
                                spaceAfter=8))

        try:
            qr_buf = self.generate_qr_code(request)
            qr_img = RLImage(qr_buf, width=55, height=55)

            verify_text = Paragraph(
                '<b>Verify this document</b><br/>'
                '<font size="7" color="#888888">'
                'Scan the QR code or visit the verification URL<br/>'
                f'Agreement: {self.invitation.invitation_number}<br/>'
                f'Document ID: {self.doc_uuid}<br/>'
                f'SHA-256: {self._compute_hash()}'
                '</font>',
                s['sig_value']
            )

            qr_table = Table([[qr_img, verify_text]], colWidths=[70, 400])
            qr_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(qr_table)
        except Exception as e:
            logger.error(f"Failed to add QR code to PDF: {e}")

        return story

    # ─── Public API ─────────────────────────────────────────────

    def generate(self, request):
        """Generate the complete PDF and return a BytesIO buffer."""
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=55,
            rightMargin=50,
            topMargin=115,   # room for first-page header
            bottomMargin=65
        )

        story = self._build_story(request)

        doc.build(
            story,
            onFirstPage=self._on_first_page,
            onLaterPages=self._on_later_pages
        )

        buffer.seek(0)
        return buffer

    def upload_to_s3(self, pdf_buffer):
        """Upload generated PDF to S3 and return key."""
        try:
            storage = ContractStorage()
            date_path = timezone.now().strftime('%Y/%m')
            filename = f"contracts/{date_path}/{self.invitation.invitation_number}.pdf"
            content = ContentFile(pdf_buffer.read())
            file_key = storage.save(filename, content)
            return file_key
        except Exception as e:
            logger.error(f"Failed to upload contract {self.invitation.invitation_number} to S3: {e}")
            raise

    def generate_and_upload(self, request):
        """Convenience method: generate PDF, upload to S3, update invitation."""
        try:
            pdf_buffer = self.generate(request)
            s3_key = self.upload_to_s3(pdf_buffer)

            self.invitation.pdf_s3_key = s3_key
            self.invitation.save(update_fields=['pdf_s3_key'])

            ContractTrackingEvent.objects.create(
                invitation=self.invitation,
                event_type='PDF_GENERATED',
                metadata={'s3_key': s3_key, 'doc_uuid': self.doc_uuid}
            )

            return s3_key
        except Exception as e:
            logger.error(f"Error in generate_and_upload: {e}")
            return None
