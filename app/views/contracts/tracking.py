from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.utils import timezone
from app.models import ContractInvitation, ContractTrackingEvent, InterpreterContractSignature
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Retrieve client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def create_and_sign_contract(invitation, request):
    """
    Creates and auto-signs a contract for the direct accept flow.
    
    This function:
    1. Creates or retrieves the contract signature record
    2. Marks the contract as signed
    3. Creates tracking events
    4. Generates PDF and uploads to S3
    5. Sends confirmation email to interpreter
    
    Args:
        invitation: ContractInvitation instance
        request: HttpRequest object for URL generation
    """
    # Create or get contract signature model
    if not invitation.contract_signature:
        # Create new contract signature record
        contract = InterpreterContractSignature.objects.create(
            interpreter=invitation.interpreter,
            user=invitation.interpreter.user,
            status='SIGNED',
            signature_type='type',  # Default for direct accept
            signature_typography_text=invitation.interpreter.user.get_full_name(),
            signed_at=timezone.now(),
            ip_address=get_client_ip(request),
            is_fully_signed=False # Wait for company signature
        )
        invitation.contract_signature = contract
    else:
        contract = invitation.contract_signature
        contract.status = 'SIGNED'
        contract.signed_at = timezone.now()
        contract.save()
        
    invitation.status = 'SIGNED'
    invitation.signed_at = timezone.now()
    invitation.save()
    
    # Create tracking event
    ContractTrackingEvent.objects.create(
        invitation=invitation,
        event_type='CONTRACT_SIGNED',
        metadata={'method': 'direct_accept', 'ip': get_client_ip(request)}
    )
    
    # Trigger PDF generation & Upload
    try:
        from app.services.contract_pdf_service import ContractPDFGenerator
        pdf_gen = ContractPDFGenerator(invitation)
        pdf_gen.generate_and_upload(request)
        
        # Trigger confirmation email
        from app.services.email_service import ContractEmailService
        ContractEmailService.send_confirmation_email(invitation, request)
    except Exception as e:
        logger.error(f"Error in direct accept post-signing logic: {e}")


class EmailTrackingPixelView(View):
    """
    Invisible 1x1 pixel to track email opens.
    Endpoint: /contracts/track/<token>/pixel.png
    """
    def get(self, request, token):
        try:
            invitation = get_object_or_404(ContractInvitation, token=token)
            
            # Only record first open to avoid noise
            if not invitation.email_opened_at:
                invitation.email_opened_at = timezone.now()
                if invitation.status == 'SENT':
                    invitation.status = 'OPENED'
                invitation.save()
                
                # Create tracking event
                ContractTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='EMAIL_OPENED',
                    metadata={
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': get_client_ip(request)
                    }
                )
        except Exception as e:
            # Silently fail for tracking pixels to not break image loading
            # But log the error for debugging
            logger.warning(f"Failed to track email open for token {token}: {e}")
        
        # Return 1x1 transparent PNG
        pixel = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        return HttpResponse(pixel, content_type='image/png')


class DirectAcceptView(View):
    """
    Direct acceptance from email link.
    Endpoint: /contracts/accept/<accept_token>/
    """
    def get(self, request, accept_token):
        try:
            invitation = get_object_or_404(ContractInvitation, accept_token=accept_token)
            
            # 1. Validate Status
            if invitation.status in ['VOIDED', 'EXPIRED']:
                return redirect('dbdint:contract_error')
            
            # 2. Check Expiration
            if invitation.is_expired():
                invitation.status = 'EXPIRED'
                invitation.save()
                return redirect('dbdint:contract_error')
            
            # 3. Record Click
            if not invitation.link_clicked_at:
                invitation.link_clicked_at = timezone.now()
                invitation.link_clicked_type = 'ACCEPT'
                invitation.save()
                
                ContractTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='ACCEPT_LINK_CLICKED',
                    metadata={'ip': get_client_ip(request)}
                )
            
            # 4. Execute Signing Logic
            create_and_sign_contract(invitation, request)
            
            # Set flag for success view security
            request.session['contract_just_signed'] = True
            
            return redirect('dbdint:contract_success')
            
        except Exception as e:
            logger.error(f"Error in direct accept: {e}")
            return redirect('dbdint:contract_error')


