from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Q, Avg
from django.utils import timezone
from django.views.generic import TemplateView, ListView

from ...models import Assignment, Payment, Notification

class InterpreterDashboardView(LoginRequiredMixin, UserPassesTestMixin,TemplateView):
    template_name = 'trad/home.html'
    
    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer l'interprète
        interpreter = self.request.user.interpreter_profile
        
        # Période pour les statistiques
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Statistiques générales
        context['stats'] = {
            'pending_assignments': Assignment.objects.filter(
                interpreter=interpreter, 
                status='PENDING'
            ).count(),
            'upcoming_assignments': Assignment.objects.filter(
                interpreter=interpreter,
                status='CONFIRMED',
                start_time__gte=timezone.now()
            ).count(),
            'completed_assignments': Assignment.objects.filter(
                interpreter=interpreter,
                status='COMPLETED',
                completed_at__gte=thirty_days_ago
            ).count(),
            'total_earnings': Payment.objects.filter(
                assignment__interpreter=interpreter,
                payment_type='INTERPRETER_PAYMENT',
                status='COMPLETED',
                payment_date__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
        }
        
        # Missions du jour
        today = timezone.now().date()
        context['today_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__date=today,
            status__in=['CONFIRMED', 'IN_PROGRESS']
        ).order_by('start_time')
        
        # Prochaines missions
        context['upcoming_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='CONFIRMED',
            start_time__gt=timezone.now()
        ).order_by('start_time')[:5]
        
        # Derniers paiements
        context['recent_payments'] = Payment.objects.filter(
            assignment__interpreter=interpreter,
            payment_type='INTERPRETER_PAYMENT'
        ).order_by('-payment_date')[:5]
        
        # Notifications non lues
        context['unread_notifications'] = Notification.objects.filter(
            recipient=self.request.user,
            read=False
        ).order_by('-created_at')[:5]
        
        # Statistiques de performance
        assignments_completed = Assignment.objects.filter(
            interpreter=interpreter,
            status='COMPLETED'
        )
        
        context['performance'] = {
            'total_hours': sum((a.end_time - a.start_time).total_seconds() / 3600 
                             for a in assignments_completed),
            'average_rating': assignments_completed.aggregate(
                avg_rating=Avg('assignmentfeedback__rating')
            )['avg_rating'] or 0,
            'completion_rate': (
                assignments_completed.count() / 
                Assignment.objects.filter(interpreter=interpreter).count() * 100
                if Assignment.objects.filter(interpreter=interpreter).exists() 
                else 0
            )
        }
        
        return context
