# tasks.py
import logging

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import User

logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email(user_id):
    try:
        user = User.objects.get(id=user_id)

        # Définir le contenu selon le rôle
        if user.role == 'CLIENT':
            template_name = 'emails/welcome_client.html'
            subject = 'Welcome to JHBRIDGE - Your Trusted Interpretation Partner'
            context = {
                'name': user.username,
                'mission': 'Providing exceptional interpretation services',
                'values': [
                    'Integrity',
                    'Excellence',
                    'Cultural Sensitivity',
                    'Global Reach',
                    'Professionalism',
                    'Communication'
                ]
            }
        else:  # INTERPRETER
            template_name = 'emails/welcome_interpreter.html'
            subject = 'Welcome to JHBRIDGE - Join Our Interpreter Network'
            context = {
                'name': user.username,
                'benefits': [
                    'Flexible Schedule',
                    'Professional Development',
                    'Supportive Community',
                    'Remote Opportunities'
                ]
            }

        # Rendre le template HTML
        html_message = render_to_string(template_name, context)

        # Envoyer l'email
        send_mail(
            subject=subject,
            message='',  # Version texte plain (optionnelle)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

    except User.DoesNotExist:
        logger.error("User %s not found", user_id)
    except Exception as e:
        logger.error("Error sending welcome email: %s", e)


@shared_task
def send_quote_request_status_email(quote_request_id):
    try:
        from .models import QuoteRequest

        quote_request = QuoteRequest.objects.select_related(
            'client__user',
            'service_type',
            'source_language',
            'target_language'
        ).get(id=quote_request_id)

        status_templates = {
            'PENDING': {
                'template': 'emails/quote_request_pending.html',
                'subject': 'Your Quote Request Has Been Received - JHBRIDGE'
            },
            'PROCESSING': {
                'template': 'emails/quote_request_processing.html',
                'subject': 'Your Quote Request is Being Processed - JHBRIDGE'
            },
            'QUOTED': {
                'template': 'emails/quote_request_quoted.html',
                'subject': 'Your Quote is Ready - JHBRIDGE'
            },
            'ACCEPTED': {
                'template': 'emails/quote_request_accepted.html',
                'subject': 'Quote Request Accepted - JHBRIDGE'
            },
            'REJECTED': {
                'template': 'emails/quote_request_rejected.html',
                'subject': 'Quote Request Status Update - JHBRIDGE'
            },
            'EXPIRED': {
                'template': 'emails/quote_request_expired.html',
                'subject': 'Quote Request Expired - JHBRIDGE'
            }
        }

        status_info = status_templates.get(quote_request.status)
        if not status_info:
            return

        # Contexte commun pour tous les templates
        context = {
            'client_name': quote_request.client.user.get_full_name() or quote_request.client.user.username,
            'service_type': quote_request.service_type.name,
            'requested_date': quote_request.requested_date,
            'duration': quote_request.duration,
            'location': f"{quote_request.location}, {quote_request.city}, {quote_request.state} {quote_request.zip_code}",
            'source_language': quote_request.source_language.name,
            'target_language': quote_request.target_language.name,
            'request_id': quote_request.id
        }

        # Rendre le template HTML
        html_message = render_to_string(status_info['template'], context)

        # Envoyer l'email
        send_mail(
            subject=status_info['subject'],
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[quote_request.client.user.email],
            html_message=html_message,
            fail_silently=False,
        )

    except Exception as e:
        logger.error("Error sending quote request status email: %s", e)


@shared_task
def send_quote_status_email(quote_id):
    """Send status email for a Quote (SENT, ACCEPTED, REJECTED, etc.)."""
    try:
        from .models import Quote

        quote = Quote.objects.select_related(
            'quote_request__client__user',
            'quote_request__service_type',
        ).get(id=quote_id)

        status_templates = {
            'SENT': {
                'template': 'emails/quote_sent.html',
                'subject': 'Your Quote is Ready for Review - JHBRIDGE',
            },
            'ACCEPTED': {
                'template': 'emails/quote_accepted.html',
                'subject': 'Quote Accepted - JHBRIDGE',
            },
            'REJECTED': {
                'template': 'emails/quote_rejected.html',
                'subject': 'Quote Status Update - JHBRIDGE',
            },
            'EXPIRED': {
                'template': 'emails/quote_expired.html',
                'subject': 'Quote Expired - JHBRIDGE',
            },
            'CANCELLED': {
                'template': 'emails/quote_cancelled.html',
                'subject': 'Quote Cancelled - JHBRIDGE',
            },
        }

        status_info = status_templates.get(quote.status)
        if not status_info:
            return

        client_user = quote.quote_request.client.user
        context = {
            'client_name': client_user.get_full_name() or client_user.username,
            'reference_number': quote.reference_number,
            'amount': quote.amount,
            'tax_amount': quote.tax_amount,
            'valid_until': quote.valid_until,
            'service_type': quote.quote_request.service_type.name,
            'quote_id': quote.id,
        }

        html_message = render_to_string(status_info['template'], context)

        send_mail(
            subject=status_info['subject'],
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client_user.email],
            html_message=html_message,
            fail_silently=False,
        )

    except Exception as e:
        logger.error("Error sending quote status email: %s", e)


@shared_task
def send_assignment_status_email(assignment_id):
    """Send status email for an Assignment (CONFIRMED, COMPLETED, CANCELLED, etc.)."""
    try:
        from .models import Assignment

        assignment = Assignment.objects.select_related(
            'interpreter__user',
            'client',
            'service_type',
            'source_language',
            'target_language',
        ).get(id=assignment_id)

        status_templates = {
            'PENDING': {
                'template': 'emails/assignment_pending.html',
                'subject': 'New Assignment Available - JHBRIDGE',
            },
            'CONFIRMED': {
                'template': 'emails/assignment_confirmed.html',
                'subject': 'Assignment Confirmed - JHBRIDGE',
            },
            'IN_PROGRESS': {
                'template': 'emails/assignment_in_progress.html',
                'subject': 'Assignment In Progress - JHBRIDGE',
            },
            'COMPLETED': {
                'template': 'emails/assignment_completed.html',
                'subject': 'Assignment Completed - JHBRIDGE',
            },
            'CANCELLED': {
                'template': 'emails/assignment_cancelled.html',
                'subject': 'Assignment Cancelled - JHBRIDGE',
            },
            'NO_SHOW': {
                'template': 'emails/assignment_no_show.html',
                'subject': 'Assignment No-Show Recorded - JHBRIDGE',
            },
        }

        status_info = status_templates.get(assignment.status)
        if not status_info:
            return

        # Send to interpreter if assigned
        recipient = None
        context = {
            'assignment_id': assignment.id,
            'service_type': assignment.service_type.name if assignment.service_type else '',
            'start_time': assignment.start_time,
            'end_time': assignment.end_time,
            'location': f"{assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}",
            'source_language': assignment.source_language.name if assignment.source_language else '',
            'target_language': assignment.target_language.name if assignment.target_language else '',
            'status': assignment.status,
        }

        if assignment.interpreter and assignment.interpreter.user:
            recipient = assignment.interpreter.user.email
            context['interpreter_name'] = (
                assignment.interpreter.user.get_full_name()
                or assignment.interpreter.user.username
            )

        if not recipient:
            return

        html_message = render_to_string(status_info['template'], context)

        send_mail(
            subject=status_info['subject'],
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )

    except Exception as e:
        logger.error("Error sending assignment status email: %s", e)
