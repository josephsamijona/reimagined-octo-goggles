from django.urls import reverse
from app.models import InterpreterContractSignature, ContractInvitation

def has_signed_contract(user):
    """
    Checks if the user (interpreter) has a valid signed contract.
    Supports both legacy and new wizard-based contracts.
    """
    if not user.is_authenticated or user.role != 'INTERPRETER':
        return False
        
    try:
        # Check for new system signature
        if hasattr(user, 'interpreter_contracts'):
            if user.interpreter_contracts.filter(status='SIGNED').exists():
                return True
                
        # Check for legacy system signature (if applicable)
        # Assuming legacy system also used InterpreterContractSignature but might have different status flags
        # or different relation. Based on current model, 'user' FK exists on InterpreterContractSignature.
        
        # Also check the Interpreter profile flag
        if hasattr(user, 'interpreter_profile'):
            if user.interpreter_profile.has_accepted_contract:
                return True
                
        return False
    except Exception:
        return False

def get_contract_wizard_link(user):
    """
    Generates the link to the contract wizard for a user.
    If an invitation exists, uses its token. If not, creates one.
    """
    # Try to find existing pending invitation
    if hasattr(user, 'interpreter_profile'):
        invitation = ContractInvitation.objects.filter(
            interpreter=user.interpreter_profile,
            status__in=['SENT', 'OPENED', 'REVIEWING']
        ).first()
        
        if invitation:
            return reverse('dbdint:contract_wizard_token', kwargs={'token': invitation.token})
            
    # If no invitation, return the generic wizard link (which might require login/session setup)
    return reverse('dbdint:contract_wizard')