class ReviewLinkView(View):
    """
    Review link redirects to wizard.
    Endpoint: /contracts/review/<review_token>/
    """
    def get(self, request, review_token):
        try:
            invitation = get_object_or_404(ContractInvitation, review_token=review_token)
            
            # 1. Validate
            if invitation.status in ['VOIDED', 'EXPIRED']:
                return redirect('dbdint:contract_error')
            
            if invitation.is_expired():
                invitation.status = 'EXPIRED'
                invitation.save()
                return redirect('dbdint:contract_error')
            
            # 2. Record Click
            if not invitation.link_clicked_at:
                invitation.link_clicked_at = timezone.now()
                invitation.link_clicked_type = 'REVIEW'
                if invitation.status == 'SENT' or invitation.status == 'OPENED':
                    invitation.status = 'REVIEWING'
                invitation.save()
                
                ContractTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='REVIEW_LINK_CLICKED',
                    metadata={'ip': get_client_ip(request)}
                )
            
            # 3. Setup Session for Wizard
            request.session['invitation_id'] = str(invitation.id)
            
            # 4. Redirect to Wizard
            return redirect('dbdint:contract_wizard')
            
        except Exception as e:
            logger.error(f"Error in review link: {e}")
            return redirect('dbdint:contract_error')


class ContractPDFDownloadView(View):
    """
    Download signed contract PDF.
    Endpoint: /contracts/download/<uuid:invitation_id>/
    Requires authentication (Admin or Owner).
    """
    def get(self, request, invitation_id):
        from django.contrib.auth.mixins import LoginRequiredMixin
        
        if not request.user.is_authenticated:
            return redirect('dbdint:login')
            
        invitation = get_object_or_404(ContractInvitation, id=invitation_id)
        
        # Check permissions
        is_admin = request.user.is_staff or request.user.is_superuser
        is_owner = hasattr(request.user, 'interpreter') and invitation.interpreter == request.user.interpreter
        
        if not (is_admin or is_owner):
            return HttpResponse("Unauthorized", status=403)
            
        if not invitation.pdf_s3_key:
            return HttpResponse("PDF not generated yet.", status=404)
            
        try:
            # Get file from S3 using storage backend
            from custom_storages import ContractStorage
            storage = ContractStorage()
            
            # Open file
            f = storage.open(invitation.pdf_s3_key)
            
            # Return as download
            response = HttpResponse(f.read(), content_type='application/pdf')
            filename = f"Contract_{invitation.invitation_number}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return HttpResponse("Error retrieving file", status=500)


class ContractPublicVerifyView(View):
    """
    Public verification endpoint for QR codes.
    Endpoint: /verify/<str:invitation_number>/
    No authentication required (Public).
    """
    def get(self, request, invitation_number):
        # Allow checking via INV number
        invitation = get_object_or_404(ContractInvitation, invitation_number=invitation_number)
        
        status_color = "#dc3545" # Red
        status_text = "Invalid / Not Signed"
        status_icon = "✕"
        
        if invitation.status == 'SIGNED' and invitation.signed_at:
            status_color = "#76b041" # Green
            status_text = "Valid & Signed"
            status_icon = "✓"
        elif invitation.status == 'VOIDED':
            status_text = "Voided"
        elif invitation.status == 'EXPIRED':
            status_text = "Expired"
            
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Contract Verification</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: sans-serif; text-align: center; padding: 40px; background: #f8f9fa; }}
                .card {{ background: white; padding: 40px; border-radius: 12px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                .icon {{ font-size: 64px; color: {status_color}; margin-bottom: 20px; }}
                h1 {{ color: #1d3557; margin-top: 0; }}
                .meta {{ margin-top: 30px; color: #666; font-size: 14px; text-align: left; background: #f8f9fa; padding: 20px; border-radius: 8px; }}
                .meta p {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">{status_icon}</div>
                <h1>{status_text}</h1>
                <p>Contract Number: <strong>{invitation.invitation_number}</strong></p>
                <p>Interpreter: <strong>{invitation.interpreter.user.get_full_name()}</strong></p>
                
                <div class="meta">
                    <p>Signed: {invitation.signed_at.strftime('%Y-%m-%d %H:%M:%S') if invitation.signed_at else 'Pending'}</p>
                    <p>Status: {invitation.get_status_display()}</p>
                    <p>ID: {str(invitation.id)}</p>
                </div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)
