from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from ..forms import (
    PayrollDocumentForm,
    ServiceFormSet,
    ReimbursementFormSet,
    DeductionFormSet
)
from ..models import (
    PayrollDocument,
    Service,
    Reimbursement,
    Deduction
)
from .utils import format_decimal, generate_document_number

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
