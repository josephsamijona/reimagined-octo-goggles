import logging
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
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
            
            base_url = getattr(settings, 'SITE_URL', 'https://portal.jhbridgetranslation.com').rstrip('/')

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

class OnboardingEmailService:
    """Service for sending onboarding invitation emails."""

    @classmethod
    def send_invitation_email(cls, onboarding_invitation, request=None, template_type=None):
        """Send the onboarding invitation email with tracking pixel."""
        try:
            base_url = getattr(settings, 'SITE_URL', 'https://portal.jhbridgetranslation.com').rstrip('/')

            onboarding_path = reverse('dbdint:onboarding_entry', kwargs={'token': onboarding_invitation.token})
            tracking_path = reverse('dbdint:onboarding_tracking_pixel', kwargs={'token': onboarding_invitation.token})

            onboarding_url = f"{base_url}{onboarding_path}"
            tracking_pixel_url = f"{base_url}{tracking_path}"

            context = {
                'first_name': onboarding_invitation.first_name,
                'last_name': onboarding_invitation.last_name,
                'full_name': onboarding_invitation.full_name,
                'onboarding_url': onboarding_url,
                'tracking_pixel_url': tracking_pixel_url,
                'invitation_number': onboarding_invitation.invitation_number,
            }

            template_name = 'emails/onboarding/invitation.html'
            subject = 'Welcome to JHBridge Translation Services!'

            if template_type == 'RESEND_ISSUE':
                template_name = 'emails/onboarding/resend_issue.html'
                subject = 'Help with your JHBridge Onboarding'
            elif template_type == 'STUCK_WELCOME':
                template_name = 'emails/onboarding/resend_stuck_welcome.html'
                subject = 'Action Required: Finish your Welcome Tour'
            elif template_type == 'STUCK_ACCOUNT':
                template_name = 'emails/onboarding/resend_stuck_account.html'
                subject = 'Reminder: Complete your JHBridge Profile'
            elif template_type == 'STUCK_CONTRACT':
                template_name = 'emails/onboarding/resend_stuck_contract.html'
                subject = 'One last step: Sign your Agreement'
            elif template_type == 'STUCK_OPENED':
                template_name = 'emails/onboarding/resend_stuck_opened.html'
                subject = 'Ready to start your JHBridge Onboarding?'

            html_message = render_to_string(template_name, context)

            logger.info(f"Sending onboarding invitation {onboarding_invitation.invitation_number} to {onboarding_invitation.email}")

            sent_count = send_mail(
                subject=subject,
                message='',
                html_message=html_message,
                from_email='JHBridge Team <team@jhbridgetranslation.com>',
                recipient_list=[onboarding_invitation.email],
                fail_silently=False,
            )

            return sent_count > 0

        except Exception as e:
            logger.error(f"Failed to send onboarding invitation email: {e}", exc_info=True)
            logger.error(f"EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'Not Set')}")
            logger.error(f"RESEND_API_KEY set: {bool(getattr(settings, 'RESEND_API_KEY', None))}")
            return False


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
            
            base_url = getattr(settings, 'SITE_URL', 'https://portal.jhbridgetranslation.com').rstrip('/')
            if invitation:
                review_path = reverse('dbdint:contract_review_link', kwargs={'review_token': invitation.review_token})
                accept_path = reverse('dbdint:contract_direct_accept', kwargs={'accept_token': invitation.accept_token})
                contract_url = f"{base_url}{review_path}"
                accept_url = f"{base_url}{accept_path}"
            else:
                dashboard_path = reverse('dbdint:interpreter_dashboard')
                contract_url = f"{base_url}{dashboard_path}"
                accept_url = contract_url

            context = {
                'interpreter_name': user.get_full_name(),
                'contract_url': contract_url,
                'accept_url': accept_url,
                'days_pending': [3, 7, 14][level-1],
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


class PayrollEmailService:
    """Send pay stub emails with HTML body and PDF attachment."""

    FROM_EMAIL = 'JHBridge Payroll <payroll@jhbridgetranslation.com>'

    @classmethod
    def send_stub(cls, stub, pdf_bytes: bytes) -> bool:
        """
        Send a pay stub email to the interpreter.

        Args:
            stub: PayrollDocument instance (with prefetched services/reimbursements/deductions)
            pdf_bytes: Raw PDF content as bytes
        Returns:
            True on success, False on failure
        """
        try:
            services = list(stub.services.all())
            reimbursements = list(stub.reimbursements.all())
            deductions = list(stub.deductions.all())

            context = {
                'interpreter_name': stub.interpreter_name,
                'document_number': stub.document_number,
                'services': services,
                'reimbursements': reimbursements,
                'deductions': deductions,
                'total_amount': stub.total_amount,
                'company_address': stub.company_address,
            }

            html_body = render_to_string('emails/payroll_stub.html', context)

            email = EmailMessage(
                subject=f'Pay Stub {stub.document_number} — JHBridge Translation',
                body=html_body,
                from_email=cls.FROM_EMAIL,
                to=[stub.interpreter_email],
            )
            email.content_subtype = 'html'
            email.attach(
                f'paystub-{stub.document_number}.pdf',
                pdf_bytes,
                'application/pdf',
            )
            email.send(fail_silently=False)

            logger.info(f"Pay stub {stub.document_number} emailed to {stub.interpreter_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to email pay stub {stub.document_number}: {e}")
            return False
