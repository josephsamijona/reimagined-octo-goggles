from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
import logging

from ...models import (
    User,
    QuoteRequest,
    Assignment,
    Payment,
    Notification
)

logger = logging.getLogger(__name__)

class ClientDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'client/home.html'
    login_url = 'dbdint:login'
    permission_denied_message = "Access denied. This area is for clients only."
    
    def test_func(self):
        user = self.request.user
        
        logger.debug(
            "Testing client dashboard access",
            extra={
                'user_id': user.id,
                'role': getattr(user, 'role', 'NO_ROLE'),
                'has_client_profile': hasattr(user, 'client_profile'),
                'registration_complete': user.registration_complete
            }
        )
        
        if not user.role:
            logger.error(f"User {user.id} has no role assigned")
            return False

        return (user.role == User.Roles.CLIENT and 
                hasattr(user, 'client_profile') and 
                user.registration_complete)

    def handle_no_permission(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return redirect(self.login_url)
        
        if not user.role:
            messages.error(self.request, "Your account setup is incomplete. Please contact support.")
            return redirect('dbdint:home')
            
        if user.role == User.Roles.CLIENT and not user.registration_complete:
            if 'registration_step1' in self.request.session:
                return redirect('dbdint:client_register_step2')
            else:
                return redirect('dbdint:client_register')
                
        if user.role == User.Roles.INTERPRETER:
            messages.warning(self.request, "This area is for clients only. Redirecting to interpreter dashboard.")
            return redirect('dbdint:new_interpreter_dashboard')
        elif user.role == User.Roles.ADMIN:
            return redirect('dbdint:admin_dashboard')
            
        messages.error(self.request, "Access denied. Please complete your registration or contact support.")
        return redirect('dbdint:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            client = self.request.user.client_profile
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Statistiques de base
            context['stats'] = {
                'pending_quotes': QuoteRequest.objects.filter(
                    client=client, 
                    status='PENDING'
                ).count(),
                'active_assignments': Assignment.objects.filter(
                    client=client, 
                    status__in=['CONFIRMED', 'IN_PROGRESS']
                ).count(),
                'completed_assignments': Assignment.objects.filter(
                    client=client, 
                    status='COMPLETED', 
                    completed_at__gte=thirty_days_ago
                ).count(),
                'total_spent': Payment.objects.filter(
                    assignment__client=client,
                    status='COMPLETED',
                    payment_date__gte=thirty_days_ago
                ).aggregate(total=Sum('amount'))['total'] or 0
            }
            
            # Données récentes
            context.update({
                'recent_quotes': QuoteRequest.objects.filter(
                    client=client
                ).select_related(
                    'service_type',
                    'source_language',
                    'target_language'
                ).order_by('-created_at')[:5],
                
                'upcoming_assignments': Assignment.objects.filter(
                    client=client,
                    status__in=['CONFIRMED', 'IN_PROGRESS'],
                    start_time__gte=timezone.now()
                ).select_related(
                    'service_type',
                    'source_language',
                    'target_language'
                ).order_by('start_time')[:5],
                
                'recent_payments': Payment.objects.filter(
                    assignment__client=client
                ).select_related(
                    'assignment',
                    'assignment__service_type'
                ).order_by('-payment_date')[:5],
                
                'unread_notifications': Notification.objects.filter(
                    recipient=self.request.user,
                    read=False
                ).order_by('-created_at')[:5],
                
                'client_profile': client
            })

        except Exception as e:
            logger.error(
                "Error loading client dashboard data",
                exc_info=True,
                extra={
                    'user_id': self.request.user.id,
                    'error': str(e)
                }
            )
            messages.error(
                self.request,
                "There was a problem loading your dashboard data. Please refresh the page or contact support if the problem persists."
            )
            context.update({
                'error_loading_data': True,
                'stats': {
                    'pending_quotes': 0,
                    'active_assignments': 0,
                    'completed_assignments': 0,
                    'total_spent': 0
                }
            })
        
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        response = super().dispatch(request, *args, **kwargs)
        
        if response.status_code == 200:
            logger.info(
                "Client dashboard accessed successfully",
                extra={
                    'user_id': request.user.id,
                    'ip_address': request.META.get('REMOTE_ADDR')
                }
            )
        
        return response

class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # Get notification ID from request data
            notification_id = request.POST.get('notification_id')
            
            if not notification_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Notification ID is required'
                }, status=400)

            # Get notification and verify ownership
            notification = Notification.objects.get(
                id=notification_id,
                recipient=request.user,
            )
            
            # Mark as read
            notification.read = True
            notification.read_at = timezone.now()
            notification.save()

            return JsonResponse({
                'success': True,
                'message': 'Notification marked as read',
                'notification_id': notification_id
            })

        except Notification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Notification not found'
            }, status=404)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred'
            }, status=500)

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'success': False,
            'message': 'Method not allowed'
        }, status=405)

class ClearAllNotificationsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            # Get all unread notifications for the user
            notifications = Notification.objects.filter(
                recipient=request.user,
                read=False
            )
            
            # Update all notifications
            count = notifications.count()
            notifications.update(
                read=True,
                read_at=timezone.now()
            )

            return JsonResponse({
                'success': True,
                'message': f'{count} notifications marked as read',
                'count': count
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred'
            }, status=500)

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'success': False,
            'message': 'Method not allowed'
        }, status=405)
