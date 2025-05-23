# Standard Library Imports
import io
import json
import logging
import os
import socket
import time
import pytz
import string
import tempfile
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from email.utils import make_msgid
import base64
import random
from django.db import models
import traceback
from django.utils.html import strip_tags
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.urls import NoReverseMatch
# Third-Party Imports
from docx import Document
from docx.shared import Inches
from icalendar import Calendar, Event, Alarm, vCalAddress, vText
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from django.core.mail import EmailMultiAlternatives
# Django Core Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.mail import send_mail, EmailMessage
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import ExtractDay, TruncMonth, TruncYear
from django.http import HttpResponse, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string, get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

# Local Imports
from .forms import (
    AssignmentFeedbackForm,
    ClientProfileForm,
    ClientProfileUpdateForm,
    ClientRegistrationForm1,
    ClientRegistrationForm2,
    ContactForm,
    CustomPasswordChangeForm,
    DeductionFormSet,ReimbursementFormSet,
    CustomPasswordResetForm,
    CustomPasswordtradChangeForm,
    InterpreterProfileForm,
    InterpreterRegistrationForm1,
    InterpreterRegistrationForm2,
    InterpreterRegistrationForm3,
    LoginForm,
    NotificationPreferenceForm,
    NotificationPreferencesForm,
    PayrollDocumentForm,
    PublicQuoteRequestForm,
    QuoteFilterForm,
    QuoteRequestForm,
    ServiceFormSet,
    UserCreationForm,
    UserProfileForm,
)
from .models import (
    Assignment,
    AssignmentNotification,
    Client,
    ContactMessage,
    Interpreter,
    Language,
    Notification,
    NotificationPreference,
    Payment,
    PayrollDocument,
    PublicQuoteRequest,
    Quote,
    QuoteRequest,
    Service,
    ServiceType,
    User,Reimbursement,Deduction,InterpreterContractSignature
)
from .mixins.assignment_mixins import AssignmentAdminMixin
from .assignment_views import AssignmentAcceptView, AssignmentDeclineView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import socket
import requests
import tempfile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import http.client
from urllib.parse import urlparse
#from .serializer import InterpreterContractSignatureSerializer
from .api_auth.decorators import api_key_required
# Constants
BOSTON_TZ = pytz.timezone('America/New_York')

# Logger configuration
logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def generate_pdf(request):
    """
    Vue pour générer un PDF à partir d'une capture d'écran.
    """
    try:
        # Récupérer et valider les données JSON
        try:
            data = json.loads(request.body)
            if 'imageData' not in data:
                return JsonResponse({
                    'error': 'Données d\'image manquantes'
                }, status=400)
            
            image_data = data['imageData'].split(',')[1]
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Données JSON invalides'
            }, status=400)
        
        # Créer des fichiers temporaires pour l'image et le PDF
        temp_img_path = None
        temp_pdf_path = None
        
        try:
            # Créer un fichier temporaire pour l'image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_img:
                temp_img_path = temp_img.name
                # Décoder et sauvegarder l'image
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                image.save(temp_img_path, 'PNG')
            
            # Créer un fichier temporaire pour le PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Créer le PDF
            pdf = canvas.Canvas(temp_pdf_path, pagesize=A4)
            pdf_width, pdf_height = A4
            
            # Calculer les dimensions
            aspect = image.width / image.height
            margin = 50
            
            usable_width = pdf_width - (2 * margin)
            usable_height = pdf_height - (2 * margin)
            
            if aspect > 1:
                width = usable_width
                height = width / aspect
            else:
                height = usable_height
                width = height * aspect
            
            # Centrer l'image
            x = (pdf_width - width) / 2
            y = (pdf_height - height) / 2
            
            # Ajouter l'image au PDF
            pdf.drawImage(temp_img_path, x, y, width, height)
            pdf.save()
            
            # Lire le PDF généré
            with open(temp_pdf_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            # Créer la réponse
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="payment-statement.pdf"'
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du PDF: {str(e)}")
            return JsonResponse({
                'error': 'Erreur lors de la génération du PDF'
            }, status=500)
            
        finally:
            # Nettoyer les fichiers temporaires
            if temp_img_path and os.path.exists(temp_img_path):
                os.unlink(temp_img_path)
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
        
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        return JsonResponse({
            'error': 'Une erreur inattendue est survenue'
        }, status=500)
        
def format_decimal(value):
    """Format decimal numbers to remove trailing zeros if no cents"""
    if value is None:
        return "0"
    # Convert to Decimal if not already
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    # Format with 2 decimals
    formatted = f"{value:.2f}"
    # Remove .00 if no cents
    if formatted.endswith('.00'):
        return formatted[:-3]
    return formatted

def generate_document_number():
    """Generate a unique document number based on timestamp and random string"""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"JHB-{timestamp}-{random_str}"

class PayrollCreateView(CreateView):
    model = PayrollDocument
    form_class = PayrollDocumentForm
    template_name = 'payroll_form.html'
    success_url = reverse_lazy('dbdint:payroll_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['service_formset'] = ServiceFormSet(self.request.POST, self.request.FILES, prefix='services')
            context['reimbursement_formset'] = ReimbursementFormSet(self.request.POST, self.request.FILES, prefix='reimbursements', queryset=Reimbursement.objects.none())
            context['deduction_formset'] = DeductionFormSet(self.request.POST, self.request.FILES, prefix='deductions', queryset=Deduction.objects.none())
        else:
            context['service_formset'] = ServiceFormSet(queryset=Service.objects.none(), prefix='services')
            context['reimbursement_formset'] = ReimbursementFormSet(queryset=Reimbursement.objects.none(), prefix='reimbursements')
            context['deduction_formset'] = DeductionFormSet(queryset=Deduction.objects.none(), prefix='deductions')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        service_formset = context['service_formset']
        reimbursement_formset = context['reimbursement_formset']
        deduction_formset = context['deduction_formset']

        # Vérifier si les formsets sont valides
        if not service_formset.is_valid():
            return self.form_invalid(form)
        
        # Vérifier les formsets de remboursement et déduction seulement s'ils contiennent des données
        has_reimbursement_data = False
        for reimbursement_form in reimbursement_formset:
            if reimbursement_form.has_changed():
                has_reimbursement_data = True
                break
                    
        has_deduction_data = False
        for deduction_form in deduction_formset:
            if deduction_form.has_changed():
                has_deduction_data = True
                break
        
        # Valider les formsets seulement s'ils contiennent des données
        if has_reimbursement_data and not reimbursement_formset.is_valid():
            return self.form_invalid(form)
                
        if has_deduction_data and not deduction_formset.is_valid():
            return self.form_invalid(form)

        # Sauvegarder le document principal
        self.object = form.save(commit=False)
        self.object.document_number = generate_document_number()
        self.object.document_date = datetime.now().date()
        self.object.save()

        # Sauvegarder les services
        services = service_formset.save(commit=False)
        for service in services:
            service.payroll = self.object
            service.save()
        
        # Gérer les suppressions des services
        for obj in service_formset.deleted_objects:
            obj.delete()

        # Sauvegarder les remboursements (seulement s'ils existent)
        if has_reimbursement_data:
            reimbursements = reimbursement_formset.save(commit=False)
            for reimbursement in reimbursements:
                # Vérifier si le formulaire est marqué pour suppression après validation
                if not hasattr(reimbursement_form, 'cleaned_data') or not reimbursement_form.cleaned_data.get('DELETE', False):
                    reimbursement.payroll = self.object
                    reimbursement.save()
            
            # Gérer les suppressions des remboursements
            for obj in reimbursement_formset.deleted_objects:
                obj.delete()

        # Sauvegarder les déductions (seulement s'ils existent)
        if has_deduction_data:
            deductions = deduction_formset.save(commit=False)
            for deduction in deductions:
                # Vérifier si le formulaire est marqué pour suppression après validation
                if not hasattr(deduction_form, 'cleaned_data') or not deduction_form.cleaned_data.get('DELETE', False):
                    deduction.payroll = self.object
                    deduction.save()
            
            # Gérer les suppressions des déductions
            for obj in deduction_formset.deleted_objects:
                obj.delete()

        # Gérer les réponses AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'id': self.object.pk,
                'message': 'Document saved successfully'
            })
        
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            context = self.get_context_data()
            return JsonResponse({
                'status': 'error',
                'errors': {
                    'form': form.errors,
                    'service_formset': context['service_formset'].errors,
                    'reimbursement_formset': context['reimbursement_formset'].errors,
                    'deduction_formset': context['deduction_formset'].errors
                }
            }, status=400)
        return super().form_invalid(form)

class PayrollDetailView(DetailView):
    model = PayrollDocument
    template_name = 'payroll_template.html'
    context_object_name = 'payroll'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les données
        services = self.object.services.all()
        reimbursements = self.object.reimbursements.all()
        deductions = self.object.deductions.all()
        
        # Initialiser les totaux
        total_duration = Decimal('0')
        total_service_amount = Decimal('0')
        total_reimbursement_amount = Decimal('0')
        total_deduction_amount = Decimal('0')
        
        # Calculer les totaux pour les services
        for service in services:
            total_duration += service.duration or Decimal('0')
            total_service_amount += service.amount
        
        # Calculer le total des remboursements
        for reimbursement in reimbursements:
            total_reimbursement_amount += reimbursement.amount
        
        # Calculer le total des déductions
        for deduction in deductions:
            total_deduction_amount += deduction.amount
        
        # Calculer le montant final (services + remboursements - déductions)
        final_amount = total_service_amount + total_reimbursement_amount - total_deduction_amount
        
        # Mettre à jour le contexte avec toutes les données calculées
        context.update({
            'services': services,
            'reimbursements': reimbursements,
            'deductions': deductions,
            'total_duration': format_decimal(total_duration),
            'total_service_amount': format_decimal(total_service_amount),
            'total_reimbursement_amount': format_decimal(total_reimbursement_amount),
            'total_deduction_amount': format_decimal(total_deduction_amount),
            'final_amount': format_decimal(final_amount),
            'generation_date': datetime.now().date()
        })
        
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)

        # Check if export is requested
        export_format = request.GET.get('export')
        if export_format == 'pdf':
            return export_document(request, self.object.pk)

        return super().get(request, *args, **kwargs)

class PayrollPreviewView(DetailView):
    template_name = 'payroll_template.html'
    context_object_name = 'payroll'

    def post(self, request, *args, **kwargs):
        form = PayrollDocumentForm(request.POST, request.FILES)
        service_formset = ServiceFormSet(request.POST, prefix='services')
        reimbursement_formset = ReimbursementFormSet(request.POST, request.FILES, prefix='reimbursements')
        deduction_formset = DeductionFormSet(request.POST, prefix='deductions')
        
        if form.is_valid() and service_formset.is_valid():
            # Vérifier les formsets de remboursement et déduction seulement s'ils contiennent des données
            has_reimbursement_data = False
            valid_reimbursements = True
            for reimbursement_form in reimbursement_formset:
                if reimbursement_form.has_changed() and not reimbursement_form.cleaned_data.get('DELETE', False):
                    has_reimbursement_data = True
                    if not reimbursement_form.is_valid():
                        valid_reimbursements = False
                    break
                    
            has_deduction_data = False
            valid_deductions = True
            for deduction_form in deduction_formset:
                if deduction_form.has_changed() and not deduction_form.cleaned_data.get('DELETE', False):
                    has_deduction_data = True
                    if not deduction_form.is_valid():
                        valid_deductions = False
                    break
            
            if ((has_reimbursement_data and not valid_reimbursements) or 
                (has_deduction_data and not valid_deductions)):
                return JsonResponse({
                    'status': 'error',
                    'errors': {
                        'form': form.errors,
                        'service_formset': service_formset.errors,
                        'reimbursement_formset': reimbursement_formset.errors if has_reimbursement_data else {},
                        'deduction_formset': deduction_formset.errors if has_deduction_data else {}
                    }
                }, status=400)
            
            payroll = form.save(commit=False)
            payroll.document_number = generate_document_number()
            payroll.document_date = datetime.now().date()
            
            # Préparer les services pour l'affichage
            services = service_formset.save(commit=False)
            
            # Préparer les remboursements pour l'affichage
            reimbursements = []
            if has_reimbursement_data:
                reimbursements = [form.save(commit=False) for form in reimbursement_formset 
                                 if form.has_changed() and not form.cleaned_data.get('DELETE', False)]
            
            # Préparer les déductions pour l'affichage
            deductions = []
            if has_deduction_data:
                deductions = [form.save(commit=False) for form in deduction_formset 
                             if form.has_changed() and not form.cleaned_data.get('DELETE', False)]
            
            # Calculer les totaux
            total_duration = Decimal('0')
            total_service_amount = Decimal('0')
            total_reimbursement_amount = Decimal('0')
            total_deduction_amount = Decimal('0')
            
            # Services
            for service in services:
                service.duration = service.duration if service.duration else Decimal('0')
                service.rate = service.rate if service.rate else Decimal('0')
                
                total_duration += service.duration
                total_service_amount += service.duration * service.rate
            
            # Remboursements
            for reimbursement in reimbursements:
                total_reimbursement_amount += reimbursement.amount
            
            # Déductions
            for deduction in deductions:
                total_deduction_amount += deduction.amount
            
            # Montant final
            final_amount = total_service_amount + total_reimbursement_amount - total_deduction_amount
            
            # Préparer le contexte pour la prévisualisation
            context = {
                'payroll': payroll,
                'services': services,
                'reimbursements': reimbursements,
                'deductions': deductions,
                'total_duration': format_decimal(total_duration),
                'total_service_amount': format_decimal(total_service_amount),
                'total_reimbursement_amount': format_decimal(total_reimbursement_amount),
                'total_deduction_amount': format_decimal(total_deduction_amount),
                'final_amount': format_decimal(final_amount),
                'generation_date': datetime.now().date(),
                'is_preview': True
            }
            
            return render(request, 'payroll_template.html', context)
        else:
            return JsonResponse({
                'status': 'error',
                'errors': {
                    'form': form.errors,
                    'service_formset': service_formset.errors
                }
            }, status=400)

# Dans views.py

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from decimal import Decimal
from datetime import datetime

def format_decimal(value):
    """Format decimal numbers to remove trailing zeros if no cents"""
    if value is None:
        return "0"
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    formatted = f"{value:.2f}"
    if formatted.endswith('.00'):
        return formatted[:-3]
    return formatted

