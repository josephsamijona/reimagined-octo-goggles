import logging
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
from app.models import ContractTrackingEvent
from custom_storages import ContractStorage

logger = logging.getLogger(__name__)

class ContractEmailService:
    """
    Service to handle sending contract-related emails with tracking.
    """
    
    @classmethod
    def send_invitation_email(cls, invitation, request):
        """
        Sends the contract invitation email with tracking pixel and magic links.
        """
        try:
            interpreter = invitation.interpreter
            user = interpreter.user
            
            # Construct URLs using request.build_absolute_uri() for dynamic environment support
            accept_path = reverse('dbdint:contract_direct_accept', kwargs={'accept_token': invitation.accept_token})
            review_path = reverse('dbdint:contract_review_link', kwargs={'review_token': invitation.review_token})
            tracking_path = reverse('dbdint:contract_tracking_pixel', kwargs={'token': invitation.token})
            
            accept_url = request.build_absolute_uri(accept_path)
            review_url = request.build_absolute_uri(review_path)
            tracking_pixel_url = request.build_absolute_uri(tracking_path)
            
            context = {
                'interpreter_name': user.get_full_name(),
                'accept_url': accept_url,
                'review_url': review_url,
                'tracking_pixel_url': tracking_pixel_url,
                'invitation_number': invitation.invitation_number
            }
            
            html_message = render_to_string('emails/contractnotif/invitation.html', context)
            
            logger.info(f"Sending contract invitation {invitation.invitation_number} to {user.email}")
            
            sent_count = send_mail(
                subject='Action Required: 2026 Independent Contractor Agreement',
                message='', # Plain text fallback (optional)
                html_message=html_message,
                from_email='JHBridge Compliance <contracts@jhbridgetranslation.com>',
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")
            # --- DEBUG LOGGING ---
            logger.error("--- EMAIL DEBUG INFO ---")
            logger.error(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not Set')}")
            logger.error(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not Set')}")
            logger.error(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not Set')}")
            logger.error(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not Set')}")
            logger.error(f"Current User Email: {user.email}")
            logger.error("------------------------")
            return False

    @classmethod
    def send_confirmation_email(cls, invitation, request):
        """
        Sends confirmation email with link to signed PDF and attaches the PDF.
        """
        try:
            interpreter = invitation.interpreter
            user = interpreter.user
            
            # Generate URL for PDF download view
            pdf_url = None
            if invitation.pdf_s3_key:
                pdf_path = reverse('dbdint:contract_pdf_download', kwargs={'invitation_id': invitation.id})
                pdf_url = request.build_absolute_uri(pdf_path)

            dashboard_path = reverse('dbdint:interpreter_dashboard')
            dashboard_url = request.build_absolute_uri(dashboard_path)
            
            context = {
                'interpreter_name': user.get_full_name(),
                'dashboard_url': dashboard_url,
                'pdf_url': pdf_url
            }
            
            html_message = render_to_string('emails/contractnotif/confirmation.html', context)
            subject = 'Agreement Confirmed: 2026 Contractor Agreement'
            from_email = 'JHBridge Compliance <contracts@jhbridgetranslation.com>'
            recipient_list = [user.email]
            
            # Create EmailMultiAlternatives object
            msg = EmailMultiAlternatives(
                subject=subject,
                body="Please find your signed agreement attached.", # Plain text fallback
                from_email=from_email,
                to=recipient_list
            )
            msg.attach_alternative(html_message, "text/html")
            
            # Attach PDF if available
            if invitation.pdf_s3_key:
                try:
                    storage = ContractStorage()
                    if storage.exists(invitation.pdf_s3_key):
                        with storage.open(invitation.pdf_s3_key, 'rb') as pdf_file:
                             pdf_content = pdf_file.read()
                             filename = f"Contract_{invitation.invitation_number}.pdf"
                             msg.attach(filename, pdf_content, 'application/pdf')
                             logger.info(f"Attached PDF {filename} to confirmation email.")
                    else:
                        logger.warning(f"PDF file not found in storage: {invitation.pdf_s3_key}")
                except Exception as pdf_err:
                     logger.error(f"Failed to attach PDF to email: {pdf_err}")

            msg.send(fail_silently=False)
            
            # Log success
            logger.info(f"Confirmation email sent to {user.email}")
            
            ContractTrackingEvent.objects.create(
                invitation=invitation,
                event_type='CONFIRMATION_SENT',
                metadata={'email': user.email}
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e}")
            # --- DEBUG LOGGING ---
            logger.error("--- EMAIL DEBUG INFO ---")
            logger.error(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not Set')}")
            logger.error(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not Set')}")
            logger.error(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Not Set')}")
            logger.error(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not Set')}")
            logger.error(f"Current User Email: {user.email}")
            logger.error("------------------------")
            # Re-raise to alert caller if needed
            raise e
