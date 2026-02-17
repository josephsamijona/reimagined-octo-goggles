import logging
import uuid
import pytz
import smtplib
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email import encoders
from email.utils import make_msgid
from icalendar import Calendar, Event, vCalAddress, Alarm

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.urls import reverse

from app.models import Assignment, User

logger = logging.getLogger(__name__)

# Définir le timezone de Boston
BOSTON_TZ = pytz.timezone('America/New_York')

class AssignmentNotificationService:
    """
    Service central pour la gestion des notifications liées aux missions (Assignments).
    Gère la génération des fichiers ICS et l'envoi des emails aux interprètes et administrateurs.
    """

    @staticmethod
    def generate_ics_content(assignment, method='REQUEST', status='CONFIRMED'):
        """
        Génère le contenu d'un fichier ICS pour une mission.
        """
        cal = Calendar()
        cal.add('PRODID', '-//JHBRIDGE Assignment System//EN')
        cal.add('VERSION', '2.0')
        cal.add('METHOD', method)

        event = Event()
        event.add('SUMMARY', f"Interpretation Assignment - {assignment.service_type.name}")
        
        start_time = assignment.start_time.astimezone(BOSTON_TZ)
        end_time = assignment.end_time.astimezone(BOSTON_TZ)
        
        event.add('DTSTART', start_time)
        event.add('DTEND', end_time)
        event.add('DTSTAMP', timezone.now().astimezone(pytz.UTC))
        event.add('CREATED', timezone.now().astimezone(pytz.UTC))
        event.add('LOCATION', f"{assignment.location}, {assignment.city}, {assignment.state}")
        event.add('STATUS', status)
        
        client_name = assignment.client.company_name if assignment.client else assignment.client_name
        description = (
            f"Client: {client_name}\n"
            f"Service: {assignment.service_type.name}\n"
            f"Languages: {assignment.source_language.name} -> {assignment.target_language.name}\n"
            f"Location: {assignment.location}, {assignment.city}, {assignment.state} {assignment.zip_code}\n\n"
            f"Special Requirements: {assignment.special_requirements or 'None'}\n\n"
            f"Rate: ${assignment.interpreter_rate}/hour\n"
        )
        event.add('DESCRIPTION', description)
        
        # UID unique et stable pour l'événement
        event.add('UID', f"assignment-{assignment.id}@jhbridge.com")

        # ORGANIZER
        organizer_email = settings.DEFAULT_FROM_EMAIL
        organizer = vCalAddress(f"MAILTO:{organizer_email}")
        organizer.params['CN'] = "JHBridge System"
        event['ORGANIZER'] = organizer

        # ATTENDEE (Interprète)
        if assignment.interpreter:
            attendee = vCalAddress(f"MAILTO:{assignment.interpreter.user.email}")
            attendee.params['CN'] = assignment.interpreter.user.get_full_name()
            attendee.params['RSVP'] = 'TRUE'
            event.add('ATTENDEE', attendee)

        # Alarmes (Rappels)
        if status == 'CONFIRMED':
            reminders = [
                (timedelta(days=-2), 'Reminder: Assignment in 2 days'),
                (timedelta(hours=-24), 'Reminder: Assignment tomorrow'),
                (timedelta(hours=-2), 'Reminder: Assignment in 2 hours'),
                (timedelta(minutes=-30), 'Reminder: Assignment in 30 minutes'),
            ]
            for trigger, desc in reminders:
                alarm = Alarm()
                alarm.add('ACTION', 'DISPLAY')
                alarm.add('DESCRIPTION', desc)
                alarm.add('TRIGGER', trigger)
                event.add_component(alarm)

        cal.add_component(event)
        return cal.to_ical()

    @classmethod
    def send_confirmation_email(cls, assignment):
        """
        Envoie l'email de confirmation à l'interprète avec l'invitation ICS.
        """
        interpreter = assignment.interpreter
        if not interpreter:
            return False

        client_name = assignment.client.company_name if assignment.client else assignment.client_name
        
        context = {
            'interpreter_name': interpreter.user.get_full_name(),
            'assignment': assignment, # Garder pour compatibilité template
            'assignment_id': assignment.id,
            'client_name': client_name,
            'client_phone': assignment.client_phone,
            'start_time': assignment.start_time.astimezone(BOSTON_TZ),
            'end_time': assignment.end_time.astimezone(BOSTON_TZ),
            'location': f"{assignment.location}, {assignment.city}, {assignment.state}",
            'service_type': assignment.service_type.name,
            'source_language': assignment.source_language.name,
            'target_language': assignment.target_language.name,
            'rate': assignment.interpreter_rate,
            'interpreter_rate': assignment.interpreter_rate, # Compatibilité
            'special_requirements': assignment.special_requirements or 'None'
        }

        # Essayer d'utiliser le template HTML existant s'il convient, sinon fallback
        # Nous allons utiliser un template unifié ou celui de assignment_views.py qui semble complet
        template_name = 'emails/assignments/interpreter_assignment_confirmation.html'
        
        try:
            html_message = render_to_string(template_name, context)
        except Exception:
            # Fallback si le template n'existe pas, utiliser celui de views/assignments.py
            html_message = render_to_string('emails/assignment_confirmation.html', context)

        text_message = strip_tags(html_message)
        
        unique_id = f"ID-{uuid.uuid4().hex[:8].upper()}"
        subject = f'Assignment Confirmation #{assignment.id} - Calendar Invitation [{unique_id}]'
        
        unique_message_id = make_msgid(domain="jhbridge.com")
        unique_ref = f"assignment-{assignment.id}-{uuid.uuid4().hex}"

        headers = {
            'Message-ID': unique_message_id,
            'X-Entity-Ref-ID': unique_ref,
            'Thread-Topic': f"Assignment {assignment.id} confirmation {uuid.uuid4().hex[:6]}",
            'Thread-Index': uuid.uuid4().hex,
            'X-No-Threading': 'true'
        }

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[interpreter.user.email],
            headers=headers,
        )
        email.attach_alternative(html_message, "text/html")

        # PJ ICS
        ics_data = cls.generate_ics_content(assignment, method='REQUEST')
        ical_part = MIMEBase('text', 'calendar', method='REQUEST', name='invite.ics')
        ical_part.set_payload(ics_data)
        encoders.encode_base64(ical_part)
        ical_part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
        ical_part.add_header('Content-class', 'urn:content-classes:calendarmessage')
        email.attach(ical_part)

        return email.send(fail_silently=False)

    @classmethod
    def send_completion_email(cls, assignment):
        """
        Envoie l'email de confirmation de complétion (fin de mission).
        """
        if not assignment.interpreter:
            return False

        duration = assignment.end_time - assignment.start_time
        hours = duration.total_seconds() / 3600
        total_payment = assignment.total_interpreter_payment
        
        start_local = timezone.localtime(assignment.start_time, BOSTON_TZ)
        end_local = timezone.localtime(assignment.end_time, BOSTON_TZ)
        completed_local = timezone.localtime(assignment.completed_at, BOSTON_TZ) if assignment.completed_at else None

        context = {
            'interpreter_name': assignment.interpreter.user.get_full_name(),
            'assignment_id': assignment.id,
            'start_time': start_local.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': end_local.strftime('%I:%M %p'),
            'location': assignment.location,
            'city': assignment.city,
            'state': assignment.state,
            'service_type': assignment.service_type.name,
            'source_language': assignment.source_language.name,
            'target_language': assignment.target_language.name,
            'interpreter_rate': assignment.interpreter_rate,
            'duration_hours': round(hours, 2),
            'total_payment': total_payment,
            'completed_at': completed_local.strftime('%B %d, %Y at %I:%M %p') if completed_local else '',
            'minimum_hours': assignment.minimum_hours
        }

        email_html = render_to_string('emails/assignment_completion.html', context)
        subject = 'Assignment Completion Confirmation - JHBRIDGE'

        email = EmailMessage(
            subject=subject,
            body=email_html,
            from_email='noreply@jhbridge.com',
            to=[assignment.interpreter.user.email],
        )
        
        email.extra_headers = {
            'Message-ID': make_msgid(domain='jhbridge.com'),
            'X-Entity-Ref-ID': str(uuid.uuid4()),
        }
        email.content_subtype = "html"
        return email.send(fail_silently=False)

    @classmethod
    def send_decline_confirmation(cls, assignment, interpreter):
        """
        Envoie confirmation de refus à l'interprète.
        """
        client_name = assignment.client.company_name if assignment.client else assignment.client_name
        
        context = {
            'interpreter_name': interpreter.user.get_full_name(),
            'assignment': assignment,
            'client_name': client_name,
            'client_phone': assignment.client_phone,
            'start_time': assignment.start_time.astimezone(BOSTON_TZ),
        }
        
        # Template existant
        template_name = 'emails/assignments/interprter_assignment_decline_confirmation.html'
        html_message = render_to_string(template_name, context)
        text_message = strip_tags(html_message)
        
        unique_id = f"ID-{uuid.uuid4().hex[:8].upper()}"
        subject = f'Assignment Declined - Confirmation #{assignment.id} [{unique_id}]'
        
        unique_message_id = make_msgid(domain="jhbridge.com")
        
        headers = {
            'Message-ID': unique_message_id,
            'X-No-Threading': 'true'
        }
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[interpreter.user.email],
            headers=headers,
        )
        email.attach_alternative(html_message, "text/html")
        return email.send(fail_silently=False)

    @classmethod
    def notify_admin(cls, assignment, action, interpreter=None, old_interpreter=None):
        """
        Notifie les admins d'une action (accepted, declined, rejected).
        """
        interpreter = interpreter or assignment.interpreter
        
        admin_users = User.objects.filter(role='ADMIN', is_active=True)
        if not admin_users.exists():
            return False
        admin_emails = [u.email for u in admin_users if u.email]

        if action == 'accepted':
            template = 'emails/assignments/admin_assignment_response.html' # ou 'emails/admin_assignment_notification.html'
            # Utilisons le template le plus riche. Celui de assignment_views.py (notifmail) semble bien.
            context = {
                'interpreter_name': interpreter.user.get_full_name(),
                'assignment': assignment,
                'client_name': assignment.client.company_name if assignment.client else assignment.client_name,
                'action': action,
                'admin_url': reverse('admin:app_assignment_change', args=[assignment.id])
            }
            subject = f'Assignment #{assignment.id} {action} by {interpreter.user.get_full_name()}'
            
            # Si on veut inclure l'ICS pour l'admin (comme dans views/assignments.py)
            ics_data = cls.generate_ics_content(assignment, method='REQUEST')
            has_ics = True

        elif action == 'declined':
            # Notification simple
            template = 'emails/assignments/admin_assignment_response.html'
            context = {
                'interpreter_name': interpreter.user.get_full_name(),
                'assignment': assignment,
                'action': action,
                'client_name': assignment.client.company_name if assignment.client else assignment.client_name,
                'admin_url': reverse('admin:app_assignment_change', args=[assignment.id])
            }
            subject = f'Assignment #{assignment.id} {action} by {interpreter.user.get_full_name()}'
            has_ics = False

        elif action == 'rejected' and old_interpreter:
            # Cas où l'interprète annule une mission déjà acceptée (dans le dashboard)
            template = 'emails/assignment_rejection_notification.html'
            context = { # Contexte spécifique à ce template
                'assignment_id': assignment.id,
                'interpreter_name': old_interpreter.user.get_full_name(),
                'interpreter_email': old_interpreter.user.email,
                'client_name': assignment.client.company_name if assignment.client else assignment.client_name,
                'start_time': timezone.localtime(assignment.start_time, BOSTON_TZ).strftime("%B %d, %Y at %I:%M %p"),
                'end_time': timezone.localtime(assignment.end_time, BOSTON_TZ).strftime("%I:%M %p"),
                'location': assignment.location,
                'city': assignment.city,
                'state': assignment.state,
                'service_type': assignment.service_type.name,
                'source_language': assignment.source_language.name,
                'target_language': assignment.target_language.name,
            }
            subject = f'ACTION REQUIRED: Assignment #{assignment.id} Rejected by Interpreter'
            has_ics = False
        else:
            return False

        html_message = render_to_string(template, context)
        text_message = strip_tags(html_message)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        email.attach_alternative(html_message, "text/html")
        
        if has_ics:
             ical_part = MIMEBase('text', 'calendar', method='REQUEST', name='admin_invite.ics')
             ical_part.set_payload(ics_data)
             encoders.encode_base64(ical_part)
             ical_part.add_header('Content-Disposition', 'attachment; filename="admin_invite.ics"')
             email.attach(ical_part)

        return email.send(fail_silently=False)