def export_document(request, pk):
    try:
        payroll = get_object_or_404(PayrollDocument, pk=pk)
        services = payroll.services.all()

        # Création du PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Liste des éléments du PDF
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#003B71'),
            alignment=1  # Centre
        )

        # En-tête
        elements.append(Paragraph("JHBRIDGE TRANSLATION SERVICES", title_style))
        elements.append(Paragraph("Payment Statement", styles['Heading1']))
        elements.append(Spacer(1, 20))

        # Informations du document
        elements.append(Paragraph(f"Document No: {payroll.document_number}", styles['Normal']))
        elements.append(Paragraph(f"Date: {payroll.document_date.strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Informations de l'entreprise
        elements.append(Paragraph("From:", styles['Heading2']))
        elements.append(Paragraph(payroll.company_address or "500 GROSSMAN DR, BRAINTREE, MA, 02184", styles['Normal']))
        elements.append(Paragraph(payroll.company_phone or "+1 (774) 223 8771", styles['Normal']))
        elements.append(Paragraph(payroll.company_email or "jhbridgetranslation@gmail.com", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Informations de l'interprète
        elements.append(Paragraph("To:", styles['Heading2']))
        elements.append(Paragraph(payroll.interpreter_name, styles['Normal']))
        elements.append(Paragraph(payroll.interpreter_address, styles['Normal']))
        elements.append(Paragraph(payroll.interpreter_phone, styles['Normal']))
        elements.append(Paragraph(payroll.interpreter_email, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Tableau des services
        table_data = [['Date', 'Client', 'Languages', 'Duration', 'Rate', 'Amount']]
        
        total_duration = Decimal('0')
        total_amount = Decimal('0')

        for service in services:
            duration = service.duration or Decimal('0')
            rate = service.rate or Decimal('0')
            amount = service.amount

            total_duration += duration
            total_amount += amount

            table_data.append([
                service.date.strftime('%b %d, %Y'),
                service.client,
                f"{service.source_language} > {service.target_language}",
                f"{format_decimal(duration)} hrs",
                f"${format_decimal(rate)}",
                f"${format_decimal(amount)}"
            ])

        # Style du tableau
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003B71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Corps du tableau
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        # Totaux
        elements.append(Paragraph(f"Total Duration: {format_decimal(total_duration)} hrs", styles['Normal']))
        elements.append(Paragraph(f"Total Amount: ${format_decimal(total_amount)}", styles['Heading2']))

        # Pied de page
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(Paragraph(f"© {datetime.now().year} JH BRIDGE Translation. All rights reserved.", styles['Normal']))

        # Génération du PDF
        doc.build(elements)
        buffer.seek(0)

        # Retourne le PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="statement_{payroll.document_number}.pdf"'

        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)














class ChooseRegistrationTypeView(TemplateView):
    template_name = 'choose_registration.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.role == 'CLIENT':
                return redirect('dbdint:client_dashboard')
            return redirect('dbdint:interpreter_dashboard')
        return super().dispatch(request, *args, **kwargs)



class PublicQuoteRequestView(CreateView):
    model = PublicQuoteRequest
    form_class = PublicQuoteRequestForm
    template_name = 'public/quote_request_form.html'
    success_url = reverse_lazy('dbdint:quote_request_success')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Request a Quote'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        quote_request = self.object

        # Send confirmation email to customer
        customer_context = {
            'quote_request': quote_request,
            'name': quote_request.full_name,
        }
        customer_email_html = render_to_string('emails/quote_request_confirmation.html', customer_context)
        customer_email_txt = render_to_string('emails/quote_request_confirmation.txt', customer_context)

        send_mail(
            subject='Quote Request Received - JHBRIDGE',
            message=customer_email_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[quote_request.email],
            html_message=customer_email_html,
            fail_silently=False,
        )

        # Send notification to staff
        staff_context = {
            'quote_request': quote_request,
            'admin_url': self.request.build_absolute_uri(
                reverse('dbdint:app_publicquoterequest_change', args=[quote_request.id])
            )
        }
        staff_email_html = render_to_string('emails/quote_request_notification.html', staff_context)
        staff_email_txt = render_to_string('emails/quote_request_notification.txt', staff_context)

        send_mail(
            subject=f'New Quote Request: {quote_request.company_name}',
            message=staff_email_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.QUOTE_NOTIFICATION_EMAIL],
            html_message=staff_email_html,
            fail_silently=False,
        )

        messages.success(
            self.request,
            'Your quote request has been submitted successfully! '
            'We will contact you shortly with more information.'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'There was an error with your submission. Please check the form and try again.'
        )
        return super().form_invalid(form)

class QuoteRequestSuccessView(TemplateView):
    template_name = 'public/quote_request_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Quote Request Submitted'
        return context
    
    
class ContactView(CreateView):
    model = ContactMessage
    form_class = ContactForm
    template_name = 'public/contact.html'
    success_url = reverse_lazy('dbdint:contact_success')

    def form_valid(self, form):
        response = super().form_valid(form)
        contact = self.object

        # Send confirmation email to the sender
        send_mail(
            subject='Thank you for contacting JHBRIDGE',
            message=f"""Dear {contact.name},

Thank you for contacting JHBRIDGE. We have received your message and will get back to you shortly.

Your message details:
Subject: {contact.subject}
Reference Number: #{contact.id}

Best regards,
JHBRIDGE Team""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact.email],
            fail_silently=False,
        )

        # Send notification to staff
        send_mail(
            subject=f'New Contact Form Submission: {contact.subject}',
            message=f"""New contact form submission received:

From: {contact.name} <{contact.email}>
Subject: {contact.subject}

Message:
{contact.message}

View in admin panel: {self.request.build_absolute_uri(reverse('dbdint:app_contactmessage_change', args=[contact.id]))}""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_NOTIFICATION_EMAIL],
            fail_silently=False,
        )

        messages.success(
            self.request,
            'Your message has been sent successfully! We will contact you shortly.'
        )
        return response

class ContactSuccessView(TemplateView):
    template_name = 'public/contact_success.html'
    



class CustomLoginView(LoginView):
    template_name = 'login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        logger.info(f"Determining success URL for user {user.id} with role {user.role}")
        
        try:
            if user.role == 'CLIENT':
                logger.debug(f"User {user.id} identified as CLIENT, redirecting to client dashboard")
                return reverse_lazy('dbdint:client_dashboard')
            
            logger.debug(f"User {user.id} identified as INTERPRETER, redirecting to interpreter dashboard")
            return reverse_lazy('dbdint:new_interpreter_dashboard')
            
        except Exception as e:
            logger.error(f"Error in get_success_url for user {user.id}: {str(e)}", exc_info=True)
            raise

    def form_invalid(self, form):
        logger.warning(
            "Login attempt failed",
            extra={
                'errors': form.errors,
                'cleaned_data': form.cleaned_data,
                'ip_address': self.request.META.get('REMOTE_ADDR')
            }
        )
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)

    def form_valid(self, form):
        logger.info(f"Successful login for user: {form.get_user().id}")
        return super().form_valid(form)
#################################CLIENT##################
#########################################################
####################################################################################################################################################
#########################################################
#########################################################



@method_decorator(never_cache, name='dispatch')
class ClientRegistrationView(FormView):
    template_name = 'client/auth/step1.html'
    form_class = ClientRegistrationForm1
    success_url = reverse_lazy('dbdint:client_register_step2')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.registration_complete:
            return redirect('dbdint:client_dashboard')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            logger.info("Processing valid registration form step 1")
            
            # Créer l'utilisateur avec le rôle CLIENT
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone=form.cleaned_data['phone'],
                role=User.Roles.CLIENT,
                registration_complete=False
            )

            # Connecter l'utilisateur
            login(self.request, user)
            
            logger.info(
                f"Step 1 completed successfully",
                extra={
                    'user_id': user.id,
                    'username': user.username,
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )

            messages.success(self.request, "Personal information saved successfully. Please complete your company details.")
            return super().form_valid(form)

        except Exception as e:
            logger.error(
                "Error processing registration form step 1",
                exc_info=True,
                extra={
                    'form_data': {
                        k: v for k, v in form.cleaned_data.items() 
                        if k not in ['password1', 'password2']
                    },
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )
            messages.error(self.request, "An error occurred during registration. Please try again.")
            return self.form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class ClientRegistrationStep2View(FormView):
    template_name = 'client/auth/step2.html'
    form_class = ClientRegistrationForm2
    success_url = reverse_lazy('dbdint:client_dashboard')

    def get(self, request, *args, **kwargs):
        # Si l'utilisateur n'est pas authentifié, rediriger vers l'étape 1
        if not request.user.is_authenticated:
            messages.error(request, "Please complete step 1 first.")
            return redirect('dbdint:client_register')
            
        # Si l'utilisateur a déjà complété son inscription
        if request.user.registration_complete:
            return redirect('dbdint:client_dashboard')
        
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['user_data'] = {
                'username': self.request.user.username,
                'email': self.request.user.email,
                'first_name': self.request.user.first_name,
                'last_name': self.request.user.last_name,
                'phone': self.request.user.phone
            }
        return context

    def form_valid(self, form):
        try:
            logger.info("Processing valid registration form step 2")
            
            if not self.request.user.is_authenticated:
                messages.error(self.request, "Session expired. Please start over.")
                return redirect('dbdint:client_register')

            # Créer le profil client avec l'utilisateur existant
            client_profile = form.save(commit=False)
            client_profile.user = self.request.user
            client_profile.save()

            # Marquer l'inscription comme complète
            self.request.user.registration_complete = True
            self.request.user.save()
            
            logger.info(
                "Registration completed successfully",
                extra={
                    'user_id': self.request.user.id,
                    'username': self.request.user.username,
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )

            messages.success(self.request, "Registration completed successfully! Welcome to JHBRIDGE.")
            return super().form_valid(form)

        except Exception as e:
            logger.error(
                "Error processing registration form step 2",
                exc_info=True,
                extra={
                    'form_data': form.cleaned_data,
                    'ip_address': self.request.META.get('REMOTE_ADDR')
                }
            )
            raise

    def form_invalid(self, form):
        logger.warning(
            "Invalid registration form step 2 submission",
            extra={
                'errors': form.errors,
                'ip_address': self.request.META.get('REMOTE_ADDR')
            }
        )
        return super().form_invalid(form)
    
    
    
class NotificationPreferencesView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferencesForm
    template_name = 'client/setnotifications.html'
    success_url = reverse_lazy('dbdint:client_dashboard')

    def get_object(self, queryset=None):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference

    def form_valid(self, form):
        messages.success(self.request, 'Your notification preferences have been updated!')
        return super().form_valid(form)

class RegistrationSuccessView(TemplateView):
    template_name = 'client/auth/success.html'
    
    



class ClientDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'client/home.html'
    login_url = 'dbdint:login'
    permission_denied_message = "Access denied. This area is for clients only."
    
    def test_func(self):
        user = self.request.user
        
        logger.debug(
            "Testing client dashboard access",
            extra={
                'user_id': user.id,
                'role': getattr(user, 'role', 'NO_ROLE'),
                'has_client_profile': hasattr(user, 'client_profile'),
                'registration_complete': user.registration_complete
            }
        )
        
        if not user.role:
            logger.error(f"User {user.id} has no role assigned")
            return False

        return (user.role == User.Roles.CLIENT and 
                hasattr(user, 'client_profile') and 
                user.registration_complete)

    def handle_no_permission(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return redirect(self.login_url)
        
        if not user.role:
            messages.error(self.request, "Your account setup is incomplete. Please contact support.")
            return redirect('dbdint:home')
            
        if user.role == User.Roles.CLIENT and not user.registration_complete:
            if 'registration_step1' in self.request.session:
                return redirect('dbdint:client_register_step2')
            else:
                return redirect('dbdint:client_register')
                
        if user.role == User.Roles.INTERPRETER:
            messages.warning(self.request, "This area is for clients only. Redirecting to interpreter dashboard.")
            return redirect('dbdint:new_interpreter_dashboard')
        elif user.role == User.Roles.ADMIN:
            return redirect('dbdint:admin_dashboard')
            
        messages.error(self.request, "Access denied. Please complete your registration or contact support.")
        return redirect('dbdint:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            client = self.request.user.client_profile
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Statistiques de base
            context['stats'] = {
                'pending_quotes': QuoteRequest.objects.filter(
                    client=client, 
                    status='PENDING'
                ).count(),
                'active_assignments': Assignment.objects.filter(
                    client=client, 
                    status__in=['CONFIRMED', 'IN_PROGRESS']
                ).count(),
                'completed_assignments': Assignment.objects.filter(
                    client=client, 
                    status='COMPLETED', 
                    completed_at__gte=thirty_days_ago
                ).count(),
                'total_spent': Payment.objects.filter(
                    assignment__client=client,
                    status='COMPLETED',
                    payment_date__gte=thirty_days_ago
                ).aggregate(total=Sum('amount'))['total'] or 0
            }
            
            # Données récentes
            context.update({
                'recent_quotes': QuoteRequest.objects.filter(
                    client=client
                ).select_related(
                    'service_type',
                    'source_language',
                    'target_language'
                ).order_by('-created_at')[:5],
                
                'upcoming_assignments': Assignment.objects.filter(
                    client=client,
                    status__in=['CONFIRMED', 'IN_PROGRESS'],
                    start_time__gte=timezone.now()
                ).select_related(
                    'service_type',
                    'source_language',
                    'target_language'
                ).order_by('start_time')[:5],
                
                'recent_payments': Payment.objects.filter(
                    assignment__client=client
                ).select_related(
                    'assignment',
                    'assignment__service_type'
                ).order_by('-payment_date')[:5],
                
                'unread_notifications': Notification.objects.filter(
                    recipient=self.request.user,
                    read=False
                ).order_by('-created_at')[:5],
                
                'client_profile': client
            })

        except Exception as e:
            logger.error(
                "Error loading client dashboard data",
                exc_info=True,
                extra={
                    'user_id': self.request.user.id,
                    'error': str(e)
                }
            )
            messages.error(
                self.request,
                "There was a problem loading your dashboard data. Please refresh the page or contact support if the problem persists."
            )
            context.update({
                'error_loading_data': True,
                'stats': {
                    'pending_quotes': 0,
                    'active_assignments': 0,
                    'completed_assignments': 0,
                    'total_spent': 0
                }
            })
        
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        response = super().dispatch(request, *args, **kwargs)
        
        if response.status_code == 200:
            logger.info(
                "Client dashboard accessed successfully",
                extra={
                    'user_id': request.user.id,
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
        
        return response
class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # Get notification ID from request data
            notification_id = request.POST.get('notification_id')
            
            if not notification_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Notification ID is required'
                }, status=400)

            # Get notification and verify ownership
            notification = Notification.objects.get(
                id=notification_id,
                recipient=request.user,
            )
            
            # Mark as read
            notification.read = True
            notification.read_at = timezone.now()
            notification.save()

            return JsonResponse({
                'success': True,
                'message': 'Notification marked as read',
                'notification_id': notification_id
            })

        except Notification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Notification not found'
            }, status=404)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred'
            }, status=500)

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'success': False,
            'message': 'Method not allowed'
        }, status=405)

class ClearAllNotificationsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # Get all unread notifications for the user
            notifications = Notification.objects.filter(
                recipient=request.user,
                read=False
            )
            
            # Update all notifications
            count = notifications.count()
            notifications.update(
                read=True,
                read_at=timezone.now()
            )

            return JsonResponse({
                'success': True,
                'message': f'{count} notifications marked as read',
                'count': count
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred'
            }, status=500)

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'success': False,
            'message': 'Method not allowed'
        }, status=405)




class ClientRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a client"""
    def test_func(self):
        return self.request.user.role == 'CLIENT'
class QuoteRequestListView(LoginRequiredMixin, ClientRequiredMixin, ListView):
    """
    Display all quote requests for the client with filtering and pagination
    """
    model = QuoteRequest
    template_name = 'client/quote_list.html'
    context_object_name = 'quotes'
    paginate_by = 10

    def get_queryset(self):
        queryset = QuoteRequest.objects.filter(
            client=self.request.user.client_profile
        ).order_by('-created_at')

        # Apply filters from form
        filter_form = QuoteFilterForm(self.request.GET)
        if filter_form.is_valid():
            # Status filter
            status = filter_form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)

            # Date range filter
            date_from = filter_form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(requested_date__gte=date_from)

            date_to = filter_form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(requested_date__lte=date_to)

            # Service type filter
            service_type = filter_form.cleaned_data.get('service_type')
            if service_type:
                queryset = queryset.filter(service_type=service_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter form
        context['filter_form'] = QuoteFilterForm(self.request.GET)
        
        # Add choices for dropdowns
        context['status_choices'] = QuoteRequest.Status.choices
        # Pour le service_type, on doit faire une requête car c'est un modèle
        context['service_types'] = ServiceType.objects.filter(active=True).values_list('id', 'name')
        
        # Add statistics
        base_queryset = self.get_queryset()
        context['stats'] = {
            'pending_count': base_queryset.filter(status=QuoteRequest.Status.PENDING).count(),
            'processing_count': base_queryset.filter(status=QuoteRequest.Status.PROCESSING).count(),
            'quoted_count': base_queryset.filter(status=QuoteRequest.Status.QUOTED).count(),
            'accepted_count': base_queryset.filter(status=QuoteRequest.Status.ACCEPTED).count()
        }

        # Add current filters to context for pagination
        context['current_filters'] = self.request.GET.dict()
        if 'page' in context['current_filters']:
            del context['current_filters']['page']
            
        return context

class QuoteRequestCreateView(LoginRequiredMixin, ClientRequiredMixin, CreateView):
    """
    Create a new quote request
    """
    model = QuoteRequest
    form_class = QuoteRequestForm
    template_name = 'client/quote_create.html'
    success_url = reverse_lazy('dbdint:client_quote_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.client = self.request.user.client_profile
        form.instance.status = QuoteRequest.Status.PENDING
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            'Your quote request has been successfully submitted. Our team will review it shortly.'
        )
        return response

class QuoteRequestDetailView(LoginRequiredMixin, ClientRequiredMixin, DetailView):
    """
    Display detailed information about a quote request and its timeline
    """
    model = QuoteRequest
    template_name = 'client/quote_detail.html'
    context_object_name = 'quote_request'

    def get_queryset(self):
        return QuoteRequest.objects.filter(
            client=self.request.user.client_profile
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quote_request = self.get_object()
        
        # Get related quote if exists
        try:
            context['quote'] = quote_request.quote
        except Quote.DoesNotExist:
            context['quote'] = None

        # Get related assignment if exists
        if context['quote'] and context['quote'].status == 'ACCEPTED':
            try:
                context['assignment'] = context['quote'].assignment
            except Assignment.DoesNotExist:
                context['assignment'] = None

        # Create timeline events
        timeline_events = [
            {
                'date': quote_request.created_at,
                'status': 'CREATED',
                'description': 'Quote request submitted'
            }
        ]
        
        # Add quote events if exists
        if context['quote']:
            timeline_events.append({
                'date': context['quote'].created_at,
                'status': 'QUOTED',
                'description': 'Quote generated and sent'
            })

        # Add assignment events if exists
        if context.get('assignment'):
            timeline_events.append({
                'date': context['assignment'].created_at,
                'status': 'ASSIGNED',
                'description': 'Interpreter assigned'
            })
            if context['assignment'].status == 'COMPLETED':
                timeline_events.append({
                    'date': context['assignment'].completed_at,
                    'status': 'COMPLETED',
                    'description': 'Service completed'
                })

        context['timeline_events'] = sorted(
            timeline_events,
            key=lambda x: x['date'],
            reverse=True
        )

        return context

class QuoteAcceptView(LoginRequiredMixin, ClientRequiredMixin, View):
    """
    Handle quote acceptance
    """
    def post(self, request, *args, **kwargs):
        quote = get_object_or_404(
            Quote,
            quote_request__client=request.user.client_profile,
            pk=kwargs['pk'],
            status='SENT'
        )

        try:
            quote.status = Quote.Status.ACCEPTED
            quote.save()
            
            messages.success(
                request,
                'Quote accepted successfully. Our team will assign an interpreter shortly.'
            )
            return redirect('dbdint:client_quote_detail', pk=quote.quote_request.pk)

        except Exception as e:
            messages.error(request, 'An error occurred while accepting the quote.')
            return redirect('dbdint:quote_detail', pk=quote.quote_request.pk)

class QuoteRejectView(LoginRequiredMixin, ClientRequiredMixin, View):
    """
    Handle quote rejection
    """
    def post(self, request, *args, **kwargs):
        quote = get_object_or_404(
            Quote,
            quote_request__client=request.user.client_profile,
            pk=kwargs['pk'],
            status='SENT'
        )

        try:
            quote.status = Quote.Status.REJECTED
            quote.save()
            
            messages.success(request, 'Quote rejected successfully.')
            return redirect('dbdint:client_quote_detail', pk=quote.quote_request.pk)

        except Exception as e:
            messages.error(request, 'An error occurred while rejecting the quote.')
            return redirect('dbdint:quote_detail', pk=quote.quote_request.pk)

class AssignmentDetailClientView(LoginRequiredMixin, ClientRequiredMixin, DetailView):
    """
    Display assignment details for the client
    """
    model = Assignment
    template_name = 'client/assignment_detail.html'
    context_object_name = 'assignment'

    def get_queryset(self):
        return Assignment.objects.filter(
            client=self.request.user.client_profile
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = self.get_object()

        # Add feedback form if assignment is completed and no feedback exists
        if (assignment.status == 'COMPLETED' and 
            not hasattr(assignment, 'assignmentfeedback')):
            context['feedback_form'] = AssignmentFeedbackForm()

        return context

    def post(self, request, *args, **kwargs):
        """Handle feedback submission"""
        assignment = self.get_object()
        
        if assignment.status != 'COMPLETED':
            messages.error(request, 'Feedback can only be submitted for completed assignments.')
            return redirect('dbdint:client_assignment_detail', pk=assignment.pk)

        if hasattr(assignment, 'assignmentfeedback'):
            messages.error(request, 'Feedback has already been submitted for this assignment.')
            return redirect('dbdint:client_assignment_detail', pk=assignment.pk)

        form = AssignmentFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.assignment = assignment
            feedback.created_by = request.user
            feedback.save()
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('dbdint:client_assignment_detail', pk=assignment.pk)

        context = self.get_context_data(object=assignment)
        context['feedback_form'] = form
        return self.render_to_response(context)




class ProfileView(LoginRequiredMixin, TemplateView):
    """Main profile view that combines user and client profile forms"""
    template_name = 'client/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_form'] = UserProfileForm(instance=self.request.user)
        context['client_form'] = ClientProfileForm(instance=self.request.user.client_profile)
        return context

    def post(self, request, *args, **kwargs):
        user_form = UserProfileForm(request.POST, instance=request.user)
        client_form = ClientProfileForm(request.POST, instance=request.user.client_profile)

        if user_form.is_valid() and client_form.is_valid():
            user_form.save()
            client_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('dbdint:client_profile_edit')
        
        return self.render_to_response(
            self.get_context_data(
                user_form=user_form,
                client_form=client_form
            )
        )
        
        
class ClientProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientProfileUpdateForm
    template_name = 'accounts/profile/update.html'
    success_url = reverse_lazy('dbdint:client_dashboard')

    def get_object(self, queryset=None):
        return self.request.user.client_profile

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully!')
        return super().form_valid(form)


class ProfilePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """View for changing password"""
    form_class = CustomPasswordChangeForm
    template_name = 'client/change_password.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully.')
        return super().form_valid(form)


#####INTERPRETERDASHBOARD##################################


@method_decorator(never_cache, name='dispatch')
class InterpreterRegistrationStep1View(FormView):
   template_name = 'trad/auth/step1.html'
   form_class = InterpreterRegistrationForm1
   success_url = reverse_lazy('dbdint:interpreter_registration_step2')

   def dispatch(self, request, *args, **kwargs):
       logger.info(f"Dispatch called for InterpreterRegistrationStep1View - User authenticated: {request.user.is_authenticated}")
       
       if request.user.is_authenticated:
           logger.info(f"Authenticated user {request.user.email} attempting to access registration. Redirecting to dashboard.")
           return redirect('dbdint:interpreter_dashboard')
       return super().dispatch(request, *args, **kwargs)

   def form_valid(self, form):
       logger.info("Form validation successful for InterpreterRegistrationStep1View")
       
       try:
           session_data = {
               'username': form.cleaned_data['username'],
               'email': form.cleaned_data['email'],
               'password': form.cleaned_data['password1'],
               'first_name': form.cleaned_data['first_name'],
               'last_name': form.cleaned_data['last_name'],
               'phone': form.cleaned_data['phone']
           }
           self.request.session['dbdint:interpreter_registration_step1'] = session_data
           logger.info(f"Session data saved successfully for username: {session_data['username']}, email: {session_data['email']}")
           
       except Exception as e:
           logger.error(f"Error saving session data: {str(e)}")
           messages.error(self.request, 'An error occurred while saving your information.')
           return self.form_invalid(form)
       
       logger.info(f"Redirecting to step 2 for username: {session_data['username']}")
       return super().form_valid(form)

   def form_invalid(self, form):
       logger.warning("Form validation failed for InterpreterRegistrationStep1View")
       logger.debug(f"Form errors: {form.errors}")
       
       messages.error(self.request, 'Please correct the errors below.')
       return super().form_invalid(form)

   def get(self, request, *args, **kwargs):
       logger.info("GET request received for InterpreterRegistrationStep1View")
       return super().get(request, *args, **kwargs)

   def post(self, request, *args, **kwargs):
       logger.info("POST request received for InterpreterRegistrationStep1View")
       logger.debug(f"POST data: {request.POST}")
       return super().post(request, *args, **kwargs)

@method_decorator(never_cache, name='dispatch')
class InterpreterRegistrationStep2View(FormView):
   template_name = 'trad/auth/step2.html'
   form_class = InterpreterRegistrationForm2
   success_url = reverse_lazy('dbdint:interpreter_registration_step3')

   def get_context_data(self, **kwargs):
       logger.info("Getting context data for InterpreterRegistrationStep2View")
       context = super().get_context_data(**kwargs)
       
       try:
           context['languages'] = Language.objects.filter(is_active=True)
           logger.debug(f"Found {context['languages'].count()} active languages")
           
           step2_data = self.request.session.get('dbdint:interpreter_registration_step2')
           if step2_data and 'languages' in step2_data:
               context['selected_languages'] = step2_data['languages']
               logger.debug(f"Retrieved previously selected languages: {step2_data['languages']}")
       except Exception as e:
           logger.error(f"Error getting context data: {str(e)}")
           
       return context

   def dispatch(self, request, *args, **kwargs):
       logger.info("Dispatch called for InterpreterRegistrationStep2View")
       
       if not request.session.get('dbdint:interpreter_registration_step1'):
           logger.warning("Step 1 data not found in session. Redirecting to step 1.")
           messages.error(request, 'Please complete step 1 first.')
           return redirect('dbdint:interpreter_registration_step1')
           
       logger.debug("Step 1 data found in session. Proceeding with step 2.")
       return super().dispatch(request, *args, **kwargs)

   def form_valid(self, form):
       logger.info("Form validation successful for InterpreterRegistrationStep2View")
       
       try:
           selected_languages = [str(lang.id) for lang in form.cleaned_data['languages']]
           logger.debug(f"Selected languages: {selected_languages}")
           
           self.request.session['dbdint:interpreter_registration_step2'] = {
               'languages': selected_languages
           }
           logger.info("Session data saved successfully")
           
       except Exception as e:
           logger.error(f"Error saving session data: {str(e)}")
           messages.error(self.request, 'An error occurred while saving your information.')
           return self.form_invalid(form)
           
       return super().form_valid(form)

   def form_invalid(self, form):
       logger.warning("Form validation failed for InterpreterRegistrationStep2View")
       logger.debug(f"Form errors: {form.errors}")
       messages.error(self.request, 'Please correct the errors below.')
       return super().form_invalid(form)

   def get_initial(self):
       logger.info("Getting initial data for InterpreterRegistrationStep2View")
       initial = super().get_initial()
       
       try:
           step2_data = self.request.session.get('dbdint:interpreter_registration_step2')
           if step2_data and 'languages' in step2_data:
               initial['languages'] = [int(lang_id) for lang_id in step2_data['languages']]
               logger.debug(f"Retrieved initial languages data: {initial['languages']}")
       except Exception as e:
           logger.error(f"Error getting initial data: {str(e)}")
           
       return initial

   def get(self, request, *args, **kwargs):
       logger.info("GET request received for InterpreterRegistrationStep2View")
       return super().get(request, *args, **kwargs)

   def post(self, request, *args, **kwargs):
       logger.info("POST request received for InterpreterRegistrationStep2View")
       logger.debug(f"POST data: {request.POST}")
       return super().post(request, *args, **kwargs)







@method_decorator(never_cache, name='dispatch')
class InterpreterRegistrationStep3View(FormView):
   template_name = 'trad/auth/step3.html'
   form_class = InterpreterRegistrationForm3 
   success_url = reverse_lazy('dbdint:new_interpreter_dashboard')

   def get_context_data(self, **kwargs):
       logger.info("Getting context data for InterpreterRegistrationStep3View")
       context = super().get_context_data(**kwargs)
       context['current_step'] = 3
       context['states'] = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
            'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
            'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
            'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
            'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
            'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
            'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
            'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
            'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
        }
       logger.debug(f"Context data prepared with {len(context['states'])} states")
       return context

   def dispatch(self, request, *args, **kwargs):
       logger.info("Dispatch called for InterpreterRegistrationStep3View")
       step1_exists = 'dbdint:interpreter_registration_step1' in request.session
       step2_exists = 'dbdint:interpreter_registration_step2' in request.session
       
       if not all([step1_exists, step2_exists]):
           logger.warning("Previous steps data missing")
           messages.error(request, 'Please complete previous steps first.')
           return redirect('dbdint:interpreter_registration_step1')
       return super().dispatch(request, *args, **kwargs)

   def form_valid(self, form):
       logger.info("Form validation successful")
       try:
           step1_data = self.request.session['dbdint:interpreter_registration_step1']
           step2_data = self.request.session['dbdint:interpreter_registration_step2']
           
           # Création de l'utilisateur
           user = User.objects.create_user(
               username=step1_data['username'],
               email=step1_data['email'],
               password=step1_data['password'],
               first_name=step1_data['first_name'],
               last_name=step1_data['last_name'],
               phone=step1_data['phone'],
               role='INTERPRETER'
           )
           logger.info(f"User created: {user.email}")

           # Création de l'interprète
           interpreter = form.save(commit=False)
           interpreter.user = user
           interpreter.save()
           
           for language_id in step2_data['languages']:
               interpreter.languages.add(language_id)
           
           # Création du contrat
           otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
           contract = InterpreterContractSignature(
               user=user,
               interpreter=interpreter,
               interpreter_name=f"{user.first_name} {user.last_name}",
               interpreter_email=user.email,
               interpreter_phone=user.phone,
               interpreter_address=f"{interpreter.address}, {interpreter.city}, {interpreter.state} {interpreter.zip_code}",
               token=str(uuid.uuid4()),
               otp_code=otp_code,
           )
           contract.save()
           logger.info(f"Contract created for interpreter: {interpreter.id}, token: {contract.token}")
           
           # Envoi de l'email avec le contrat
           self.send_contract_email(user, interpreter, contract)
           
           del self.request.session['dbdint:interpreter_registration_step1']
           del self.request.session['dbdint:interpreter_registration_step2']

           login(self.request, user)
           messages.success(self.request, 'Your interpreter account has been created successfully! Please check your email to sign the agreement contract.')
           return super().form_valid(form)

       except Exception as e:
           logger.error(f"Registration error: {str(e)}", exc_info=True)
           messages.error(self.request, 'An error occurred while creating your account.')
           return redirect('dbdint:interpreter_registration_step1')

   def send_contract_email(self, user, interpreter, contract):
        """Sends the contract email to the interpreter with anti-spam optimization."""
        try:
            # Création d'un identifiant unique pour ce message
            message_id = f"<contract-{contract.id}-{uuid.uuid4()}@{socket.gethostname()}>"
            
            # Construction de l'URL absolue pour le lien de vérification
            verification_url = self.request.build_absolute_uri(
                reverse('dbdint:contract_verification', kwargs={'token': contract.token})
            )
            
            # Préparation des données pour le template
            context = {
                'interpreter_name': f"{user.first_name} {user.last_name}",
                'token': contract.token,
                'otp_code': contract.otp_code,
                'verification_url': verification_url,  # Passez l'URL complète au template
                'email': user.email  # Pour le lien de désabonnement
            }
            
            # Rendu du template HTML
            html_message = render_to_string('notifmail/esign_notif.html', context)
            plain_message = strip_tags(html_message)
            
            # Ligne d'objet en anglais - éviter les formulations qui déclenchent les filtres anti-spam
            subject = f"Your JH Bridge Interpreter Agreement - Signature Required"
            
            # Format professionnel pour l'adresse expéditeur
            from_email = f"JH Bridge Contracts <contracts@jhbridgetranslation.com>"
            
            # Création de l'email avec du texte brut comme corps principal
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[user.email],
                reply_to=['support@jhbridgetranslation.com']
            )
            
            # Ajout de la version HTML comme alternative
            email.attach_alternative(html_message, "text/html")
            
            # En-têtes optimisés pour la délivrabilité
            email.extra_headers = {
                # En-têtes d'avant
                'Message-ID': message_id,
                'X-Entity-Ref-ID': str(contract.token),
                'X-Mailer': 'JHBridge-ContractMailer/1.0',
                'X-Contact-ID': str(user.id),
                'List-Unsubscribe': f'<mailto:unsubscribe@jhbridgetranslation.com?subject=Unsubscribe-{user.email}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'Precedence': 'bulk',
                'Auto-Submitted': 'auto-generated',
                'Feedback-ID': f'contract-{contract.id}:{user.id}:jhbridge:{int(time.time())}'
            }
            
            # Envoi de l'email
            email.send(fail_silently=False)
            
            logger.info(f"Contract agreement email sent to: {user.email} with Message-ID: {message_id}")
            
        except Exception as e:
            logger.error(f"Error sending contract email: {str(e)}", exc_info=True)

   def form_invalid(self, form):
       logger.warning(f"Form validation failed: {form.errors}")
       messages.error(self.request, 'Please correct the errors below.')
       return super().form_invalid(form)


class InterpreterDashboardView(LoginRequiredMixin, UserPassesTestMixin,TemplateView):
    template_name = 'trad/home.html'
    
    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer l'interprète
        interpreter = self.request.user.interpreter_profile
        
        # Période pour les statistiques
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Statistiques générales
        context['stats'] = {
            'pending_assignments': Assignment.objects.filter(
                interpreter=interpreter, 
                status='PENDING'
            ).count(),
            'upcoming_assignments': Assignment.objects.filter(
                interpreter=interpreter,
                status='CONFIRMED',
                start_time__gte=timezone.now()
            ).count(),
            'completed_assignments': Assignment.objects.filter(
                interpreter=interpreter,
                status='COMPLETED',
                completed_at__gte=thirty_days_ago
            ).count(),
            'total_earnings': Payment.objects.filter(
                assignment__interpreter=interpreter,
                payment_type='INTERPRETER_PAYMENT',
                status='COMPLETED',
                payment_date__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
        }
        
        # Missions du jour
        today = timezone.now().date()
        context['today_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__date=today,
            status__in=['CONFIRMED', 'IN_PROGRESS']
        ).order_by('start_time')
        
        # Prochaines missions
        context['upcoming_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='CONFIRMED',
            start_time__gt=timezone.now()
        ).order_by('start_time')[:5]
        
        # Derniers paiements
        context['recent_payments'] = Payment.objects.filter(
            assignment__interpreter=interpreter,
            payment_type='INTERPRETER_PAYMENT'
        ).order_by('-payment_date')[:5]
        
        # Notifications non lues
        context['unread_notifications'] = Notification.objects.filter(
            recipient=self.request.user,
            read=False
        ).order_by('-created_at')[:5]
        
        # Statistiques de performance
        assignments_completed = Assignment.objects.filter(
            interpreter=interpreter,
            status='COMPLETED'
        )
        
        context['performance'] = {
            'total_hours': sum((a.end_time - a.start_time).total_seconds() / 3600 
                             for a in assignments_completed),
            'average_rating': assignments_completed.aggregate(
                avg_rating=Avg('assignmentfeedback__rating')
            )['avg_rating'] or 0,
            'completion_rate': (
                assignments_completed.count() / 
                Assignment.objects.filter(interpreter=interpreter).count() * 100
                if Assignment.objects.filter(interpreter=interpreter).exists() 
                else 0
            )
        }
        
        return context
    
    
    
# views.py


class InterpreterSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trad/settings.html'
    
    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_notification_preferences(self):
        try:
            return NotificationPreference.objects.get(user=self.request.user)
        except NotificationPreference.DoesNotExist:
            return NotificationPreference.objects.create(
                user=self.request.user,
                email_quote_updates=True,
                email_assignment_updates=True,
                email_payment_updates=True,
                sms_enabled=False,
                quote_notifications=True,
                assignment_notifications=True,
                payment_notifications=True,
                system_notifications=True,
                notification_frequency='immediate',
                preferred_language=None
            )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # S'assure que les préférences de notification existent
        notification_preference = self.get_notification_preferences()
        
        if self.request.POST:
            context['profile_form'] = InterpreterProfileForm(
                self.request.POST, 
                self.request.FILES,
                user=user,
                instance=user.interpreter_profile
            )
            context['notification_form'] = NotificationPreferenceForm(
                self.request.POST,
                instance=notification_preference
            )
            context['password_form'] = CustomPasswordtradChangeForm(user, self.request.POST)
        else:
            context['profile_form'] = InterpreterProfileForm(
                user=user,
                instance=user.interpreter_profile
            )
            context['notification_form'] = NotificationPreferenceForm(
                instance=notification_preference
            )
            context['password_form'] = CustomPasswordtradChangeForm(user)
        
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        action = request.POST.get('action')
        
        if action == 'update_profile':
            profile_form = context['profile_form']
            if profile_form.is_valid():
                profile = profile_form.save(commit=False)
                user = request.user
                
                # Mise à jour des informations utilisateur
                user.first_name = profile_form.cleaned_data['first_name']
                user.last_name = profile_form.cleaned_data['last_name']
                user.email = profile_form.cleaned_data['email']
                user.phone_number = profile_form.cleaned_data['phone_number']
                user.save()
                
                # Mise à jour des informations bancaires
                profile.bank_name = profile_form.cleaned_data['bank_name']
                profile.account_holder_name = profile_form.cleaned_data['account_holder']
                profile.account_number = profile_form.cleaned_data['account_number']
                profile.routing_number = profile_form.cleaned_data['routing_number']
                
                profile.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('dbdint:interpreter_settings')
                
        elif action == 'update_notifications':
            notification_form = context['notification_form']
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Notification preferences updated successfully!')
                return redirect('dbdint:interpreter_settings')
                
        elif action == 'change_password':
            password_form = context['password_form']
            if password_form.is_valid():
                password_form.save()
                messages.success(request, 'Password changed successfully!')
                return redirect('dbdint:interpreter_settings')
        
        return self.render_to_response(context)
    
# views.py


class NotificationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Notification
    template_name = 'trad/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 15

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Grouper les notifications par catégorie
        context['unread_notifications'] = self.get_queryset().filter(read=False)
        context['quote_notifications'] = self.get_queryset().filter(
            Q(type='QUOTE_REQUEST') | Q(type='QUOTE_READY')
        )
        context['assignment_notifications'] = self.get_queryset().filter(
            Q(type='ASSIGNMENT_OFFER') | Q(type='ASSIGNMENT_REMINDER')
        )
        context['payment_notifications'] = self.get_queryset().filter(
            type='PAYMENT_RECEIVED'
        )
        context['system_notifications'] = self.get_queryset().filter(
            type='SYSTEM'
        )
        
        return context

@require_POST
def mark_notification_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@require_POST
def mark_all_notifications_as_read(request):
    Notification.objects.filter(
        recipient=request.user,
        read=False
    ).update(read=True)
    return JsonResponse({'status': 'success'})


# views.py

class InterpreterScheduleView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trad/schedule.html'

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interpreter = self.request.user.interpreter_profile

        # Récupérer la date actuelle
        now = timezone.now()
        
        # Prochaines missions (limitées à 5)
        context['upcoming_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status__in=['CONFIRMED', 'ASSIGNED'],
            start_time__gte=now
        ).order_by('start_time')[:5]

        # Missions en cours
        context['current_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='IN_PROGRESS'
        )

        # Statistiques de la semaine
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        weekly_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__range=(week_start, week_end),
            status__in=['CONFIRMED', 'IN_PROGRESS', 'COMPLETED']
        )

        context['weekly_stats'] = {
            'total_assignments': weekly_assignments.count(),
            'total_hours': sum(
                (a.end_time - a.start_time).total_seconds() / 3600 
                for a in weekly_assignments
            ),
            'earnings': sum(a.total_interpreter_payment or 0 for a in weekly_assignments)
        }

        return context

def get_calendar_assignments(request):
    """Vue API pour récupérer les missions pour le calendrier"""
    if not request.user.is_authenticated or request.user.role != 'INTERPRETER':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    start = request.GET.get('start')
    end = request.GET.get('end')
    interpreter = request.user.interpreter_profile

    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__range=[start, end]
    ).select_related('client', 'service_type')

    events = []
    status_colors = {
        'PENDING': '#FFA500',    # Orange
        'ASSIGNED': '#4299e1',   # Bleu clair
        'CONFIRMED': '#48bb78',  # Vert
        'IN_PROGRESS': '#805ad5', # Violet
        'COMPLETED': '#718096',  # Gris
        'CANCELLED': '#f56565',  # Rouge
        'NO_SHOW': '#ed8936',    # Orange foncé
    }

    for assignment in assignments:
        events.append({
            'id': assignment.id,
            'title': f"{assignment.client.full_name} - {assignment.service_type.name}",
            'start': assignment.start_time.isoformat(),
            'end': assignment.end_time.isoformat(),
            'backgroundColor': status_colors[assignment.status],
            'borderColor': status_colors[assignment.status],
            'extendedProps': {
                'status': assignment.status,
                'location': assignment.location,
                'city': assignment.city,
                'languages': f"{assignment.source_language.name} → {assignment.target_language.name}",
                'rate': float(assignment.interpreter_rate),
                'hours': (assignment.end_time - assignment.start_time).total_seconds() / 3600,
                'total_payment': float(assignment.total_interpreter_payment or 0),
                'special_requirements': assignment.special_requirements or 'None'
            }
        })

    return JsonResponse(events, safe=False)





class AssignmentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'trad/assignment.html'
    context_object_name = 'assignments'

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_queryset(self):
        return Assignment.objects.filter(
            interpreter=self.request.user.interpreter_profile
        ).order_by('start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interpreter = self.request.user.interpreter_profile
        now = timezone.now()
        
        # Assignments en attente de confirmation (PENDING)
        context['pending_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='PENDING'
        ).order_by('start_time')
        
        # Assignments confirmés à venir
        context['upcoming_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='CONFIRMED',
            start_time__gt=now
        ).order_by('start_time')
        
        # Assignments en cours
        context['in_progress_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='IN_PROGRESS'
        ).order_by('start_time')
        
        # Assignments terminés (derniers 30 jours)
        thirty_days_ago = now - timedelta(days=30)
        context['completed_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='COMPLETED',
            completed_at__gte=thirty_days_ago
        ).order_by('-completed_at')
        
        return context






# Définition du fuseau horaire du Massachusetts (Boston)
TZ_BOSTON = pytz.timezone('America/New_York')

def generate_ics_file(assignment):
    """Génère le fichier ICS pour un rendez-vous d'interprétation."""
    cal = Calendar()
    cal.add('prodid', '-//JHBRIDGE//Interpretation Assignment//EN')
    cal.add('version', '2.0')
    
    event = Event()
    event.add('summary', f'Interpretation Assignment at {assignment.location}')
    
    # Conversion en heure locale de Boston
    dtstart = timezone.localtime(assignment.start_time, TZ_BOSTON)
    dtend = timezone.localtime(assignment.end_time, TZ_BOSTON)
    
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', datetime.now(pytz.UTC))
    event.add('created', datetime.now(pytz.UTC))
    event.add('uid', f'assignment-{assignment.id}@jhbridge.com')
    event.add('status', 'CONFIRMED')
    event.add('location', f"{assignment.location}, {assignment.city}, {assignment.state}")

    # Alarmes
    alarm1 = Alarm()
    alarm1.add('action', 'DISPLAY')
    alarm1.add('description', 'Reminder: You have an interpretation assignment in 2 days')
    alarm1.add('trigger', timedelta(days=-2))
    event.add_component(alarm1)
    
    alarm2 = Alarm()
    alarm2.add('action', 'DISPLAY')
    alarm2.add('description', 'Reminder: You have an interpretation assignment tomorrow')
    alarm2.add('trigger', timedelta(hours=-24))
    event.add_component(alarm2)
    
    alarm3 = Alarm()
    alarm3.add('action', 'DISPLAY')
    alarm3.add('description', 'Reminder: Interpretation assignment starting in 2 hours')
    alarm3.add('trigger', timedelta(hours=-2))
    event.add_component(alarm3)
    
    alarm4 = Alarm()
    alarm4.add('action', 'DISPLAY')
    alarm4.add('description', 'Reminder: Interpretation assignment starting in 30 minutes')
    alarm4.add('trigger', timedelta(minutes=-30))
    event.add_component(alarm4)
    
    cal.add_component(event)
    return cal.to_ical()

