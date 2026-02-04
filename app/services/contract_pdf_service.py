import os
import io
import time
import requests
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from custom_storages import ContractStorage
from app.models import ContractTrackingEvent
import logging

logger = logging.getLogger(__name__)

class ContractPDFGenerator:
    """
    Generates modern, branded contract PDFs with security features.
    """
    
    def __init__(self, invitation):
        self.invitation = invitation
        self.contract_text = self.load_contract_text()
        self.logo_url = 'https://jhbridgetranslation.com/images/logo.png'#dont touch that at all keep it as it is 
        
    def load_contract_text(self):
        """Load contract text from conract.md"""
        try:
            # Adjust path relative to project root
            file_path = os.path.join(settings.BASE_DIR, 'app', 'mixins', 'conract.md')
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading contract text: {e}")
            return "Contract text could not be loaded."
            
    def generate_qr_code(self, request):
        """Generate QR code for contract verification"""
        from django.urls import reverse
        verification_url = request.build_absolute_uri(
            reverse('dbdint:contract_public_verify', kwargs={'invitation_number': self.invitation.invitation_number})
        )
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
        
    def generate(self, request):
        """Generate complete PDF and return BytesIO buffer"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        
        # --- HEADER ---
        try:
            logo_response = requests.get(self.logo_url, timeout=5)
            if logo_response.status_code == 200:
                logo_img = ImageReader(io.BytesIO(logo_response.content))
                # Draw logo at top left
                c.drawImage(logo_img, 50, height - 80, width=150, height=40, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.warning(f"Could not load logo for PDF: {e}")
            # Fallback text if logo fails
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 60, "JHBridge Translation")
            
        # Agreement Metadata Box (Top Right)
        box_x = width - 200
        box_y = height - 90
        c.setFillColorRGB(0.11, 0.21, 0.34) # Deep Blue
        c.rect(box_x, box_y, 150, 60, fill=1, stroke=0)
        
        c.setFillColorRGB(1, 1, 1) # White text
        c.setFont("Helvetica-Bold", 10)
        c.drawString(box_x + 10, box_y + 40, "AGREEMENT ID")
        c.setFont("Helvetica", 9)
        c.drawString(box_x + 10, box_y + 25, self.invitation.invitation_number)
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(box_x + 10, box_y + 10, "DATE SIGNED")
        c.setFont("Helvetica", 9)
        signed_date = self.invitation.signed_at.strftime('%Y-%m-%d') if self.invitation.signed_at else "PENDING"
        c.drawString(box_x + 80, box_y + 10, signed_date)
        
        c.setFillColorRGB(0, 0, 0) # Reset to black
        
        # --- CONTENT ---
        # Contract text rendering using ReportLab Platypus for proper formatting
        c.setFont("Helvetica", 10)
        text_y = height - 130
        margin = 50
        max_width = width - 2 * margin
        lh = 14 # Line height
        
        # Add Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, text_y, "INDEPENDENT CONTRACTOR INTERPRETER AGREEMENT")
        text_y -= 30
        
        # Intro Text
        c.setFont("Helvetica", 10)
        intro = f"This Agreement is entered into by and between JHBridge Translation Services and {self.invitation.interpreter.user.get_full_name()}."
        c.drawString(margin, text_y, intro)
        text_y -= 20
        
        # Text Rendering using ReportLab Platypus for word wrapping
        from reportlab.platypus import Paragraph, Frame
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY
        
        # Create styles
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            fontName='Helvetica-Bold',
            spaceAfter=10
        )
        
        # Parse contract text into paragraphs
        story = []
        for line in self.contract_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Detect headings (lines starting with ## or in ALL CAPS)
            if line.startswith('##') or (line.isupper() and len(line) > 5):
                clean_line = line.replace('##', '').strip()
                story.append(Paragraph(clean_line, heading_style))
            else:
                story.append(Paragraph(line, normal_style))
        
        # Create frame for text content
        frame = Frame(
            margin,
            100,  # Bottom margin
            max_width,
            text_y - 100,  # Available height
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            showBoundary=0
        )
        
        # Add paragraphs to frame
        frame.addFromList(story, c)
        
        # NOTE: For a real multi-page document, we would use SimpleDocTemplate.
        # Since we draw on a canvas manually to control headers/footers,
        # we rely on Frame's basic overflow handling for single-page contracts.
        
        # Set fixed position for signature section
        text_y = 150

        # --- SIGNATURE SECTION ---
        # Ensure we have enough space, else new page
        if text_y < 200:
            c.showPage()
            text_y = height - 100
            
        text_y -= 30
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(margin, text_y, width - margin, text_y) # Separator line
        text_y -= 30
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, text_y, "SIGNATURES")
        text_y -= 40
        
        # Interpreter Signature
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, text_y, "INTERPRETER:")
        c.line(margin, text_y - 20, margin + 200, text_y - 20) # Signature line
        
        sig_text = self.invitation.interpreter.user.get_full_name()
        if self.invitation.status == 'SIGNED':
             # Digital Signature Statement - No fake signature font
             c.setFillColorRGB(0, 0.5, 0) # Dark Green for validity
             c.setFont("Helvetica-Bold", 10)
             c.drawString(margin + 10, text_y - 15, "DIGITALLY SIGNED")
             c.setFillColorRGB(0, 0, 0) # Reset
        
        c.setFont("Helvetica", 8)
        c.drawString(margin, text_y - 30, f"Signed by: {sig_text}")
        c.drawString(margin, text_y - 40, f"Date: {self.invitation.signed_at.strftime('%Y-%m-%d %H:%M:%S') if self.invitation.signed_at else ''}")
        
        # Company Signature
        company_x = width / 2 + 50
        c.setFont("Helvetica-Bold", 10)
        c.drawString(company_x, text_y, "JHBRIDGE TRANSLATION:")
        c.line(company_x, text_y - 20, company_x + 200, text_y - 20)
        
        c.setFont("Helvetica", 9)
        c.drawString(company_x + 10, text_y - 15, "Digitally Signed by Marc-Henry Valme")
        
        c.setFont("Helvetica", 8)
        c.drawString(company_x, text_y - 30, "Name: Marc-Henry Valme")
        c.drawString(company_x, text_y - 40, "JHBridge representative")
        
        # --- FOOTER & QR CODE ---
        try:
            logger.info("Generating QR code for PDF...")
            qr_buffer = self.generate_qr_code(request)
            qr_img = ImageReader(qr_buffer)
            # Draw slightly higher to ensure visibility: y=60
            c.drawImage(qr_img, width - 100, 60, width=60, height=60, preserveAspectRatio=True)
            logger.info("QR code drawn successfully.")
        except Exception as e:
            logger.error(f"Failed to draw QR code on PDF: {e}")
        
        c.save()
        buffer.seek(0)
        return buffer

    def upload_to_s3(self, pdf_buffer):
        """Upload generated PDF to S3 and return key"""
        try:
            storage = ContractStorage()
            date_path = timezone.now().strftime('%Y/%m')
            filename = f"contracts/{date_path}/{self.invitation.invitation_number}.pdf"
            
            # ContentFile wrapper needed for Django storage
            content = ContentFile(pdf_buffer.read())
            
            # Save using custom storage
            # Note: Django storage handles duplicate names if needed, 
            # though invitation_number should be unique.
            file_key = storage.save(filename, content)
            
            return file_key
        except Exception as e:
            logger.error(f"Failed to upload contract {self.invitation.invitation_number} to S3: {e}")
            raise

    def generate_and_upload(self, request):
        """Convenience method to generate and upload in one step"""
        try:
            pdf_buffer = self.generate(request)
            s3_key = self.upload_to_s3(pdf_buffer)
            
            # Update invitation
            self.invitation.pdf_s3_key = s3_key
            self.invitation.save(update_fields=['pdf_s3_key'])
            
            # Log event
            ContractTrackingEvent.objects.create(
                invitation=self.invitation,
                event_type='PDF_GENERATED',
                metadata={'s3_key': s3_key}
            )
            
            return s3_key
        except Exception as e:
            logger.error(f"Error in generate_and_upload: {e}")
            # Depending on requirements, might want to re-raise
            return None
