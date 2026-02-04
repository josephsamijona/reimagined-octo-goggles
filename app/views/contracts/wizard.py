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
                
            context = {
                'contract': contract,
                'invitation': invitation,
                'interpreter_name': interpreter_name,
                'agreement_number': agreement_number,
                'contract_date': timezone.now().strftime('%B %d, %Y'),
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
            
            # Sign the contract using the same logic as DirectAcceptView
            from .tracking import create_and_sign_contract
            create_and_sign_contract(invitation, request)
            
            # Clear session data
            request.session.pop('invitation_id', None)
            request.session.pop('wizard_tracked', None)
            
            # Set flag for success view security
            request.session['contract_just_signed'] = True
            
            return redirect('dbdint:contract_success')
                
        except Exception as e:
            logger.error(f"Error in contract wizard submission: {str(e)}", exc_info=True)
            messages.error(request, 'An error occurred. Please try again or contact support.')
            return render(request, self.template_name_error, {'error': 'System error'})

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