def send_completion_email(assignment):
    """Envoie un email de confirmation de complétion à l'interprète."""
    subject = 'Assignment Completion Confirmation - JHBRIDGE'
    
    duration = assignment.end_time - assignment.start_time
    hours = duration.total_seconds() / 3600
    total_payment = assignment.total_interpreter_payment
    
    # Conversion en heure locale Boston
    start_local = timezone.localtime(assignment.start_time, TZ_BOSTON)
    end_local = timezone.localtime(assignment.end_time, TZ_BOSTON)
    completed_local = timezone.localtime(assignment.completed_at, TZ_BOSTON) if assignment.completed_at else None

    context = {
        'interpreter_name': assignment.interpreter.user.get_full_name(),
        'assignment_id': assignment.id,
        'start_time': start_local.strftime('%B %d, %Y at %I:%M %p'),
        'end_time': end_local.strftime('%I:%M %p'),
        'location': assignment.location,
        'city': assignment.city,
        'state': assignment.state,
        'service_type': assignment.service_type.name,
        'source_language': assignment.source_language.name,
        'target_language': assignment.target_language.name,
        'interpreter_rate': assignment.interpreter_rate,
        'duration_hours': round(hours, 2),
        'total_payment': total_payment,
        'completed_at': completed_local.strftime('%B %d, %Y at %I:%M %p') if completed_local else '',
        'minimum_hours': assignment.minimum_hours
    }
    
    email_html = render_to_string('emails/assignment_completion.html', context)
    
    email = EmailMessage(
        subject=subject,
        body=email_html,
        from_email='noreply@jhbridge.com',
        to=[assignment.interpreter.user.email],
    )
    
    email.extra_headers = {
        'Message-ID': make_msgid(domain='jhbridge.com'),
        'X-Entity-Ref-ID': str(uuid.uuid4()),
    }
    
    email.content_subtype = "html"
    return email.send()

def send_confirmation_email(assignment):
    """Envoie l'email de confirmation avec le fichier ICS."""
    subject = 'Assignment Confirmation - JHBRIDGE'
    
    # Conversion en heure locale Boston
    start_local = timezone.localtime(assignment.start_time, TZ_BOSTON)
    end_local = timezone.localtime(assignment.end_time, TZ_BOSTON)
    
    context = {
        'interpreter_name': assignment.interpreter.user.get_full_name(),
        'assignment_id': assignment.id,
        'start_time': start_local.strftime('%B %d, %Y at %I:%M %p'),
        'end_time': end_local.strftime('%I:%M %p'),
        'location': assignment.location,
        'city': assignment.city,
        'state': assignment.state,
        'service_type': assignment.service_type.name,
        'source_language': assignment.source_language.name,
        'target_language': assignment.target_language.name,
        'interpreter_rate': assignment.interpreter_rate,
        'special_requirements': assignment.special_requirements
    }
    
    email_html = render_to_string('emails/assignment_confirmation.html', context)
    
    email = EmailMessage(
        subject=subject,
        body=email_html,
        from_email='noreply@jhbridge.com',
        to=[assignment.interpreter.user.email],
    )
    
    email.extra_headers = {
        'Message-ID': make_msgid(domain='jhbridge.com'),
        'X-Entity-Ref-ID': str(uuid.uuid4()),
    }
    
    email.content_subtype = "html"
    
    # Génération du fichier ICS
    ics_content = generate_ics_file(assignment)
    email.attach('appointment.ics', ics_content, 'text/calendar')
    
    return email.send()

def send_admin_notification_email(assignment):
    """Envoie un email aux admins lorsque l'interprète accepte l'assignement."""
    admin_users = User.objects.filter(role='ADMIN', is_active=True)
    if not admin_users.exists():
        return False
        
    subject = f'Interpreter Accepted Assignment - ID: {assignment.id}'
    
    start_local = timezone.localtime(assignment.start_time, TZ_BOSTON)
    end_local = timezone.localtime(assignment.end_time, TZ_BOSTON)
    
    context = {
        'interpreter_name': assignment.interpreter.user.get_full_name(),
        'interpreter_email': assignment.interpreter.user.email,
        'interpreter_phone': assignment.interpreter.user.phone,
        'assignment_id': assignment.id,
        'start_time': start_local.strftime('%B %d, %Y at %I:%M %p'),
        'end_time': end_local.strftime('%I:%M %p'),
        'location': assignment.location,
        'city': assignment.city,
        'state': assignment.state,
        'service_type': assignment.service_type.name,
        'source_language': assignment.source_language.name,
        'target_language': assignment.target_language.name,
        'interpreter_rate': assignment.interpreter_rate,
        'special_requirements': assignment.special_requirements
    }
    
    email_html = render_to_string('emails/admin_assignment_notification.html', context)
    
    email = EmailMessage(
        subject=subject,
        body=email_html,
        from_email='noreply@jhbridge.com',
        to=[admin.email for admin in admin_users],
    )
    
    email.extra_headers = {
        'Message-ID': make_msgid(domain='jhbridge.com'),
        'X-Entity-Ref-ID': str(uuid.uuid4()),
    }
    
    email.content_subtype = "html"
    
    ics_content = generate_ics_file(assignment)
    email.attach('admin_appointment.ics', ics_content, 'text/calendar')
    
    return email.send()

def send_admin_rejection_email(assignment, old_interpreter):
    """Envoie un email aux admins lorsque l'interprète refuse une mission."""
    admin_users = User.objects.filter(role='ADMIN', is_active=True)
    if not admin_users.exists():
        return False
    
    subject = f'ACTION REQUIRED: Assignment #{assignment.id} Rejected by Interpreter'
    
    context = {
        'assignment_id': assignment.id,
        'interpreter_name': old_interpreter.user.get_full_name(),
        'interpreter_email': old_interpreter.user.email,
        'client_name': assignment.client.company_name,
        'start_time': timezone.localtime(assignment.start_time, TZ_BOSTON).strftime("%B %d, %Y at %I:%M %p"),
        'end_time': timezone.localtime(assignment.end_time, TZ_BOSTON).strftime("%I:%M %p"),
        'location': assignment.location,
        'city': assignment.city,
        'state': assignment.state,
        'service_type': assignment.service_type.name,
        'source_language': assignment.source_language.name,
        'target_language': assignment.target_language.name,
    }
    
    html_message = render_to_string('emails/assignment_rejection_notification.html', context)
    
    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin.email for admin in admin_users],
    )
    
    email.extra_headers = {
        'Message-ID': make_msgid(domain='jhbridge.com'),
        'X-Entity-Ref-ID': str(uuid.uuid4()),
    }
    
    email.content_subtype = "html"
    return email.send()

@require_POST
@login_required
def accept_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_confirmed():
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    conflicting_assignments = Assignment.objects.filter(
        interpreter=request.user.interpreter_profile,
        status__in=['CONFIRMED', 'IN_PROGRESS'],
        start_time__lt=assignment.end_time,
        end_time__gt=assignment.start_time
    ).exists()
    
    if conflicting_assignments:
        return JsonResponse({
            'error': 'Schedule conflict',
            'message': 'You already have an assignment during this time period'
        }, status=400)
    
    if assignment.confirm():
        try:
            send_confirmation_email(assignment)
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
            
        try:
            send_admin_notification_email(assignment)
        except Exception as e:
            print(f"Error sending admin notification email: {str(e)}")
            
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Could not confirm assignment'}, status=400)

class AssignmentDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        
        if assignment.interpreter != request.user.interpreter_profile:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        data = {
            'id': assignment.id,
            'start_time': assignment.start_time.isoformat(),
            'end_time': assignment.end_time.isoformat(),
            'location': assignment.location,
            'city': assignment.city,
            'state': assignment.state,
            'zip_code': assignment.zip_code,
            'service_type': assignment.service_type.name,
            'source_language': assignment.source_language.name,
            'target_language': assignment.target_language.name,
            'interpreter_rate': str(assignment.interpreter_rate),
            'minimum_hours': assignment.minimum_hours,
            'status': assignment.status,
            'special_requirements': assignment.special_requirements or '',
            'notes': assignment.notes or '',
            'can_start': assignment.can_be_started(),
            'can_complete': assignment.can_be_completed(),
            'can_cancel': assignment.can_be_cancelled()
        }
        
        return JsonResponse(data)

@require_POST
@login_required
def reject_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_cancelled():
        return JsonResponse({'error': 'Invalid status'}, status=400)
        
    old_interpreter = assignment.cancel()
    if old_interpreter:
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Could not reject assignment'}, status=400)

@require_POST
@login_required
def start_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_started():
        return JsonResponse({'error': 'Invalid status'}, status=400)

    if timezone.now() + timedelta(minutes=15) < assignment.start_time:
        return JsonResponse({
            'error': 'Too early',
            'message': 'You can only start the assignment 15 minutes before the scheduled time'
        }, status=400)

    if assignment.start():
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Could not start assignment'}, status=400)

@require_POST
@login_required
def complete_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_completed():
        return JsonResponse({'error': 'Invalid status'}, status=400)
        
    if assignment.complete():
        try:
            send_completion_email(assignment)
        except Exception as e:
            print(f"Error sending completion email: {str(e)}")
            
        return JsonResponse({
            'status': 'success',
            'payment': str(assignment.total_interpreter_payment)
        })
    
    return JsonResponse({'error': 'Could not complete assignment'}, status=400)

