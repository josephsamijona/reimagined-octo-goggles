from django.views.generic import TemplateView
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.signing import Signer, BadSignature
from datetime import datetime, timedelta

from ..models import Assignment, AuditLog
from ..services.assignment_notifications import AssignmentNotificationService
from .utils import BOSTON_TZ


class AssignmentResponseBaseMixin:
    """Base mixin for handling assignment responses (accept/decline)."""
    
    def verify_token(self, token, action):
        """
        Vérifie la validité du token signé (assignment_id, action, timestamp).
        Retourne l'ID de l'Assignment si valide, sinon None.
        """
        signer = Signer()
        try:
            data = signer.unsign(token)
            assignment_id, token_action, timestamp, _ = data.split(':', 3)
            
            # Vérifie que l'action correspond
            if token_action != action:
                return None

            # Vérifie l'expiration (24h) en timezone de Boston
            token_time = datetime.fromtimestamp(float(timestamp))
            token_time = BOSTON_TZ.localize(token_time)
            if timezone.now().astimezone(BOSTON_TZ) - token_time > timedelta(hours=24):
                return None
            
            return int(assignment_id)
        
        except (BadSignature, ValueError):
            return None

    def handle_expired_token(self, request):
        """
        Rend une page indiquant que le lien a expiré ou n'est plus valide.
        """
        return render(request, 'pages/token_expired.html', {
            'title': _('Link Expired'),
            'message': _('This link has expired or is no longer valid.'),
            'login_url': reverse('dbdint:login')
        })

    def handle_already_processed(self, request):
        """
        Rend une page indiquant que l'Assignment a déjà été traité.
        """
        return render(request, 'pages/already_processed.html', {
            'title': _('Already Processed'),
            'message': _('This assignment has already been processed.'),
            'login_url': reverse('dbdint:login')
        })

    def log_action(self, assignment, action, user, changes=None):
        """
        Log l'action réalisée sur l'Assignment dans l'AuditLog.
        """
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name='Assignment',
            object_id=str(assignment.id),
            changes=changes or {}
        )


class AssignmentAcceptView(AssignmentResponseBaseMixin, TemplateView):
    """
    Vue appelée lorsqu'un interprète clique sur le lien d'acceptation.
    Vérifie le token, met à jour le statut de l'Assignment et envoie
    la notification + invitation calendrier.
    """
    template_name = 'pages/accept_success.html'
    
    def get(self, request, assignment_token):
        assignment_id = self.verify_token(assignment_token, 'accept')
        
        if not assignment_id:
            return self.handle_expired_token(request)
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            
            if assignment.status != Assignment.Status.PENDING:
                return self.handle_already_processed(request)

            # Update assignment status
            old_status = assignment.status
            assignment.status = Assignment.Status.CONFIRMED
            assignment.save()

            # Notifications
            AssignmentNotificationService.send_confirmation_email(assignment)
            AssignmentNotificationService.notify_admin(assignment, 'accepted')

            # Log
            self.log_action(
                assignment=assignment,
                action='ASSIGNMENT_ACCEPTED',
                user=assignment.interpreter.user,
                changes={
                    'old_status': old_status,
                    'new_status': Assignment.Status.CONFIRMED
                }
            )

            # Contexte pour la page de confirmation
            client_name = assignment.client.company_name if assignment.client else assignment.client_name
            
            context = {
                'title': _('Assignment Accepted'),
                'assignment': assignment,
                'interpreter_name': assignment.interpreter.user.get_full_name(),
                'client_name': client_name,
                'start_time': assignment.start_time.astimezone(BOSTON_TZ),
                'end_time': assignment.end_time.astimezone(BOSTON_TZ),
                'location': f"{assignment.location}, {assignment.city}, {assignment.state}",
                'login_url': reverse('dbdint:login')
            }
            
            return render(request, self.template_name, context)
        
        except Assignment.DoesNotExist:
            return render(request, 'pages/not_found.html', {
                'title': _('Assignment Not Found'),
                'message': _('The requested assignment could not be found.'),
                'login_url': reverse('dbdint:login')
            })


class AssignmentDeclineView(AssignmentResponseBaseMixin, TemplateView):
    """
    Vue appelée lorsqu'un interprète clique sur le lien de refus.
    Vérifie le token, met à jour le statut de l'Assignment et notifie
    l'interprète et l'admin.
    """
    template_name = 'pages/decline_success.html'
    
    def get(self, request, assignment_token):
        assignment_id = self.verify_token(assignment_token, 'decline')
        
        if not assignment_id:
            return self.handle_expired_token(request)
        
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            
            if assignment.status != Assignment.Status.PENDING:
                return self.handle_already_processed(request)

            interpreter = assignment.interpreter
            old_status = assignment.status
            
            # Update assignment status + remove interpreter
            assignment.status = Assignment.Status.CANCELLED
            assignment.interpreter = None
            assignment.save()

            # Notifications
            AssignmentNotificationService.send_decline_confirmation(assignment, interpreter)
            AssignmentNotificationService.notify_admin(assignment, 'declined', interpreter=interpreter)

            # Log
            self.log_action(
                assignment=assignment,
                action='ASSIGNMENT_DECLINED',
                user=interpreter.user,
                changes={
                    'old_status': old_status,
                    'new_status': Assignment.Status.CANCELLED,
                    'reason': 'declined_by_interpreter'
                }
            )

            # Contexte pour la page de confirmation
            client_name = assignment.client.company_name if assignment.client else assignment.client_name
            
            context = {
                'title': _('Assignment Declined'),
                'interpreter_name': interpreter.user.get_full_name(),
                'client_name': client_name,
                'start_time': assignment.start_time.astimezone(BOSTON_TZ),
                'login_url': reverse('dbdint:login')
            }
            
            return render(request, self.template_name, context)
        
        except Assignment.DoesNotExist:
            return render(request, 'pages/not_found.html', {
                'title': _('Assignment Not Found'),
                'message': _('The requested assignment could not be found.'),
                'login_url': reverse('dbdint:login')
            })
