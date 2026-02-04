import datetime
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from ...models import InterpreterContractSignature

logger = logging.getLogger(__name__)

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
