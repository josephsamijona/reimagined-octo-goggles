import logging
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
from app.models import ContractTrackingEvent, ContractReminder
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
            
            # Construct URLs using hardcoded base URL based on user preference
            base_url = "https://jhbridges.up.railway.app"
            
            accept_path = reverse('dbdint:contract_direct_accept', kwargs={'accept_token': invitation.accept_token})
            review_path = reverse('dbdint:contract_review_link', kwargs={'review_token': invitation.review_token})
            tracking_path = reverse('dbdint:contract_tracking_pixel', kwargs={'token': invitation.token})
            
            accept_url = f"{base_url}{accept_path}"
            review_url = f"{base_url}{review_path}"
            tracking_pixel_url = f"{base_url}{tracking_path}"
            
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

class ContractReminderService:
    """
    Service to handle sending tiered contract reminders.
    Supports 3 levels of urgency.
    """
    
    @classmethod
    def send_level_1(cls, interpreter, invitation, triggered_by=None):
        """Send Level 1 Reminder (Gentle nudge - Day 3)"""
        return cls._send_reminder(
            interpreter, 
            invitation, 
            level=1, 
            subject="Reminder: Please Sign Your JHBridge Agreement", 
            template="emails/contractnotif/reminder_level_1.html",
            triggered_by=triggered_by
        )

    @classmethod
    def send_level_2(cls, interpreter, invitation, triggered_by=None):
        """Send Level 2 Reminder (Warning - Day 7)"""
        return cls._send_reminder(
            interpreter, 
            invitation, 
            level=2, 
            subject="Urgent: Your JHBridge Agreement is Pending", 
            template="emails/contractnotif/reminder_level_2.html",
            triggered_by=triggered_by
        )

    @classmethod
    def send_level_3(cls, interpreter, invitation, triggered_by=None):
        """Send Level 3 Reminder (Final Notice & Block - Day 14)"""
        return cls._send_reminder(
            interpreter, 
            invitation, 
            level=3, 
            subject="Final Notice: Account Blocked Due to Missing Agreement", 
            template="emails/contractnotif/reminder_level_3.html",
            triggered_by=triggered_by
        )

    @classmethod
    def _send_reminder(cls, interpreter, invitation, level, subject, template, triggered_by=None):
        try:
            user = interpreter.user
            
            # Use invitation context if available, otherwise fallback
            contract_url = "https://jhbridgetranslation.com/dashboard/" # Default fallback
            if invitation:
                 # TODO: Ideally should pass request object here for absolute URI, 
                 # but for background tasks or admin actions, we might need SITE_URL
                 # For now, simplistic approach using dashboard or direct link if possible
                 pass 

            context = {
                'interpreter_name': user.get_full_name(),
                'contract_url': contract_url, # Template should handle the precise link logic or updated later
                'days_pending': [3, 7, 14][level-1]
            }
            
            html_message = render_to_string(template, context)
            
            send_mail(
                subject=subject,
                message='',
                html_message=html_message,
                from_email='JHBridge Compliance <contracts@jhbridgetranslation.com>',
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Log the reminder
            ContractReminder.objects.create(
                interpreter=interpreter,
                invitation=invitation,
                level=level,
                sent_by=triggered_by
            )
            
            logger.info(f"Level {level} reminder sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reminder level {level}: {e}")
            return False

class ContractViolationService:
    """
    Service to handle contract violations and suspensions.
    """
    
    @classmethod
    def send_suspension_email(cls, interpreter, reason, triggered_by=None):
        """Send account suspension email due to contract violation"""
        try:
            user = interpreter.user
            
            context = {
                'interpreter_name': user.get_full_name(),
                'reason': reason,
                'support_email': 'support@jhbridgetranslation.com'
            }
            
            html_message = render_to_string('emails/contractnotif/account_suspended.html', context)
            
            send_mail(
                subject='Important: Your JHBridge Account Has Been Suspended',
                message='',
                html_message=html_message,
                from_email='JHBridge Legal <legal@jhbridgetranslation.com>',
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Log event (using ContractTrackingEvent if invitation exists, or custom log)
            # For now just log to file
            logger.info(f"Suspension email sent to {user.email} for reason: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send suspension email: {e}")
            return False