@login_required
def get_assignment_counts(request):
    if request.user.role != 'INTERPRETER':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    interpreter = request.user.interpreter_profile
    
    counts = {
        'pending': Assignment.objects.filter(interpreter=interpreter, status='PENDING').count(),
        'upcoming': Assignment.objects.filter(interpreter=interpreter, status='CONFIRMED').count(),
        'in_progress': Assignment.objects.filter(interpreter=interpreter, status='IN_PROGRESS').count(),
        'completed': Assignment.objects.filter(interpreter=interpreter, status='COMPLETED').count()
    }
    
    return JsonResponse(counts)

@require_POST
@login_required
def mark_assignments_as_read(request):
    interpreter = request.user.interpreter_profile
    AssignmentNotification.objects.filter(
        interpreter=interpreter,
        is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_assignments_count(request):
    if request.user.role != 'INTERPRETER':
        return JsonResponse({'count': 0})
        
    count = AssignmentNotification.get_unread_count(request.user.interpreter_profile)
    return JsonResponse({'count': count})
# views.py


class TranslatorEarningsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trad/earnings.html'

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interpreter = self.request.user.interpreter_profile
        now = timezone.now()

        # Statistiques générales
        all_payments = Payment.objects.filter(
            assignment__interpreter=interpreter,
            payment_type='INTERPRETER_PAYMENT'
        )

        # Statistiques du mois en cours
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_payments = all_payments.filter(payment_date__gte=current_month_start)

        context['current_month'] = {
            'earnings': current_month_payments.filter(status='COMPLETED').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'pending': current_month_payments.filter(status='PENDING').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'assignments': current_month_payments.count(),
        }

        # Statistiques des 12 derniers mois
        twelve_months_ago = now - timedelta(days=365)
        monthly_earnings = all_payments.filter(
            payment_date__gte=twelve_months_ago,
            status='COMPLETED'
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')

        context['monthly_earnings'] = monthly_earnings

        # Statistiques annuelles
        yearly_earnings = all_payments.filter(
            status='COMPLETED'
        ).annotate(
            year=TruncYear('payment_date')
        ).values('year').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-year')

        context['yearly_earnings'] = yearly_earnings

        # Paiements récents
        context['recent_payments'] = all_payments.select_related(
            'assignment'
        ).order_by('-payment_date')[:10]

        # Paiements en attente
        context['pending_payments'] = all_payments.filter(
            status='PENDING'
        ).select_related('assignment').order_by('-payment_date')

        # Statistiques globales
        context['total_stats'] = {
            'lifetime_earnings': all_payments.filter(status='COMPLETED').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'total_assignments': all_payments.filter(status='COMPLETED').count(),
            'pending_amount': all_payments.filter(status='PENDING').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'average_payment': all_payments.filter(
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00') / (
                all_payments.filter(status='COMPLETED').count() or 1
            )
        }

        # Liste des années pour le filtre
        context['years'] = yearly_earnings.values_list('year', flat=True)

        return context



@require_GET
def get_earnings_data(request, year=None):
    """Vue API pour obtenir les données des gains pour les graphiques"""
    interpreter = request.user.interpreter_profile
    payments = Payment.objects.filter(
        assignment__interpreter=interpreter,
        payment_type='INTERPRETER_PAYMENT'
    )

    if year:
        payments = payments.filter(payment_date__year=year)

    # Données mensuelles
    monthly_data = payments.filter(
        status='COMPLETED'
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')

    # Formatter les données pour les graphiques
    chart_data = {
        'labels': [],
        'earnings': [],
        'assignments': []
    }

    for data in monthly_data:
        chart_data['labels'].append(data['month'].strftime('%B %Y'))
        chart_data['earnings'].append(float(data['total']))
        chart_data['assignments'].append(data['count'])

    return JsonResponse(chart_data)



####################################################newupdate####################3
@login_required
def dashboard_view(request):
    """
    Vue principale du dashboard.
    Vérifie que l'utilisateur a complété son inscription,
    puis vérifie qu'il possède un profil d'interprète,
    calcule les statistiques et prépare les données des missions.
    """
    # Vérification si l'inscription est complète
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    
    if not hasattr(request.user, 'interpreter_profile'):
        return render(request, 'error.html', {
            'message': 'Access denied. Interpreter profile required.'
        })

    interpreter = request.user.interpreter_profile

    try:
        # Calcul des statistiques
        stats = get_interpreter_stats(interpreter)

        # Récupération des missions en attente et confirmées
        pending_assignments = get_pending_assignments(interpreter)
        confirmed_assignments = get_confirmed_assignments(interpreter)

        # Préparation des données pour l'affichage
        pending_data = prepare_assignments_data(request, pending_assignments, 'PENDING')
        confirmed_data = prepare_assignments_data(request, confirmed_assignments, 'CONFIRMED')

        context = {
            'stats': stats,
            'pending_assignments': pending_data,
            'confirmed_assignments': confirmed_data
        }

        return render(request, 'interpreter/int_main.html', context)

    except Exception as e:
        return render(request, 'error.html', {
            'message': f'An error occurred: {str(e)}'
        })


def get_interpreter_stats(interpreter):
    """
    Calcule les statistiques de l'interprète pour la semaine en cours.
    - Gains de la semaine (missions complétées)
    - Nombre de missions en attente
    - Nombre de missions confirmées et futures
    """
    # Obtenir le début et la fin de la semaine courante
    today = timezone.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)

    # Calculer les gains de la semaine
    weekly_earnings = Assignment.objects.filter(
        interpreter=interpreter,
        status='COMPLETED',
        completed_at__range=(start_of_week, end_of_week)
    ).aggregate(total=Sum('total_interpreter_payment'))['total']

    pending_count = Assignment.objects.filter(
        interpreter=interpreter,
        status='PENDING'
    ).count()

    upcoming_count = Assignment.objects.filter(
        interpreter=interpreter,
        status='CONFIRMED',
        start_time__gt=timezone.now()
    ).count()

    return {
        'weekly_earnings': '-' if weekly_earnings is None else round(weekly_earnings, 2),
        'earnings_info': 'Click on Payments for more details',  # Message d'information
        'pending_missions': pending_count,
        'upcoming_missions': upcoming_count
    }


def get_pending_assignments(interpreter):
    """
    Récupère les missions en attente avec les relations nécessaires.
    """
    return Assignment.objects.filter(
        interpreter=interpreter,
        status='PENDING'
    ).select_related(
        'service_type',
        'source_language',
        'target_language'
    ).order_by('start_time')


def get_confirmed_assignments(interpreter):
    """
    Récupère les missions confirmées avec les relations nécessaires.
    """
    return Assignment.objects.filter(
        interpreter=interpreter,
        status='CONFIRMED'
    ).select_related(
        'service_type',
        'source_language',
        'target_language'
    ).order_by('start_time')


def prepare_assignments_data(request, assignments, status_type):
    """
    Prépare les données des missions pour l'affichage.
    Ajoute les URLs d'action, et fournit les informations de date complète.
    """
    mixin = AssignmentAdminMixin()
    assignments_data = []

    for assignment in assignments:
        # Génération des tokens ou URLs d'action selon le type de statut
        action_urls = {}
        if status_type == 'PENDING':
            accept_token = mixin.generate_assignment_token(assignment.id, 'accept')
            decline_token = mixin.generate_assignment_token(assignment.id, 'decline')
            action_urls = {
                'accept': f"/assignments/accept/{accept_token}/",
                'decline': f"/assignments/decline/{decline_token}/"
            }
        elif status_type == 'CONFIRMED':
            action_urls = {
                'complete': f"/assignments/{assignment.id}/complete/"
            }

        # Conversion des heures en fuseau horaire de Boston
        start_time = assignment.start_time.astimezone(BOSTON_TZ)
        end_time = assignment.end_time.astimezone(BOSTON_TZ)

        assignment_data = {
            # Informations principales
            'main_info': {
                'id': assignment.id,
                'client_name': assignment.client.company_name if assignment.client else assignment.client_name,
                'address': f"{assignment.location}, {assignment.city}",
                'languages': f"{assignment.source_language.name} → {assignment.target_language.name}",
                'status': status_type,
                'interpreter_rate': assignment.interpreter_rate,
                # Pour l'affichage de l'heure seule
                'start_time': start_time,
                'end_time': end_time,
                # Pour l'affichage complet (date + heure)
                'start_datetime': start_time,
                'end_datetime': end_time,
                'duration': f"{(end_time - start_time).total_seconds() / 3600:.1f} hours"
            },
            # Informations détaillées
            'detailed_info': {
                'special_requirements': assignment.special_requirements or "None",
                'client_phone': assignment.client_phone or "Not provided",
                'client_email': assignment.client_email or "Not provided",
                'total_amount': assignment.total_interpreter_payment,
                'service_type': assignment.service_type.name,
                'full_address': {
                    'location': assignment.location,
                    'city': assignment.city,
                    'state': assignment.state,
                    'zip_code': assignment.zip_code
                }
            },
            # URLs d'action
            'action_urls': action_urls
        }

        assignments_data.append(assignment_data)

    return assignments_data


@login_required
@require_POST
def mark_assignment_complete(request, assignment_id):
    """
    Vue pour marquer une mission comme complétée.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"=== TENTATIVE DE COMPLETION - ASSIGNMENT {assignment_id} ===")
    
    try:
        # Récupération de l'assignment
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            interpreter=request.user.interpreter_profile
        )
        logger.info(f"Assignment trouvé - Status: {assignment.status}")

        # Vérification de la possibilité de completion
        if not assignment.can_be_completed():
            logger.error("[ÉCHEC] Conditions de completion non remplies")
            logger.error(f"- Status actuel: {assignment.status}")
            return JsonResponse({
                'success': False,
                'message': 'Assignment cannot be completed.'
            }, status=400)

        # Initialisation du mixin
        mixin = AssignmentAdminMixin()
        old_status = assignment.status

        # Mise à jour du statut
        assignment.status = Assignment.Status.COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save()
        logger.info(f"Assignment {assignment_id} marqué comme complété")

        # Gestion des notifications et changements de statut via le mixin
        try:
            # Gestion des changements liés au statut (paiements, etc.)
            mixin.handle_status_change(request, assignment, old_status)
            logger.info("Status change handled successfully")

            # Envoi de l'email de completion
            email_sent = mixin.send_assignment_email(request, assignment, 'completed')
            if email_sent:
                logger.info("Email de completion envoyé avec succès")
            else:
                logger.warning("L'email de completion n'a pas pu être envoyé")
                
            # Gestion des notifications de changement de statut
            mixin.handle_status_change_notification(request, assignment, old_status)
            logger.info("Notifications de changement de statut envoyées")

        except Exception as e:
            logger.error(f"Erreur lors de la gestion des notifications: {str(e)}")
            # On continue malgré l'erreur de notification car l'assignment est déjà complété

        return JsonResponse({
            'success': True,
            'message': 'Assignment marked as completed successfully.'
        })

    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def calendar_view(request):
    """
    Vue pour afficher le calendrier des rendez-vous de l'interprète
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    # Vérifier si l'utilisateur a un profil d'interprète
    if not hasattr(request.user, 'interpreter_profile'):
        return render(request, 'error.html', {
            'message': 'Access denied. Interpreter profile required.'
        })
        

    interpreter = request.user.interpreter_profile

    # Récupérer le mois actuel ou le mois demandé dans les paramètres
    try:
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
    except ValueError:
        year = timezone.now().year
        month = timezone.now().month

    # Créer les dates de début et fin du mois
    start_date = timezone.datetime(year, month, 1)
    if month == 12:
        end_date = timezone.datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = timezone.datetime(year, month + 1, 1) - timedelta(days=1)

    # Récupérer toutes les missions du mois pour l'interprète
    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__date__range=[start_date, end_date]
    ).select_related(
        'client', 
        'source_language', 
        'target_language'
    ).order_by('start_time')

    # Récupération des prochaines missions (aujourd'hui et à venir)
    now = timezone.now()
    upcoming_assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__gte=now
    ).select_related(
        'client', 
        'source_language', 
        'target_language'
    ).order_by('start_time')[:5]  # Limite aux 5 prochaines missions

    # Grouper les missions par jour avec leur statut
    assignments_by_date = {}
    for assignment in assignments:
        date_key = assignment.start_time.date()
        if date_key not in assignments_by_date:
            assignments_by_date[date_key] = {
                'missions': [],
                'status_count': {status[0]: 0 for status in Assignment.Status.choices}
            }
        
        # Préparation des informations détaillées pour chaque mission
        mission_details = {
            'id': assignment.id,
            'start_time': assignment.start_time,
            'end_time': assignment.end_time,
            'status': assignment.status,
            'client_info': {
                'name': assignment.get_client_display(),
                'phone': assignment.client.phone if assignment.client else assignment.client_phone,
                'email': assignment.client.email if assignment.client else assignment.client_email
            },
            'location': {
                'address': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'zip_code': assignment.zip_code,
                'full_address': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}"
            },
            'languages': {
                'source': assignment.source_language.name,
                'target': assignment.target_language.name
            },
            'notes': assignment.notes,
            'special_requirements': assignment.special_requirements
        }
        
        assignments_by_date[date_key]['missions'].append(mission_details)
        assignments_by_date[date_key]['status_count'][assignment.status] += 1

    # Préparation des données pour les missions à venir
    upcoming_missions_details = []
    for assignment in upcoming_assignments:
        upcoming_mission = {
            'id': assignment.id,
            'start_time': assignment.start_time,
            'end_time': assignment.end_time,
            'status': assignment.status,
            'client_info': {
                'name': assignment.get_client_display(),
                'phone': assignment.client.phone if assignment.client else assignment.client_phone,
                'email': assignment.client.email if assignment.client else assignment.client_email
            },
            'location': {
                'address': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'zip_code': assignment.zip_code,
                'full_address': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}"
            },
            'languages': {
                'source': assignment.source_language.name,
                'target': assignment.target_language.name
            },
            'can_be_started': assignment.can_be_started(),
            'can_be_completed': assignment.can_be_completed(),
            'can_be_cancelled': assignment.can_be_cancelled()
        }
        upcoming_missions_details.append(upcoming_mission)

    # Récupérer les missions du jour actuel
    today = timezone.now().date()
    todays_assignments = []
    
    # Filtrer les missions pour aujourd'hui
    if today in assignments_by_date:
        todays_assignments = assignments_by_date[today]['missions']

    # Créer le contexte avec toutes les données nécessaires
    context = {
        'current_year': year,
        'current_month': month,
        'assignments_by_date': assignments_by_date,
        'upcoming_missions': upcoming_missions_details,
        'todays_assignments': todays_assignments,  # Ajout des missions du jour
        'statuses': Assignment.Status.choices,
        'today': today,
        'interpreter': interpreter,
        'current_time': timezone.now(),
        'has_appointments_today': len(todays_assignments) > 0  # Indicateur pour savoir s'il y a des missions aujourd'hui
    }

    return render(request, 'interpreter/int_calend.html', context)


@login_required
@require_http_methods(["GET"])
def calendar_data_api(request, year, month):
    """
    API pour récupérer les données du calendrier pour un mois spécifique
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    if not hasattr(request.user, 'interpreter_profile'):
        return JsonResponse({'error': 'Interpreter profile required'}, status=403)

    interpreter = request.user.interpreter_profile
    
    # Créer les dates de début et fin du mois
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # Récupérer toutes les missions du mois
    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__date__range=[start_date, end_date - timedelta(days=1)]
    ).values('start_time__date', 'status')

    # Organiser les données par date
    dates_data = {}
    for assignment in assignments:
        date_str = assignment['start_time__date'].isoformat()
        if date_str not in dates_data:
            dates_data[date_str] = {
                'has_missions': True,
                'mission_count': 1,
                'status_summary': {status[0]: 0 for status in Assignment.Status.choices}
            }
        else:
            dates_data[date_str]['mission_count'] += 1
        dates_data[date_str]['status_summary'][assignment['status']] += 1

    return JsonResponse({
        'dates': dates_data
    })

@login_required
@require_http_methods(["GET"])
def daily_missions_api(request, date_str):
    """
    API pour récupérer les missions d'une journée spécifique
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    if not hasattr(request.user, 'interpreter_profile'):
        return JsonResponse({'error': 'Interpreter profile required'}, status=403)

    interpreter = request.user.interpreter_profile
    
    try:
        # Convertir la date string en objet date
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # Récupérer les missions du jour
    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__date=target_date
    ).select_related(
        'client',
        'source_language',
        'target_language'
    )

    missions_data = []
    for assignment in assignments:
        missions_data.append({
            'id': assignment.id,
            'start_time': assignment.start_time.isoformat(),
            'end_time': assignment.end_time.isoformat(),
            'client_info': {
                'name': assignment.get_client_display(),
                'phone': assignment.client.phone if assignment.client else assignment.client_phone,
                'email': assignment.client.email if assignment.client else assignment.client_email
            },
            'location': {
                'address': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'zip_code': assignment.zip_code,
                'full_address': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}"
            },
            'languages': {
                'source': assignment.source_language.name,
                'target': assignment.target_language.name
            },
            'status': assignment.status,
            'can_be_started': assignment.can_be_started(),
            'can_be_completed': assignment.can_be_completed(),
            'can_be_cancelled': assignment.can_be_cancelled(),
            'notes': assignment.notes,
            'special_requirements': assignment.special_requirements
        })

    return JsonResponse({
        'date': date_str,
        'missions': missions_data
    })

def appointments_view(request):
    """
    Vue pour afficher la liste des rendez-vous
    """
    return render(request, 'interpreter/appointment.html')

