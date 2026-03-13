import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

from ...models import InterpreterContractSignature
from ..onboarding import get_onboarding_invitation

logger = logging.getLogger(__name__)


def _encrypt_value(value):
    """Encrypt a value using Fernet encryption."""
    if not value:
        return value
    try:
        encrypted = InterpreterContractSignature.encrypt_data(value)
        return encrypted.decode() if isinstance(encrypted, bytes) else encrypted
    except Exception as e:
        logger.warning(f"Encryption failed for sensitive data: {e}. xzerty.")
        return value


def _decrypt_value(value):
    """Decrypt a value using Fernet encryption."""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            value = value.encode()
        return InterpreterContractSignature.decrypt_data(value) or ''
    except Exception:
        return value if isinstance(value, str) else ''

@method_decorator(never_cache, name='dispatch')
class ContractWizardView(View):
    template_name = 'contract/wizard.html'
    template_name_error = 'signature_app/expiredlinks.html'
    
    def get(self, request, *args, **kwargs):
        """
        Token-based contract wizard view.
        No additional verification required - security is enforced via unique tokens.
        """
        contract_id = request.session.get('contract_id')
        otp_verified = request.session.get('otp_verified', False)
            
        try:
            # --- NEW CONTRACT FLOW INTEGRATION ---
            invitation_id = request.session.get('invitation_id')
            invitation = None
            if invitation_id:
                try:
                    from ...models import ContractInvitation, ContractTrackingEvent
                    invitation = ContractInvitation.objects.get(id=invitation_id)
                    interpreter_name = invitation.interpreter.user.get_full_name()
                    agreement_number = invitation.invitation_number
                    
                    # Track Wizard Started
                    if not request.session.get('wizard_tracked'):
                         ContractTrackingEvent.objects.create(
                            invitation=invitation,
                            event_type='WIZARD_STARTED',
                            metadata={'user_agent': request.META.get('HTTP_USER_AGENT')}
                        )
                         request.session['wizard_tracked'] = True
                except Exception as ex:
                    logger.error(f"Error loading invitation {invitation_id}: {ex}")
            # -------------------------------------

            # -------------------------------------

            if contract_id:
                contract = get_object_or_404(InterpreterContractSignature, id=contract_id)
                interpreter_name = contract.interpreter_name
                agreement_number = request.session.get('agreement_number')
            elif invitation:
                # Security Check: If already signed, redirect immediately
                if invitation.status == 'SIGNED':
                    return redirect('dbdint:contract_already_confirmed')
                    
                contract = None
                # interpreter_name and agreement_number already set from invitation above
            else:
                # No valid contract or invitation - show error
                logger.error("Wizard accessed without valid contract or invitation")
                messages.error(request, 'Invalid access. Please use the link from your email.')
                return render(request, self.template_name_error, {'error': 'Invalid access'})
                
            # Prepare data for wizard
            from ...models import InterpreterLanguage
            interpreter = invitation.interpreter if invitation else (contract.interpreter if contract else None)

            bank_name = ''
            account_holder_name = ''
            account_type = ''
            routing_number = ''
            account_number = ''

            # Recap / review data
            interpreter_email = ''
            interpreter_phone = ''
            interpreter_dob = ''
            interpreter_address = ''
            interpreter_languages_display = ''
            interpreter_primary_language = ''
            interpreter_certified = 'No'
            interpreter_cert_type = ''
            interpreter_cert_number = ''
            interpreter_experience = ''
            interpreter_preferred_type = ''
            interpreter_radius = ''
            interpreter_assignment_types = ''
            interpreter_cities = ''

            if interpreter:
                # Banking (pre-fill from existing data)
                bank_name = interpreter.bank_name or ''
                account_holder_name = interpreter.account_holder_name or ''
                account_type = interpreter.account_type or ''
                routing_number = _decrypt_value(interpreter.routing_number)
                account_number = _decrypt_value(interpreter.account_number)

                # Profile info for recap step
                interpreter_email = interpreter.user.email if interpreter.user else ''
                # On va chercher le téléphone dans l'objet User lié
                interpreter_phone = interpreter.user.phone or ''
                interpreter_dob = interpreter.date_of_birth.strftime('%B %d, %Y') if interpreter.date_of_birth else ''

                addr_parts = [interpreter.address or '', interpreter.city or '', interpreter.state or '', interpreter.zip_code or '']
                interpreter_address = ', '.join([p for p in addr_parts if p])

                # Languages
                langs = InterpreterLanguage.objects.filter(interpreter=interpreter).select_related('language')
                lang_names = [il.language.name for il in langs]
                interpreter_languages_display = ', '.join(lang_names) if lang_names else ''
                primary_lang = langs.filter(is_primary=True).first()
                interpreter_primary_language = primary_lang.language.name if primary_lang else ''

                # Certification
                existing_cert = interpreter.certifications or {}
                if existing_cert.get('certified'):
                    interpreter_certified = 'Yes'
                    interpreter_cert_type = existing_cert.get('type', '')
                    interpreter_cert_number = existing_cert.get('number', '')

                # Experience
                interpreter_experience = interpreter.years_of_experience or ''
                interpreter_preferred_type = interpreter.preferred_assignment_type or ''
                interpreter_radius = interpreter.radius_of_service or ''

                atypes = interpreter.assignment_types or []
                interpreter_assignment_types = ', '.join(atypes) if isinstance(atypes, list) else str(atypes)

                cities_list = interpreter.cities_willing_to_cover or []
                interpreter_cities = ', '.join(cities_list) if isinstance(cities_list, list) else str(cities_list)

            context = {
                'contract': contract,
                'invitation': invitation,
                'interpreter_name': interpreter_name,
                'agreement_number': agreement_number,
                'contract_date': timezone.now().strftime('%B %d, %Y'),
                'interpreter': interpreter,
                # Banking data (editable in step 8)
                'bank_name': bank_name,
                'account_holder_name': account_holder_name,
                'account_type': account_type,
                'routing_number': routing_number,
                'account_number': account_number,
                # Recap data (read-only in step 9, from profile)
                'interpreter_email': interpreter_email,
                'interpreter_phone': interpreter_phone,
                'interpreter_dob': interpreter_dob,
                'interpreter_address': interpreter_address,
                'interpreter_languages_display': interpreter_languages_display,
                'interpreter_primary_language': interpreter_primary_language,
                'interpreter_certified': interpreter_certified,
                'interpreter_cert_type': interpreter_cert_type,
                'interpreter_cert_number': interpreter_cert_number,
                'interpreter_experience': interpreter_experience,
                'interpreter_preferred_type': interpreter_preferred_type,
                'interpreter_radius': interpreter_radius,
                'interpreter_assignment_types': interpreter_assignment_types,
                'interpreter_cities': interpreter_cities,
            }

            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in contract wizard view: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})

    def post(self, request, *args, **kwargs):
        """
        Handle wizard form submission - sign contract and send confirmation.
        """
        invitation_id = request.session.get('invitation_id')
        
        if not invitation_id:
            messages.error(request, 'Session expired. Please use the link from your email.')
            return redirect('dbdint:contract_error')
            
        try:
            from ...models import ContractInvitation
            invitation = ContractInvitation.objects.get(id=invitation_id)
            
            # Check if already signed
            if invitation.status == 'SIGNED':
                return redirect('dbdint:contract_already_confirmed')
            
            # Require agreement checkbox
            if request.POST.get('agreement') != 'yes':
                messages.error(request, 'You must agree to the terms to proceed.')
                return self.get(request)

            # Process banking data (only field collected in wizard now)
            interpreter = invitation.interpreter

            bank_name = request.POST.get('bank_name', '').strip()
            account_holder_name = request.POST.get('account_holder_name', '').strip()
            account_type = request.POST.get('account_type', '')
            routing_number = request.POST.get('routing_number', '').strip()
            account_number = request.POST.get('account_number', '').strip()

            # Update banking info (encrypt sensitive fields)
            interpreter.bank_name = bank_name
            interpreter.account_holder_name = account_holder_name
            interpreter.account_type = account_type
            interpreter.routing_number = _encrypt_value(routing_number)
            interpreter.account_number = _encrypt_value(account_number)

            interpreter.save(update_fields=[
                'bank_name', 'account_holder_name', 'account_type',
                'routing_number', 'account_number',
            ])

            # Sign the contract using helper
            from .tracking import create_and_sign_contract
            create_and_sign_contract(invitation, request, signature_method='WIZARD')

            # Clear session data
            request.session.pop('invitation_id', None)
            request.session.pop('wizard_tracked', None)

            # Check if this is part of an onboarding flow
            onboarding_id = request.session.get('dbdint:onboarding_invitation_id')
            if onboarding_id:
                try:
                    from ...models import OnboardingInvitation, OnboardingTrackingEvent
                    onboarding = OnboardingInvitation.objects.get(id=onboarding_id)
                    onboarding.current_phase = 'COMPLETED'
                    onboarding.completed_at = timezone.now()
                    onboarding.save(update_fields=['current_phase', 'completed_at'])

                    OnboardingTrackingEvent.objects.create(
                        invitation=onboarding,
                        event_type='ONBOARDING_COMPLETED',
                        metadata={'contract_invitation': str(invitation.invitation_number)}
                    )

                    # Enable dashboard access
                    user = invitation.interpreter.user
                    if not user.registration_complete:
                        user.registration_complete = True
                        user.contract_acceptance_date = timezone.now()
                        user.save(update_fields=['registration_complete', 'contract_acceptance_date'])

                    request.session.pop('dbdint:onboarding_invitation_id', None)
                    return redirect('dbdint:onboarding_complete')
                except Exception as onb_err:
                    logger.error(f"Failed to finalize onboarding: {onb_err}", exc_info=True)

            # Set flag for success view security
            request.session['contract_just_signed'] = True

            return redirect('dbdint:contract_success')
                
        except Exception as e:
            logger.error(f"Error in contract wizard submission: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred during submission. Please check your data and try again.')
            return self.get(request)

@method_decorator(never_cache, name='dispatch')
class ContractSuccessView(View):
    """View for successful first-time agreement confirmation"""
    template_name = 'contract/successclickone.html'
    
    def get(self, request, *args, **kwargs):
        # Security: Only allow access if specifically set by wizard/signing flow
        if not request.session.get('contract_just_signed'):
            logger.warning("Attempted direct access to success page without signing")
            return redirect('dbdint:contract_error')
        
        # Clear the flag so it cannot be reloaded indefinitely (optional, depending on UX)
        # request.session.pop('contract_just_signed', None) 
        
        return render(request, self.template_name)


@method_decorator(never_cache, name='dispatch')
class ContractAlreadyConfirmedView(View):
    """View for when user clicks agreement link a second time"""
    template_name = 'contract/secondclick.html'
    
    def get(self, request, *args, **kwargs):
        # If this is part of onboarding, try to finalize it
        onboarding = get_onboarding_invitation(request)
        if onboarding and onboarding.current_phase != 'COMPLETED':
            try:
                onboarding.current_phase = 'COMPLETED'
                onboarding.completed_at = timezone.now()
                onboarding.save(update_fields=['current_phase', 'completed_at'])
                
                # Ensure registration is marked complete
                user = onboarding.user
                if user and not user.registration_complete:
                    user.registration_complete = True
                    user.contract_acceptance_date = timezone.now()
                    user.save(update_fields=['registration_complete', 'contract_acceptance_date'])
                
                return redirect('dbdint:onboarding_complete')
            except Exception as e:
                logger.error(f"Failed to finalize onboarding in already_confirmed view: {e}")

        return render(request, self.template_name)


@method_decorator(never_cache, name='dispatch')
class ContractErrorView(View):
    """View for when something goes wrong with the contract process"""
    template_name = 'contract/wrongclick.html'
    
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


@method_decorator(never_cache, name='dispatch')
class ContractOTPView(View):
    """View for OTP entry page"""
    template_name = 'contract/otp.html'
    
    def get(self, request, *args, **kwargs):
        email = request.session.get('contract_email', '')
        context = {
            'email': email
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        otp_code = request.POST.get('otp_code')
        
        if not otp_code or len(otp_code) != 6:
            messages.error(request, 'Invalid OTP code')
            return self.get(request)
        
        # Get stored OTP from session or database
        stored_otp = request.session.get('otp_code')
        otp_expiry = request.session.get('otp_expiry')
        
        # Verify OTP
        if not stored_otp or not otp_expiry:
            messages.error(request, 'OTP expired or not found')
            return self.get(request)
        
        if timezone.now() > otp_expiry:
            messages.error(request, 'OTP has expired')
            return self.get(request)
        
        if otp_code != stored_otp:
            messages.error(request, 'Invalid OTP code')
            return self.get(request)
        
        # Mark as verified
        request.session['otp_verified'] = True
        request.session.pop('otp_code', None)
        request.session.pop('otp_expiry', None)
        
        return redirect('dbdint:contract_success')
