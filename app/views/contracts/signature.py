import json
import logging
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from ...models import InterpreterContractSignature

logger = logging.getLogger(__name__)

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
            
            # --- NEW CONTRACT FLOW INTEGRATION ---
            invitation_id = request.session.get('invitation_id')
            if invitation_id:
                try:
                    from ...models import ContractInvitation, ContractTrackingEvent
                    from ...services.contract_pdf_service import ContractPDFGenerator
                    from ...services.email_service import ContractEmailService
                    
                    invitation = ContractInvitation.objects.get(id=invitation_id)
                    invitation.contract_signature = contract
                    invitation.status = 'SIGNED'
                    invitation.signed_at = timezone.now()
                    invitation.save()
                    
                    # Track Wizard Completion
                    ContractTrackingEvent.objects.create(
                        invitation=invitation,
                        event_type='WIZARD_COMPLETED',
                        metadata={'ip': ip_address, 'method': signature_method}
                    )
                    
                    # Generate PDF & Upload to S3
                    pdf_service = ContractPDFGenerator(invitation)
                    pdf_s3_key = pdf_service.generate_and_upload()
                    
                    # Create tracking event for signing
                    ContractTrackingEvent.objects.create(
                        invitation=invitation,
                        event_type='CONTRACT_SIGNED',
                        metadata={'s3_key': pdf_s3_key}
                    )
                    
                    # Send Confirmation Email
                    ContractEmailService.send_confirmation_email(invitation)
                    
                    logger.info(f"New contract flow completed for invitation {invitation.invitation_number}")
                    
                except Exception as ex:
                    logger.error(f"Error in new contract flow integration: {ex}", exc_info=True)
                    # Don't block the user if this background stuff fails, but log heavily
            
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