@login_required
def stats_view(request):
    """
    Vue pour afficher les statistiques du dashboard de l'interprète
    """
    logger.info(f"Accessing stats view for user: {request.user.username}")

    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    # Vérifier si l'utilisateur a un profil d'interprète
    if not hasattr(request.user, 'interpreter_profile'):
        logger.error(f"User {request.user.username} does not have interpreter profile")
        return render(request, 'error.html', {
            'message': 'Access denied. Interpreter profile required.'
        })

    # Récupérer l'interprète connecté
    interpreter = request.user.interpreter_profile
    logger.info(f"Retrieved interpreter profile for user: {interpreter}")
    
    try:
        # Définir la période (par défaut le mois en cours)
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
        
        logger.info(f"Calculating stats for period: {start_of_month} to {today}")
        
        # Requêtes pour le mois en cours
        current_month_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__gte=start_of_month,
            start_time__lte=today
        )
        
        # Requêtes pour le mois précédent
        last_month_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__gte=last_month_start,
            start_time__lt=start_of_month
        )
        
        # Calcul des statistiques du mois en cours
        current_earnings = current_month_assignments.filter(
            status='COMPLETED'
        ).aggregate(
            total=Sum('total_interpreter_payment')
        )['total'] or Decimal('0')
        
        # Calcul des heures totales actuelles
        completed_assignments = current_month_assignments.filter(status='COMPLETED')
        total_hours = sum(
            (assignment.end_time - assignment.start_time).total_seconds() / 3600
            for assignment in completed_assignments
        )
        
        # Calcul des heures du mois précédent
        last_month_completed = last_month_assignments.filter(status='COMPLETED')
        last_month_hours = sum(
            (assignment.end_time - assignment.start_time).total_seconds() / 3600
            for assignment in last_month_completed
        )
        
        # Statistiques du mois précédent
        last_month_earnings = last_month_assignments.filter(
            status='COMPLETED'
        ).aggregate(
            total=Sum('total_interpreter_payment')
        )['total'] or Decimal('0')
        
        last_month_stats = last_month_assignments.aggregate(
            completed=Count('id', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status='CANCELLED')),
            no_show=Count('id', filter=Q(status='NO_SHOW'))
        )
        
        # Calcul des données pour les graphiques
        earnings_by_period = current_month_assignments.filter(
            status='COMPLETED'
        ).annotate(
            month=ExtractMonth('start_time'),
            year=ExtractYear('start_time')
        ).values('month', 'year').annotate(
            amount=Sum('total_interpreter_payment')
        ).order_by('year', 'month')

        # Préparation des données pour les graphiques
        earnings_data = [
            {
                'month': f"{item['year']}-{item['month']}",
                'amount': float(item['amount'])
            }
            for item in earnings_by_period
        ]
        
        # Statistiques des missions actuelles
        mission_stats = current_month_assignments.aggregate(
            completed=Count('id', filter=Q(status='COMPLETED')),
            cancelled=Count('id', filter=Q(status='CANCELLED')),
            no_show=Count('id', filter=Q(status='NO_SHOW'))
        )
        
        # Distribution des langues
        languages_distribution = current_month_assignments.filter(
            status='COMPLETED'
        ).values(
            'target_language__name'
        ).annotate(
            value=Count('id')
        ).order_by('-value')
        
        # Répartition des heures par jour avec gestion des erreurs
        hours_by_day = []
        days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for assignment in completed_assignments:
            day_index = assignment.start_time.weekday()
            duration = (assignment.end_time - assignment.start_time).total_seconds() / 3600
            
            # Chercher si le jour existe déjà dans hours_by_day
            day_entry = next(
                (item for item in hours_by_day if item['day'] == days_of_week[day_index]), 
                None
            )
            
            if day_entry:
                day_entry['hours'] += duration
            else:
                hours_by_day.append({
                    'day': days_of_week[day_index],
                    'hours': duration
                })
        
        # Trier les jours dans l'ordre
        hours_by_day.sort(key=lambda x: days_of_week.index(x['day']))

        # Remplir les jours manquants avec 0 heures
        existing_days = [entry['day'] for entry in hours_by_day]
        for day in days_of_week:
            if day not in existing_days:
                hours_by_day.append({'day': day, 'hours': 0})
        
        hours_by_day.sort(key=lambda x: days_of_week.index(x['day']))

        # Calcul des tendances
        earnings_trend = calculate_trend(current_earnings, last_month_earnings)
        hours_trend = calculate_trend(total_hours, last_month_hours)
        mission_trend = calculate_trend(
            mission_stats['completed'],
            last_month_stats.get('completed', 0)
        )

        context = {
            'total_earnings': current_earnings,
            'total_hours': round(total_hours, 1),
            'completed_missions': mission_stats['completed'],
            'earnings_trend': earnings_trend,
            'earnings_trend_abs': abs(earnings_trend),
            'hours_trend': hours_trend,
            'hours_trend_abs': abs(hours_trend),
            'mission_trend': mission_trend,
            'mission_trend_abs': abs(mission_trend),
            'mission_stats': {
                'completed_rate': calculate_percentage(mission_stats['completed'], sum(mission_stats.values())),
                'cancelled_rate': calculate_percentage(mission_stats['cancelled'], sum(mission_stats.values())),
                'no_show_rate': calculate_percentage(mission_stats['no_show'], sum(mission_stats.values())),
            },
            'earnings_data': json.dumps(earnings_data),
            'languages_data': json.dumps(list(languages_distribution)),
            'hours_data': json.dumps(hours_by_day),
        }
        
        logger.info("Successfully prepared context for template")
        return render(request, 'interpreter/stats.html', context)
        
    except Exception as e:
        logger.error(f"Error in stats_view: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return render(request, 'error.html', {
            'message': f'An error occurred while loading statistics: {str(e)}'
        })

