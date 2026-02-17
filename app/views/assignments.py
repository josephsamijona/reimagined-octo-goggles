import uuid
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event, Alarm

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from email.utils import make_msgid
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView, View

from ..mixins.assignment_mixins import AssignmentAdminMixin
from ..models import Assignment, AssignmentNotification
from ..services.assignment_notifications import AssignmentNotificationService

from .utils import TZ_BOSTON

class AssignmentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'trad/assignment.html'
    context_object_name = 'assignments'

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_queryset(self):
        return Assignment.objects.filter(
            interpreter=self.request.user.interpreter_profile
        ).order_by('start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interpreter = self.request.user.interpreter_profile
        now = timezone.now()
        
        # Assignments en attente de confirmation (PENDING)
        context['pending_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='PENDING'
        ).order_by('start_time')
        
        # Assignments confirmés à venir
        context['upcoming_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='CONFIRMED',
            start_time__gt=now
        ).order_by('start_time')
        
        # Assignments en cours
        context['in_progress_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='IN_PROGRESS'
        ).order_by('start_time')
        
        # Assignments terminés (derniers 30 jours)
        thirty_days_ago = now - timedelta(days=30)
        context['completed_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='COMPLETED',
            completed_at__gte=thirty_days_ago
        ).order_by('-completed_at')
        
        return context

@require_POST
@login_required
def accept_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_confirmed():
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    conflicting_assignments = Assignment.objects.filter(
        interpreter=request.user.interpreter_profile,
        status__in=['CONFIRMED', 'IN_PROGRESS'],
        start_time__lt=assignment.end_time,
        end_time__gt=assignment.start_time
    ).exists()
    
    if conflicting_assignments:
        return JsonResponse({
            'error': 'Schedule conflict',
            'message': 'You already have an assignment during this time period'
        }, status=400)
    
    if assignment.confirm():
        try:
            AssignmentNotificationService.send_confirmation_email(assignment)
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
            
        try:
            AssignmentNotificationService.notify_admin(assignment, 'accepted')
        except Exception as e:
            print(f"Error sending admin notification email: {str(e)}")
            
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Could not confirm assignment'}, status=400)

class AssignmentDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        
        if assignment.interpreter != request.user.interpreter_profile:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        data = {
            'id': assignment.id,
            'start_time': assignment.start_time.isoformat(),
            'end_time': assignment.end_time.isoformat(),
            'location': assignment.location,
            'city': assignment.city,
            'state': assignment.state,
            'zip_code': assignment.zip_code,
            'service_type': assignment.service_type.name,
            'source_language': assignment.source_language.name,
            'target_language': assignment.target_language.name,
            'interpreter_rate': str(assignment.interpreter_rate),
            'minimum_hours': assignment.minimum_hours,
            'status': assignment.status,
            'special_requirements': assignment.special_requirements or '',
            'notes': assignment.notes or '',
            'can_start': assignment.can_be_started(),
            'can_complete': assignment.can_be_completed(),
            'can_cancel': assignment.can_be_cancelled()
        }
        
        return JsonResponse(data)

@require_POST
@login_required
def reject_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_cancelled():
        return JsonResponse({'error': 'Invalid status'}, status=400)
        
    old_interpreter = assignment.cancel()
    if old_interpreter:
        try:
            AssignmentNotificationService.notify_admin(assignment, 'rejected', old_interpreter=old_interpreter)
        except Exception as e:
            print(f"Error sending rejection email: {str(e)}")
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Could not reject assignment'}, status=400)

@require_POST
@login_required
def start_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_started():
        return JsonResponse({'error': 'Invalid status'}, status=400)

    if timezone.now() + timedelta(minutes=15) < assignment.start_time:
        return JsonResponse({
            'error': 'Too early',
            'message': 'You can only start the assignment 15 minutes before the scheduled time'
        }, status=400)

    if assignment.start():
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Could not start assignment'}, status=400)

@require_POST
@login_required
def complete_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    
    if assignment.interpreter != request.user.interpreter_profile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if not assignment.can_be_completed():
        return JsonResponse({'error': 'Invalid status'}, status=400)
        
    if assignment.complete():
        try:
            AssignmentNotificationService.send_completion_email(assignment)
        except Exception as e:
            print(f"Error sending completion email: {str(e)}")
            
        return JsonResponse({
            'status': 'success',
            'payment': str(assignment.total_interpreter_payment)
        })
    
    return JsonResponse({'error': 'Could not complete assignment'}, status=400)

@login_required
def get_assignment_counts(request):
    if request.user.role != 'INTERPRETER':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    interpreter = request.user.interpreter_profile
    
    counts = {
        'pending': Assignment.objects.filter(interpreter=interpreter, status='PENDING').count(),
        'upcoming': Assignment.objects.filter(interpreter=interpreter, status='CONFIRMED').count(),
        'in_progress': Assignment.objects.filter(interpreter=interpreter, status='IN_PROGRESS').count(),
        'completed': Assignment.objects.filter(interpreter=interpreter, status='COMPLETED').count()
    }
    
    return JsonResponse(counts)

@require_POST
@login_required
def mark_assignments_as_read(request):
    interpreter = request.user.interpreter_profile
    AssignmentNotification.objects.filter(
        interpreter=interpreter,
        is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_assignments_count(request):
    if request.user.role != 'INTERPRETER':
        return JsonResponse({'count': 0})
        
    count = AssignmentNotification.get_unread_count(request.user.interpreter_profile)
    return JsonResponse({'count': count})


@login_required
@require_POST
def mark_assignment_complete(request, assignment_id):
    """
    Vue pour marquer une mission comme complétée.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"=== TENTATIVE DE COMPLETION - ASSIGNMENT {assignment_id} ===")
    
    try:
        # Récupération de l'assignment
        assignment = get_object_or_404(
            Assignment,
            id=assignment_id,
            interpreter=request.user.interpreter_profile
        )
        logger.info(f"Assignment trouvé - Status: {assignment.status}")

        # Vérification de la possibilité de completion
        if not assignment.can_be_completed():
            logger.error("[ÉCHEC] Conditions de completion non remplies")
            logger.error(f"- Status actuel: {assignment.status}")
            return JsonResponse({
                'success': False,
                'message': 'Assignment cannot be completed.'
            }, status=400)

        # Initialisation du mixin
        mixin = AssignmentAdminMixin()
        old_status = assignment.status

        # Mise à jour du statut
        assignment.status = Assignment.Status.COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save()
        logger.info(f"Assignment {assignment_id} marqué comme complété")

        # Gestion des notifications et changements de statut via le mixin
        try:
            # Gestion des changements liés au statut (paiements, etc.)
            mixin.handle_status_change(request, assignment, old_status)
            logger.info("Status change handled successfully")

            # Envoi de l'email de completion
            email_sent = mixin.send_assignment_email(request, assignment, 'completed')
            if email_sent:
                logger.info("Email de completion envoyé avec succès")
            else:
                logger.warning("L'email de completion n'a pas pu être envoyé")
                
            # Gestion des notifications de changement de statut
            mixin.handle_status_change_notification(request, assignment, old_status)
            logger.info("Notifications de changement de statut envoyées")

        except Exception as e:
            logger.error(f"Erreur lors de la gestion des notifications: {str(e)}")
            # On continue malgré l'erreur de notification car l'assignment est déjà complété

        return JsonResponse({
            'success': True,
            'message': 'Assignment marked as completed successfully.'
        })

    except Exception as e:
        logger.error(f"Erreur: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