def calculate_trend(current, previous):
    """
    Calcule le pourcentage d'évolution entre deux valeurs
    """
    if not previous:
        return 0
    try:
        return round(((current - previous) / previous) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return 0

def calculate_percentage(part, total):
    """
    Calcule le pourcentage d'une partie par rapport au total
    """
    if not total:
        return 0
    try:
        return round((part / total) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return 0
    
    
def earnings_data_api(request, period):
    """
    API pour récupérer les données de gains selon la période
    """
    if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
        return render(request, 'complete_registration.html', {
            'user': request.user
        })
    if not hasattr(request.user, 'interpreter_profile'):
        return JsonResponse({'error': 'Interpreter profile required'}, status=403)

    interpreter = request.user.interpreter_profile
    today = timezone.now()

    try:
        if period == 'week':
            start_date = today - timedelta(days=7)
            assignments = Assignment.objects.filter(
                interpreter=interpreter,
                start_time__gte=start_date,
                status='COMPLETED'
            ).annotate(
                day=ExtractDay('start_time')
            ).values('day').annotate(
                amount=Sum('total_interpreter_payment')
            ).order_by('day')

            data = [
                {
                    'day': (start_date + timedelta(days=i)).strftime('%a'),
                    'amount': 0
                } for i in range(7)
            ]

            for entry in assignments:
                day_index = (entry['day'] - start_date.day) % 7
                if 0 <= day_index < 7:
                    data[day_index]['amount'] = float(entry['amount'])

        elif period == 'month':
            start_date = today.replace(day=1)
            assignments = Assignment.objects.filter(
                interpreter=interpreter,
                start_time__year=today.year,
                start_time__month=today.month,
                status='COMPLETED'
            ).annotate(
                day=ExtractDay('start_time')
            ).values('day').annotate(
                amount=Sum('total_interpreter_payment')
            ).order_by('day')

            data = [
                {
                    'day': str(i),
                    'amount': 0
                } for i in range(1, 32)
            ]

            for entry in assignments:
                if 1 <= entry['day'] <= 31:
                    data[entry['day']-1]['amount'] = float(entry['amount'])

        else:  # year
            assignments = Assignment.objects.filter(
                interpreter=interpreter,
                start_time__year=today.year,
                status='COMPLETED'
            ).annotate(
                month=ExtractMonth('start_time')
            ).values('month').annotate(
                amount=Sum('total_interpreter_payment')
            ).order_by('month')

            data = [
                {
                    'month': (today.replace(month=i, day=1)).strftime('%b'),
                    'amount': 0
                } for i in range(1, 13)
            ]

            for entry in assignments:
                if 1 <= entry['month'] <= 12:
                    data[entry['month']-1]['amount'] = float(entry['amount'])

        return JsonResponse(data, safe=False)

    except Exception as e:
        logger.error(f"Error in earnings_data_api: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
    
    
class PaymentListView(ListView):
    model = Assignment
    template_name = 'interpreter/payment_list.html'
    context_object_name = 'assignments'
    
    
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has interpreter profile before proceeding"""
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not request.user.registration_complete:
        # Affichage de la page de complétion d'inscription
            return render(request, 'complete_registration.html', {
            'user': request.user
        })
        if not hasattr(request.user, 'interpreter_profile'):
            return render(request, 'error.html', {
                'message': 'Access denied. Interpreter profile required.'
            })
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Return assignments completed by the current interpreter"""
        # Get interpreter profile
        interpreter = self.request.user.interpreter_profile
        
        return Assignment.objects.filter(
            interpreter=interpreter,
            # Only show completed assignments
            status=Assignment.Status.COMPLETED
        ).order_by('-start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get interpreter profile
        interpreter = self.request.user.interpreter_profile
            
        # Get all completed assignments for the interpreter
        completed_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            status=Assignment.Status.COMPLETED
        )
        
        # Calculate date ranges
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Format date strings
        current_month_name = now.strftime('%B %Y')
        week_start_str = week_start.strftime('%b %d')
        week_end_str = week_end.strftime('%b %d, %Y')
        week_date_range = f"{week_start_str} - {week_end_str}"
        
        # This week's revenue
        weekly_revenue = completed_assignments.filter(
            start_time__gte=week_start
        ).aggregate(
            sum=Sum('total_interpreter_payment')
        )['sum'] or 0
        
        # This month's revenue
        monthly_revenue = completed_assignments.filter(
            start_time__gte=month_start
        ).aggregate(
            sum=Sum('total_interpreter_payment')
        )['sum'] or 0
        
        # Total revenue
        total_revenue = completed_assignments.aggregate(
            sum=Sum('total_interpreter_payment')
        )['sum'] or 0
        
        # Add revenue data to context
        context['weekly_revenue'] = weekly_revenue
        context['monthly_revenue'] = monthly_revenue
        context['total_revenue'] = total_revenue
        
        # Add date information
        context['current_month'] = current_month_name
        context['week_date_range'] = week_date_range
        
        # Payment statistics
        context['paid_count'] = completed_assignments.filter(is_paid=True).count()
        context['unpaid_count'] = completed_assignments.filter(
            Q(is_paid=False) | Q(is_paid=None)
        ).count()
        
        return context
    
#############################esignview



@method_decorator(never_cache, name='dispatch')
class ContractVerificationView(View):
    template_name_otp = 'signature_app/otp_signup.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, token=None, *args, **kwargs):
        logger.info(f"Contract verification attempted with token: {token}")
        
        if not token:
            logger.warning("No token provided in the URL")
            messages.error(request, 'Invalid verification link. No token was provided.')
            return render(request, self.template_name_error, {'error': 'No token provided'})
        
        try:
            # Recherche du contrat par token
            contract = get_object_or_404(InterpreterContractSignature, token=token)
            
            # Vérification de l'expiration du contrat
            if contract.is_expired():
                logger.warning(f"Expired contract token accessed: {token}")
                messages.error(request, 'This verification link has expired. Please contact support for assistance.')
                return render(request, self.template_name_error, {'error': 'Token expired'})
            
            # Vérification du statut du contrat
            if contract.status != 'PENDING':
                logger.warning(f"Non-pending contract accessed: {token}, status: {contract.status}")
                messages.warning(request, 'This contract has already been processed.')
                return render(request, self.template_name_error, {'error': 'Contract already processed'})
            
            # AJOUT : Marquer le lien comme accédé
            contract.status = 'LINK_ACCESSED'
            contract.save()
            
            # Génération du numéro d'accord
            current_year = timezone.now().year
            # Comptage des contrats de cette année pour obtenir un numéro séquentiel
            contract_count = InterpreterContractSignature.objects.filter(
                created_at__year=current_year
            ).count()
            
            # Format: JHB-INT-YYYY-XXXX (avec XXXX au format 0001, 0002, etc.)
            agreement_number = f"JHB-INT-{current_year}-{str(contract_count + 1).zfill(4)}"
            
            # Stocker le numéro d'accord dans la session pour l'utiliser après la vérification OTP
            request.session['agreement_number'] = agreement_number
            request.session['contract_id'] = str(contract.id)
            # AJOUT : Définir un timeout de session de 15 minutes
            request.session.set_expiry(900)
            
            logger.info(f"Contract verification successful, redirecting to OTP page. Agreement number: {agreement_number}")
            
            # Redirection vers la page OTP avec le contexte nécessaire
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'agreement_number': agreement_number,
                'expires_at': contract.expires_at
            }
            
            return render(request, self.template_name_otp, context)
            
        except Exception as e:
            logger.error(f"Error in contract verification: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
        
@method_decorator(never_cache, name='dispatch')
class ContractOTPVerificationView(View):
    template_name_success = 'signature_app/reviewcontract.html'
    template_name_otp = 'signature_app/otp_signup.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def post(self, request, *args, **kwargs):
        logger.info("OTP verification attempt received")
        
        entered_otp = request.POST.get('otp_code')
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        
        # AJOUT : Vérifier le nombre de tentatives
        attempts = request.session.get('otp_attempts', 0)
        max_attempts = 3
        
        if attempts >= max_attempts:
            logger.warning(f"Max OTP attempts exceeded for contract: {contract_id}")
            messages.error(request, 'Too many failed attempts. Please request a new link.')
            return render(request, self.template_name_error, {'error': 'Too many attempts'})
        
        if not entered_otp or not contract_id:
            logger.warning("Missing OTP code or contract ID in request")
            messages.error(request, 'Missing information. Please try again.')
            return render(request, self.template_name_error, {'error': 'Missing information'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # AJOUT : Vérifier que le contrat est dans le bon statut
            if contract.status not in ['PENDING', 'LINK_ACCESSED']:
                logger.warning(f"Invalid contract status for OTP: {contract.status}")
                messages.error(request, 'This contract has already been processed.')
                return render(request, self.template_name_error, {'error': 'Contract already processed'})
            
            # Vérification expiration
            if contract.is_expired():
                logger.warning(f"Expired contract accessed during OTP verification: {contract_id}")
                messages.error(request, 'This verification link has expired. Please contact support for assistance.')
                return render(request, self.template_name_error, {'error': 'Token expired'})
            
            # Vérification du code OTP
            if entered_otp != contract.otp_code:
                # AJOUT : Incrémenter le compteur de tentatives
                request.session['otp_attempts'] = attempts + 1
                
                logger.warning(f"Invalid OTP code for contract ID: {contract_id}")
                messages.error(request, 'The verification code you entered is incorrect. Please try again.')
                
                # Redirection vers la page OTP avec une erreur
                context = {
                    'contract': contract,
                    'interpreter_name': contract.interpreter_name,
                    'agreement_number': agreement_number,
                    'expires_at': contract.expires_at,
                    'error': 'Invalid OTP code',
                    'attempts_remaining': max_attempts - request.session.get('otp_attempts', 0)
                }
                return render(request, self.template_name_otp, context)
            
            logger.info(f"OTP verification successful for contract ID: {contract_id}")
            
            # AJOUT : Nettoyer le compteur de tentatives
            request.session.pop('otp_attempts', None)
            
            # Définir le flag de vérification dans la session
            request.session['otp_verified'] = True
            request.session['contract_verified_at'] = timezone.now().isoformat()
            
            # Préparer le contexte pour la page de review du contrat
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'agreement_number': agreement_number,
                'expires_at': contract.expires_at,
                'languages': contract.interpreter.languages.all() if hasattr(contract.interpreter, 'languages') else []
            }
            
            return render(request, self.template_name_success, context)
            
        except Exception as e:
            logger.error(f"Error in OTP verification: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
@method_decorator(never_cache, name='dispatch')
class ContractReviewView(View):
    template_name_review = 'signature_app/reviewcontract.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, *args, **kwargs):
        logger.info("Contract review page accessed")
        
        # Vérification si l'utilisateur a validé l'OTP
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        otp_verified = request.session.get('otp_verified', False)
        
        if not all([contract_id, agreement_number, otp_verified]):
            logger.warning("Unauthorized access attempt to contract review page")
            messages.error(request, 'You must complete the verification process first.')
            return render(request, self.template_name_error, {'error': 'Unauthorized access'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Vérification de l'expiration du contrat
            if contract.is_expired():
                logger.warning(f"Expired contract accessed: {contract_id}")
                messages.error(request, 'This contract has expired. Please contact support for assistance.')
                return render(request, self.template_name_error, {'error': 'Contract expired'})
            
            # Vérifier le temps écoulé depuis la vérification de l'OTP
            if 'contract_verified_at' in request.session:
                verified_at = datetime.datetime.fromisoformat(request.session['contract_verified_at'])
                current_time = timezone.now()
                
                # Si plus de 5 heures se sont écoulées depuis la vérification, exiger une nouvelle vérification
                if (current_time - verified_at).total_seconds() > 18000:  # 5 heures en secondes (5 * 60 * 60)
                    logger.warning(f"OTP verification timeout for contract ID: {contract_id}")
                    messages.error(request, 'Your verification has expired. Please verify your identity again.')
                    
                    # Réinitialiser le flag de vérification
                    request.session['otp_verified'] = False
                    
                    # Rediriger vers la page de vérification
                    return redirect('dbdint:contract_verification', token=contract.token)
            
            # Préparation du contexte pour la page de revue du contrat
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'interpreter_email': contract.interpreter_email,
                'interpreter_phone': contract.interpreter_phone,
                'interpreter_address': contract.interpreter_address,
                'agreement_number': agreement_number,
                'expires_at': contract.expires_at,
                'contract_date': timezone.now().strftime('%B %d, %Y')
            }
            
            # Ajout des langues et tarifs spécifiques à l'interprète
            if contract.interpreter and hasattr(contract.interpreter, 'languages'):
                # Récupération des langues de l'interprète
                interpreter_languages = contract.interpreter.languages.all()
                
                # Dictionnaire de correspondance langue-tarif
                language_rates = {
                    'Portuguese': '$35 per hour',
                    'Spanish': '$30 per hour',
                    'Haitian Creole': '$30 per hour',
                    'Cape Verdean': '$30 per hour',
                    'French': '$35 per hour',
                    'Mandarin': '$40 per hour'
                }
                
                # Création d'une liste de dictionnaires pour les langues et leurs tarifs
                interpreter_language_rates = []
                for lang in interpreter_languages:
                    rate = language_rates.get(lang.name, '$45 per hour')  # Par défaut pour les langues rares
                    interpreter_language_rates.append({
                        'name': lang.name,
                        'rate': rate
                    })
                
                context['interpreter_language_rates'] = interpreter_language_rates
            
            logger.info(f"Contract review page rendered for contract ID: {contract_id}")
            return render(request, self.template_name_review, context)
            
        except Exception as e:
            logger.error(f"Error in contract review: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
        
@method_decorator(never_cache, name='dispatch')
class ContractPaymentInfoView(View):
    template_name = 'signature_app/paymentinfo.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, *args, **kwargs):
        logger.info("Payment info page accessed")
        
        # Vérification si l'utilisateur a validé l'OTP
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        otp_verified = request.session.get('otp_verified', False)
        
        if not all([contract_id, agreement_number, otp_verified]):
            logger.warning("Unauthorized access attempt to payment info page")
            messages.error(request, 'You must complete the verification process first.')
            return render(request, self.template_name_error, {'error': 'Unauthorized access'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Vérification de l'expiration du contrat
            if contract.is_expired():
                logger.warning(f"Expired contract accessed: {contract_id}")
                messages.error(request, 'This contract has expired. Please contact support for assistance.')
                return render(request, self.template_name_error, {'error': 'Contract expired'})
            
            # Préparation du contexte pour la page de saisie des informations bancaires
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'interpreter_email': contract.interpreter_email,
                'interpreter_phone': contract.interpreter_phone,
                'interpreter_address': contract.interpreter_address,
                'agreement_number': agreement_number,
                'expires_at': contract.expires_at
            }
            
            # Si des informations bancaires existent déjà, les ajouter au contexte
            if contract.bank_name or contract.get_account_number():
                context['payment_data'] = {
                    'payment_name': contract.interpreter_name,
                    'payment_phone': contract.interpreter_phone,
                    'payment_address': contract.interpreter_address,
                    'payment_email': contract.interpreter_email,
                    'bank_name': contract.bank_name or '',
                    'account_type': contract.account_type or 'checking',
                    'account_number': contract.get_account_number() or '',
                    'routing_number': contract.get_routing_number() or '',
                    'swift_code': contract.get_swift_code() or ''
                }
            
            logger.info(f"Payment info page rendered for contract ID: {contract_id}")
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in payment info page: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
    def post(self, request, *args, **kwargs):
        logger.info("Payment info form submitted")
        
        # Vérification des données de session
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        
        if not contract_id:
            logger.warning("Missing contract ID in request")
            messages.error(request, 'Missing information. Please try again.')
            return render(request, self.template_name_error, {'error': 'Missing information'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Extraction des données du formulaire
            payment_data = {
                'payment_name': request.POST.get('payment_name'),
                'payment_phone': request.POST.get('payment_phone'),
                'payment_address': request.POST.get('payment_address'),
                'payment_email': request.POST.get('payment_email'),
                'bank_name': request.POST.get('bank_name'),
                'bank_address': request.POST.get('bank_address'),
                'account_holder': request.POST.get('account_holder'),
                'account_number': request.POST.get('account_number'),
                'routing_number': request.POST.get('routing_number'),
                'swift_code': request.POST.get('swift_code'),
                'account_type': request.POST.get('account_type')
            }
            
            # Validation des champs obligatoires
            required_fields = ['payment_name', 'payment_phone', 'payment_address', 'payment_email', 
                              'bank_name', 'account_holder', 'account_number', 'routing_number', 'account_type']
            
            for field in required_fields:
                if not payment_data[field]:
                    logger.warning(f"Missing required field: {field}")
                    messages.error(request, f"Please fill in all required fields.")
                    return self.form_invalid(request, contract, agreement_number, payment_data)
            
            # Mise à jour des informations de l'interprète si elles ont changé
            if payment_data['payment_name'] != contract.interpreter_name:
                contract.interpreter_name = payment_data['payment_name']
            if payment_data['payment_phone'] != contract.interpreter_phone:
                contract.interpreter_phone = payment_data['payment_phone']
            if payment_data['payment_address'] != contract.interpreter_address:
                contract.interpreter_address = payment_data['payment_address']
            if payment_data['payment_email'] != contract.interpreter_email:
                contract.interpreter_email = payment_data['payment_email']
            
            # Mise à jour des informations bancaires
            contract.bank_name = payment_data['bank_name']
            contract.account_type = payment_data['account_type']
            contract.account_holder_name = payment_data['account_holder']
            
            # Utilisation des méthodes de chiffrement pour les données sensibles
            contract.set_account_number(payment_data['account_number'])
            contract.set_routing_number(payment_data['routing_number'])
            if payment_data['swift_code']:
                contract.set_swift_code(payment_data['swift_code'])
            
            # Sauvegarde des modifications
            contract.save()
            
            # Définir un flag pour indiquer que cette étape est complétée
            request.session['payment_info_completed'] = True
            
            logger.info(f"Payment information saved successfully for contract ID: {contract_id}")
            
            # Rediriger vers la page de signature
            return redirect('dbdint:contract_signature')
            
        except Exception as e:
            logger.error(f"Error saving payment information: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while saving your payment information. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
    def form_invalid(self, request, contract, agreement_number, payment_data):
        """Gère le cas où le formulaire est invalide en réaffichant la page avec les erreurs."""
        context = {
            'contract': contract,
            'interpreter_name': contract.interpreter_name,
            'interpreter_email': contract.interpreter_email,
            'interpreter_phone': contract.interpreter_phone,
            'interpreter_address': contract.interpreter_address,
            'agreement_number': agreement_number,
            'payment_data': payment_data,  # Pour remplir le formulaire avec les données déjà saisies
            'expires_at': contract.expires_at
        }
        return render(request, self.template_name, context)
    
    
@method_decorator(never_cache, name='dispatch')
class ContractSignatureView(View):
    template_name = 'signature_app/signmethode.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, *args, **kwargs):
        logger.info("Signature page accessed")
        
        # Vérification des sessions
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        otp_verified = request.session.get('otp_verified', False)
        payment_info_completed = request.session.get('payment_info_completed', False)
        
        # Vérifier que l'utilisateur a bien complété les étapes précédentes
        if not all([contract_id, agreement_number, otp_verified, payment_info_completed]):
            logger.warning("Unauthorized access attempt to signature page")
            messages.error(request, 'You must complete the previous steps first.')
            return render(request, self.template_name_error, {'error': 'Unauthorized access'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Vérification de l'expiration du contrat
            if contract.is_expired():
                logger.warning(f"Expired contract accessed: {contract_id}")
                messages.error(request, 'This contract has expired. Please contact support for assistance.')
                return render(request, self.template_name_error, {'error': 'Contract expired'})
            
            # Préparation du contexte pour la page de signature
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'interpreter_email': contract.interpreter_email,
                'interpreter_phone': contract.interpreter_phone,
                'interpreter_address': contract.interpreter_address,
                'agreement_number': agreement_number,
                'expires_at': contract.expires_at,
                'current_date': timezone.now().strftime('%B %d, %Y')
            }
            
            logger.info(f"Signature page rendered for contract ID: {contract_id}")
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in signature page: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
    def post(self, request, *args, **kwargs):
        logger.info("Signature form submitted")
        
        # Vérification des sessions
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        
        if not contract_id:
            logger.warning("Missing contract ID in request")
            messages.error(request, 'Missing information. Please try again.')
            return render(request, self.template_name_error, {'error': 'Missing information'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Vérification de l'expiration du contrat
            if contract.is_expired():
                logger.warning(f"Expired contract accessed during signature: {contract_id}")
                messages.error(request, 'This contract has expired. Please contact support for assistance.')
                return render(request, self.template_name_error, {'error': 'Contract expired'})
            
            # Récupération des données de signature
            signature_method = request.POST.get('signature_method')
            agreement_checked = request.POST.get('agreement_checkbox') == 'on'
            
            # Vérification des conditions requises
            if not signature_method or not agreement_checked:
                logger.warning(f"Incomplete signature form for contract ID: {contract_id}")
                messages.error(request, 'Please complete all required fields and confirm the agreement.')
                return self.render_signature_page_with_error(request, contract, agreement_number, 'incomplete_form')
            
            # Récupération de la signature selon la méthode
            signature_data = None
            
            if signature_method == 'draw':
                signature_data = request.POST.get('drawn_signature_data')
                if not signature_data:
                    return self.render_signature_page_with_error(request, contract, agreement_number, 'missing_signature')
            
            elif signature_method == 'type':
                typed_signature = request.POST.get('typed_signature')
                font_class = request.POST.get('font_selector')
                
                if not typed_signature:
                    return self.render_signature_page_with_error(request, contract, agreement_number, 'missing_signature')
                
                signature_data = {
                    'text': typed_signature,
                    'font': font_class
                }
                signature_data = json.dumps(signature_data)
            
            elif signature_method == 'upload':
                uploaded_file = request.FILES.get('signature_file')
                
                if not uploaded_file:
                    return self.render_signature_page_with_error(request, contract, agreement_number, 'missing_signature')
                
                # Traitement de l'image de signature
                if signature_method == 'upload':
                    # Vérifier le type de fichier
                    if not uploaded_file.content_type.startswith('image/'):
                        messages.error(request, 'Please upload a valid image file.')
                        return self.render_signature_page_with_error(request, contract, agreement_number, 'invalid_file')
                    
                    # Vérifier la taille du fichier (max 2 Mo)
                    if uploaded_file.size > 2 * 1024 * 1024:
                        messages.error(request, 'File size must be less than 2MB.')
                        return self.render_signature_page_with_error(request, contract, agreement_number, 'file_too_large')
                    
                    # Sauvegarder l'image
                    contract.signature_image.save(
                        f"signature_{contract.id}_{int(time.time())}.{uploaded_file.name.split('.')[-1]}",
                        uploaded_file
                    )
            
            # Obtenir l'adresse IP
            ip_address = self.get_client_ip(request)
            
            # Mise à jour du contrat avec les informations de signature
            signature_kwargs = {
                'ip_address': ip_address,
            }
            
            # Traitement spécifique selon la méthode de signature
            if signature_method == 'draw':
                signature_kwargs['data'] = signature_data
            elif signature_method == 'type':
                try:
                    typed_data = json.loads(signature_data)
                    signature_kwargs['text'] = typed_data.get('text')
                    # Stocker également la police si nécessaire
                    if 'font' in typed_data:
                        signature_kwargs['font'] = typed_data.get('font')
                except (json.JSONDecodeError, TypeError):
                    # Si le format JSON n'est pas valide, utiliser le texte brut
                    signature_kwargs['text'] = signature_data
            # Pour 'upload', l'image est déjà sauvegardée dans le traitement précédent
            
            # Marquer le contrat comme signé
            contract.mark_as_signed(
                signature_type=signature_method,
                **signature_kwargs
            )
            
            # Ajouter automatiquement la signature de l'entreprise
            contract.mark_as_company_signed()
            
            # Mettre à jour le statut de l'utilisateur pour marquer sa registration comme complète
            if contract.user:
                # Correction ici: Utiliser le bon champ du modèle User
                contract.user.registration_complete = True
                
                # Si vous souhaitez également conserver la date de fin d'inscription
                # (vous devrez ajouter ce champ à votre modèle User si ce n'est pas déjà fait)
                if hasattr(contract.user, 'registration_completed_at'):
                    contract.user.registration_completed_at = timezone.now()
                    
                contract.user.save()
                logger.info(f"User {contract.user.email} registration marked as complete")
            
            # Si l'interprète existe, mettre également à jour son statut
            if contract.interpreter:
                contract.interpreter.active = True  # Utiliser le champ correct selon votre modèle Interpreter
                
                # Si vous avez ces champs dans votre modèle Interpreter
                if hasattr(contract.interpreter, 'contract_signed_at'):
                    contract.interpreter.contract_signed_at = timezone.now()
                if hasattr(contract.interpreter, 'contract_status'):
                    contract.interpreter.contract_status = 'SIGNED'
                    
                contract.interpreter.save()
                logger.info(f"Interpreter {contract.interpreter.id} marked as active with signed contract")
            
            # Définir un flag pour indiquer que cette étape est complétée
            request.session['signature_completed'] = True
            
            logger.info(f"Contract signed successfully for contract ID: {contract_id}")
            
            # Rediriger vers la page de confirmation
            return redirect('dbdint:confirmation')
            
        except Exception as e:
            logger.error(f"Error in contract signature: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your signature. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
    def render_signature_page_with_error(self, request, contract, agreement_number, error_code):
        """Rendu de la page de signature avec un message d'erreur approprié."""
        context = {
            'contract': contract,
            'interpreter_name': contract.interpreter_name,
            'interpreter_email': contract.interpreter_email,
            'interpreter_phone': contract.interpreter_phone,
            'interpreter_address': contract.interpreter_address,
            'agreement_number': agreement_number,
            'expires_at': contract.expires_at,
            'current_date': timezone.now().strftime('%B %d, %Y'),
            'error_code': error_code
        }
        return render(request, self.template_name, context)
    
    def get_client_ip(self, request):
        """Récupère l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    


@method_decorator(never_cache, name='dispatch')
class ContractConfirmationView(View):
    template_name = 'signature_app/confirmationsign.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, *args, **kwargs):
        logger.info("Confirmation page accessed")
        
        # Vérification des sessions
        contract_id = request.session.get('contract_id')
        agreement_number = request.session.get('agreement_number')
        otp_verified = request.session.get('otp_verified', False)
        payment_info_completed = request.session.get('payment_info_completed', False)
        signature_completed = request.session.get('signature_completed', False)
        
        # Vérifier que l'utilisateur a bien complété les étapes précédentes
        if not all([contract_id, agreement_number, otp_verified, payment_info_completed, signature_completed]):
            logger.warning("Unauthorized access attempt to confirmation page")
            messages.error(request, 'You must complete the previous steps first.')
            return render(request, self.template_name_error, {'error': 'Unauthorized access'})
        
        try:
            # Récupération du contrat
            contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
            
            # Générer le PDF et envoyer l'email si ce n'est pas déjà fait
            if not request.session.get('pdf_generated'):
                success = self.process_contract_pdf(contract, agreement_number)
                
                if success:
                    request.session['pdf_generated'] = True
                    messages.success(request, 'Your contract has been generated and sent to your email.')
                else:
                    messages.warning(request, 'There was an issue generating your contract. Our team has been notified.')
            
            # Préparer les données bancaires sécurisées
            account_number = None
            routing_number = None
            swift_code = None
            
            try:
                if contract.encrypted_account_number:
                    account_number = contract.get_account_number()
                    # Masquer le numéro de compte pour l'affichage
                    if account_number and len(account_number) > 4:
                        account_number = '••••' + account_number[-4:]
                
                if contract.encrypted_routing_number:
                    routing_number = contract.get_routing_number()
                    # Masquer le numéro de routage pour l'affichage
                    if routing_number and len(routing_number) > 4:
                        routing_number = '••••' + routing_number[-4:]
                
                if contract.encrypted_swift_code:
                    swift_code = contract.get_swift_code()
                    # Masquer le code SWIFT pour l'affichage
                    if swift_code and len(swift_code) > 4:
                        swift_code = '••••' + swift_code[-4:]
            except Exception as e:
                logger.error(f"Error decrypting banking information: {str(e)}")
                # Continuer même si le déchiffrement échoue
            
            # Préparation des informations de signature
            signature_info = {
                'type': contract.signature_type,
                'display_type': self.get_signature_display_type(contract.signature_type),
                'font': None,
                'data': None,
                'image_url': None
            }
            
            # Récupérer les données de signature selon le type
            if contract.signature_type == 'type':
                signature_info['data'] = contract.signature_typography_text
                signature_info['font'] = getattr(contract, 'signature_typography_font', 'font-brush-script')
            elif contract.signature_type == 'draw':
                signature_info['data'] = contract.signature_manual_data
            elif contract.signature_type == 'upload' and contract.signature_image:
                signature_info['image_url'] = contract.signature_image.url
            
            # Journal pour le débogage
            logger.info(f"Signature type: {contract.signature_type}")
            logger.info(f"Signature typography text: {contract.signature_typography_text}")
            logger.info(f"Signature manual data exists: {'Yes' if contract.signature_manual_data else 'No'}")
            logger.info(f"Signature image exists: {'Yes' if contract.signature_image else 'No'}")
            
            # Préparation du contexte pour la page de confirmation
            context = {
                'contract': contract,
                'interpreter_name': contract.interpreter_name,
                'interpreter_email': contract.interpreter_email,
                'interpreter_phone': contract.interpreter_phone,
                'interpreter_address': contract.interpreter_address,
                'agreement_number': agreement_number,
                'account_holder_name': contract.account_holder_name,
                'bank_name': contract.bank_name,
                'account_type': contract.account_type,
                'account_number': account_number,
                'routing_number': routing_number,
                'swift_code': swift_code,
                'signed_at': contract.signed_at,
                'signature_type': contract.signature_type,
                'signature_info': signature_info,
                'current_date': timezone.now().strftime('%B %d, %Y %H:%M:%S')
            }
            
            logger.info(f"Confirmation page rendered for contract ID: {contract_id}")
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in confirmation page: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred while processing your request. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})
    
    def get_signature_display_type(self, signature_type):
        """Retourne un nom lisible pour le type de signature."""
        types = {
            'draw': 'Drawn Signature',
            'type': 'Typed Signature',
            'upload': 'Uploaded Signature',
            None: 'Electronic Signature'
        }
        return types.get(signature_type, 'Electronic Signature')
    
    def process_contract_pdf(self, contract, agreement_number):
        """
        Processus complet de génération et envoi du PDF
        """
        try:
            logger.info(f"Starting PDF process for contract {contract.id}")
            
            # 1. Créer une clé PGP pour ce contrat
            logger.info("Step 1: Creating PGP key...")
            pgp_key = self._create_pgp_key_for_contract(contract)
            
            # 2. Créer un document dans la base de données
            logger.info("Step 2: Creating document record...")
            document = self._create_document_record(contract, pgp_key, agreement_number)
            
            # 3. Préparer les données pour l'API
            logger.info("Step 3: Preparing PDF data...")
            pdf_data = self._prepare_pdf_data(contract, document, agreement_number)
            
            # 4. Envoyer à l'API PDF
            logger.info("Step 4: Sending to PDF API...")
            pdf_download_url = self._send_to_pdf_api(pdf_data)
            
            if not pdf_download_url:
                logger.error("Failed to get PDF download URL from API")
                raise Exception("Failed to get PDF download URL from API")
            
            logger.info(f"Received download URL: {pdf_download_url[:100]}...")
            
            # 5. Télécharger le PDF
            logger.info("Step 5: Downloading PDF...")
            pdf_content = self._download_pdf(pdf_download_url)
            
            if not pdf_content:
                logger.error("Failed to download PDF content")
                raise Exception("Failed to download PDF content")
            
            logger.info(f"Downloaded PDF: {len(pdf_content)} bytes")
            
            # 6. Sauvegarder le PDF
            logger.info("Step 6: Saving PDF to storage...")
            pdf_path = self._save_pdf_to_storage(contract, pdf_content)
            
            # 7. Mettre à jour les enregistrements
            logger.info("Step 7: Updating records...")
            self._update_records_with_pdf(contract, document, pdf_path)
            
            # 8. Envoyer l'email avec le PDF
            logger.info("Step 8: Sending confirmation email...")
            self._send_confirmation_email_with_pdf(contract, pdf_content, agreement_number)
            
            logger.info(f"PDF process completed successfully for contract {contract.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in PDF process for contract {contract.id}: {str(e)}", exc_info=True)
            
            # Envoyer une notification à l'équipe technique
            try:
                # Vous pouvez implémenter une notification Slack, email ou autre ici
                logger.critical(f"PDF generation failed for contract {contract.id} - {contract.interpreter_email}")
            except:
                pass
                
            return False
    
    def _create_pgp_key_for_contract(self, contract):
        """Crée une clé PGP dérivée pour ce contrat"""
        from .models import PGPKey
        from .mixins.signup_mixins import KeyDerivationMixin
        
        try:
            key_name = f"Contract Key - {contract.interpreter_name} - {contract.id}"
            pgp_key = KeyDerivationMixin.derive_key(
                name=key_name,
                user_name=contract.interpreter_name,
                user_email=contract.interpreter_email,
                expiry_days=365 * 5
            )
            
            logger.info(f"PGP key created for contract {contract.id}: {pgp_key.key_id}")
            return pgp_key
            
        except Exception as e:
            logger.error(f"Error creating PGP key: {str(e)}")
            raise
    
    def _create_document_record(self, contract, pgp_key, agreement_number):
        """Crée un enregistrement dans la table Document"""
        from .models import Document
        
        try:
            document = Document.objects.create(
                title=f"Interpreter Service Agreement - {contract.interpreter_name}",
                document_type='CONTRACT',
                status='DRAFT',
                user=contract.user,
                interpreter_contract=contract,
                signing_key=pgp_key,
                agreement_id=agreement_number
            )
            
            document.add_metadata('contract_id', str(contract.id))
            document.add_metadata('interpreter_email', contract.interpreter_email)
            document.add_metadata('signature_type', contract.signature_type)
            document.save()
            
            logger.info(f"Document record created: {document.document_number}")
            return document
            
        except Exception as e:
            logger.error(f"Error creating document record: {str(e)}")
            raise
    
    def _prepare_pdf_data(self, contract, document, agreement_number):
        """
        Prépare les données pour l'API PDF
        Utilise les informations décryptées et les URLs existantes dans la DB
        """
        # Décrypter les informations bancaires
        account_number = contract.get_account_number() if contract.encrypted_account_number else ""
        routing_number = contract.get_routing_number() if contract.encrypted_routing_number else ""
        swift_code = contract.get_swift_code() if contract.encrypted_swift_code else ""
        
        # Déterminer la signature selon le type stocké dans la DB
        signature_type = 'text'  # Valeur par défaut
        signature_value = contract.interpreter_name  # Valeur par défaut
        
        if contract.signature_type == 'type':
            # Signature typographique - texte simple
            signature_type = 'text'
            signature_value = contract.signature_typography_text
            
        elif contract.signature_type == 'draw':
            # Signature dessinée - utiliser l'URL stockée dans signature_converted_url
            if contract.signature_converted_url:
                signature_type = 'image'
                signature_value = contract.get_signature_url()  # URL déjà complète depuis B2
            
        elif contract.signature_type == 'upload':
            # Signature uploadée - utiliser l'URL de signature_image
            if contract.signature_image:
                signature_type = 'image'
                signature_value = contract.get_signature_url()  # Utilise la méthode du modèle
        
        # Générer la signature PGP
        pgp_signature = self._generate_pgp_signature(contract, document)
        
        pdf_data = {
            "agreement_id": agreement_number,
            "date_created": timezone.now().strftime("%B %d, %Y"),
            "agreement_date": contract.signed_at.strftime("%B %d, %Y") if contract.signed_at else timezone.now().strftime("%B %d, %Y"),
            "interpreter": {
                "name": contract.interpreter_name,
                "address": contract.interpreter_address,
                "contact_information": f"{contract.interpreter_email} | {contract.interpreter_phone}"
            },
            "company_signature": {
                "type": "text",
                "value": contract.company_representative_name,
                "date": contract.company_signed_at.strftime("%B %d, %Y") if contract.company_signed_at else timezone.now().strftime("%B %d, %Y")
            },
            "interpreter_signature": {
                "type": signature_type,
                "value": signature_value,
                "date": contract.signed_at.strftime("%B %d, %Y") if contract.signed_at else timezone.now().strftime("%B %d, %Y")
            },
            "personal_information": {
                "name": contract.interpreter_name,
                "address": contract.interpreter_address,
                "phone": contract.interpreter_phone,
                "email": contract.interpreter_email
            },
            "account_type": contract.account_type.capitalize() if contract.account_type else "Checking",
            "banking_information": {
                "bank_name": contract.bank_name or "",
                "bank_address": contract.interpreter_address,  # Utiliser l'adresse de l'interprète
                "account_holder_name": contract.account_holder_name or contract.interpreter_name,
                "account_number": account_number,  # Décrypté
                "routing_number": routing_number,  # Décrypté
                "swift_code": swift_code  # Décrypté
            },
            "authorization": {
                "signature": {
                    "type": signature_type,
                    "value": signature_value
                },
                "date": contract.signed_at.strftime("%B %d, %Y") if contract.signed_at else timezone.now().strftime("%B %d, %Y")
            },
            "document_metadata": {
                "document_number": document.document_number,
                "agreement_id": agreement_number,
                "title": document.title,
                "document_type": document.document_type,
                "user": f"USR-{contract.user.id}" if contract.user else None,
                "interpreter_contract": f"IC-{contract.id}",
                "pgp_signature": pgp_signature,
                "signing_key": document.signing_key.key_id if document.signing_key else None,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "signed_at": contract.signed_at.isoformat() if contract.signed_at else None,
                "metadata": document.metadata
            }
        }
        
        return pdf_data
    
    def _generate_pgp_signature(self, contract, document):
        """Génère la signature PGP pour le document"""
        try:
            from .mixins.signup_mixins import KeyDerivationMixin
            
            content_to_sign = f"{document.document_number}|{contract.id}|{contract.interpreter_email}|{contract.signed_at}"
            
            if document.signing_key:
                signature, success, message = KeyDerivationMixin.generate_signature(
                    content_to_sign,
                    document.signing_key.key_id
                )
                
                if success:
                    return f"-----BEGIN PGP SIGNATURE-----\nVersion: BCPG v1.69\n\n{signature}\n-----END PGP SIGNATURE-----"
            
            logger.warning(f"Failed to generate PGP signature for document {document.id}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating PGP signature: {e}")
            return None
    
    def _send_to_pdf_api(self, pdf_data):
        """Envoie les données à l'API PDF en utilisant la bibliothèque requests."""
        try:
            # URL fixe de l'API sur Railway
            api_url = 'https://jhbridge-esign-production.up.railway.app/api/generate-contract'
            
            # Si vous voulez utiliser les settings, assurez-vous que settings.API_URL_PDF_GENERATOR est correct
            # api_url = settings.API_URL_PDF_GENERATOR
            
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': settings.PDF_GENERATOR_API_KEY  # Assurez-vous que cette clé est correcte dans settings
            }
            
            logger.info(f"Envoi de la requête POST à l'API PDF : {api_url}")
            logger.debug(f"Headers: {headers}")
            
            # Log des données envoyées (sans les infos sensibles)
            safe_data = {
                'agreement_id': pdf_data.get('agreement_id'),
                'interpreter_name': pdf_data.get('interpreter', {}).get('name'),
                'document_number': pdf_data.get('document_metadata', {}).get('document_number')
            }
            logger.info(f"Envoi de données pour : {safe_data}")

            # Utiliser un timeout de 310 secondes (légèrement plus que le timeout de Next.js)
            response = requests.post(
                api_url, 
                json=pdf_data,  # Utiliser json= au lieu de data=json.dumps()
                headers=headers, 
                timeout=310
            )

            logger.info(f"Réponse de l'API PDF - Statut : {response.status_code}")
            
            # Vérifier le statut de la réponse
            if response.status_code != 200:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('error', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text[:500]}"
                logger.error(error_msg)
                return None

            # Parser la réponse JSON
            try:
                response_json = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                logger.error(f"Response text: {response.text[:500]}")
                return None

            # Vérifier le succès de l'opération
            if not response_json.get('success', False):
                logger.error(f"API indicated failure: {response_json.get('error', 'Unknown error')}")
                return None

            # Récupérer l'URL de téléchargement
            download_url = response_json.get('downloadUrl')
            
            if not download_url:
                logger.error("No 'downloadUrl' in API response")
                logger.error(f"Response data: {response_json}")
                return None

            # Logs additionnels pour le débogage
            logger.info(f"PDF généré avec succès")
            logger.info(f"Download URL: {download_url[:100]}...")
            logger.info(f"Filename: {response_json.get('fileName')}")
            logger.info(f"Expires: {response_json.get('expires')}")
            
            return download_url

        except requests.exceptions.HTTPError as http_err:
            error_details = str(http_err)
            if http_err.response is not None:
                try:
                    error_json = http_err.response.json()
                    error_details = f"{http_err} - {error_json.get('error', error_json)}"
                except:
                    error_details = f"{http_err} - {http_err.response.text[:500]}"
            logger.error(f"HTTP error calling PDF API: {error_details}")
            return None
            
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection error to PDF API: {conn_err}")
            return None
            
        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout calling PDF API (after 310s): {timeout_err}")
            return None
            
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request exception calling PDF API: {req_err}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error calling PDF API: {str(e)}", exc_info=True)
            return None
    
    def _download_pdf(self, download_url):
        """Télécharge le PDF depuis l'URL fournie par l'API"""
        try:
            logger.info(f"Downloading PDF from: {download_url[:100]}...")
            
            # Augmenter le timeout pour les gros fichiers
            response = requests.get(download_url, timeout=60, stream=True)
            
            # Vérifier le statut
            if response.status_code != 200:
                logger.error(f"Failed to download PDF: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")
                return None
            
            # Vérifier le Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type:
                logger.warning(f"Unexpected Content-Type: {content_type}")
            
            # Télécharger le contenu
            pdf_content = response.content
            
            # Vérifier la taille
            content_length = len(pdf_content)
            if content_length == 0:
                logger.error("Downloaded PDF is empty")
                return None
            
            logger.info(f"PDF downloaded successfully: {content_length} bytes")
            
            # Vérifier que c'est bien un PDF
            if not pdf_content.startswith(b'%PDF'):
                logger.error("Downloaded file is not a valid PDF")
                logger.error(f"First bytes: {pdf_content[:20]}")
                return None
            
            return pdf_content
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading PDF from: {download_url}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading PDF: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error downloading PDF: {e}", exc_info=True)
            return None
    
    def _save_pdf_to_storage(self, contract, pdf_content):
        """Sauvegarde le PDF"""
        try:
            filename = f"contracts/contract_{contract.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            path = default_storage.save(
                filename,
                ContentFile(pdf_content)
            )
            
            logger.info(f"PDF saved to storage: {path}")
            return path
            
        except Exception as e:
            logger.error(f"Error saving PDF to storage: {str(e)}")
            raise
    
    def _update_records_with_pdf(self, contract, document, pdf_path):
        """Met à jour les enregistrements"""
        try:
            # Mettre à jour le contrat
            contract.contract_document = pdf_path
            contract.save()
            
            # Mettre à jour le document
            document.file = pdf_path
            document.status = 'SIGNED'
            document.signed_at = timezone.now()
            document.calculate_file_hash()
            document.save()
            
            logger.info(f"Records updated with PDF path: {pdf_path}")
            
        except Exception as e:
            logger.error(f"Error updating records: {str(e)}")
            raise
    
    def _send_confirmation_email_with_pdf(self, contract, pdf_content, agreement_number):
        """Envoie l'email de confirmation avec le PDF en pièce jointe"""
        try:
            # Création d'un identifiant unique pour ce message
            message_id = f"<confirmation-{contract.id}-{uuid.uuid4()}@{socket.gethostname()}>"
            
            # Préparation des données pour le template
            context = {
                'interpreter_name': contract.interpreter_name,
                'email': contract.interpreter_email,
                'agreement_number': agreement_number,
                'signed_date': contract.signed_at.strftime('%B %d, %Y') if contract.signed_at else timezone.now().strftime('%B %d, %Y'),
            }
            
            # Rendu du template HTML
            html_message = render_to_string('notifmail/contract_agreement_good.html', context)
            plain_message = strip_tags(html_message)
            
            # Ligne d'objet
            subject = f"Your Contract Has Been Approved! - JH Bridge"
            
            # Format professionnel pour l'adresse expéditeur
            from_email = f"JH Bridge Contracts <contracts@jhbridgetranslation.com>"
            
            # Création de l'email avec du texte brut comme corps principal
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[contract.interpreter_email],
                reply_to=['support@jhbridgetranslation.com']
            )
            
            # Ajout de la version HTML comme alternative
            email.attach_alternative(html_message, "text/html")
            
            # Attacher le PDF
            email.attach(
                f"contract_{contract.interpreter_name.replace(' ', '_')}.pdf",
                pdf_content,
                'application/pdf'
            )
            
            # En-têtes optimisés pour la délivrabilité
            email.extra_headers = {
                # Identifiant unique de message
                'Message-ID': message_id,
                
                # En-têtes d'authentification et de traçabilité
                'X-Entity-Ref-ID': str(contract.token),
                'X-Mailer': 'JHBridge-ContractMailer/1.0',
                'X-Contact-ID': str(contract.id),
                
                # Mécanisme de désabonnement
                'List-Unsubscribe': f'<mailto:unsubscribe@jhbridgetranslation.com?subject=Unsubscribe-{contract.interpreter_email}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                
                # En-têtes de classification du message
                'Precedence': 'bulk',
                'Auto-Submitted': 'auto-generated',
                
                # ID unique pour le feedback loop
                'Feedback-ID': f'contract-{contract.id}:{contract.id}:jhbridge:{int(time.time())}'
            }
            
            # Envoi de l'email
            email.send(fail_silently=False)
            
            logger.info(f"Confirmation email sent to: {contract.interpreter_email} with Message-ID: {message_id}")
            
            # Mettre à jour le statut du contrat
            contract.status = 'COMPLETED'
            contract.save()
            
        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}", exc_info=True)
            raise
            
            
            
            
def contract_render_view(request):
    """
    Vue très simple qui fait uniquement le rendu du template de contrat.
    """
    return render(request, 'contract/template_contract.html')