from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView

from ...models import Assignment

class InterpreterScheduleView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'trad/schedule.html'

    def test_func(self):
        return self.request.user.role == 'INTERPRETER'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interpreter = self.request.user.interpreter_profile

        # Récupérer la date actuelle
        now = timezone.now()
        
        # Prochaines missions (limitées à 5)
        context['upcoming_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status__in=['CONFIRMED', 'ASSIGNED'],
            start_time__gte=now
        ).order_by('start_time')[:5]

        # Missions en cours
        context['current_assignments'] = Assignment.objects.filter(
            interpreter=interpreter,
            status='IN_PROGRESS'
        )

        # Statistiques de la semaine
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        weekly_assignments = Assignment.objects.filter(
            interpreter=interpreter,
            start_time__range=(week_start, week_end),
            status__in=['CONFIRMED', 'IN_PROGRESS', 'COMPLETED']
        )

        context['weekly_stats'] = {
            'total_assignments': weekly_assignments.count(),
            'total_hours': sum(
                (a.end_time - a.start_time).total_seconds() / 3600 
                for a in weekly_assignments
            ),
            'earnings': sum(a.total_interpreter_payment or 0 for a in weekly_assignments)
        }

        return context

def get_calendar_assignments(request):
    """Vue API pour récupérer les missions pour le calendrier"""
    if not request.user.is_authenticated or request.user.role != 'INTERPRETER':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    start = request.GET.get('start')
    end = request.GET.get('end')
    interpreter = request.user.interpreter_profile

    assignments = Assignment.objects.filter(
        interpreter=interpreter,
        start_time__range=[start, end]
    ).select_related('client', 'service_type')

    events = []
    status_colors = {
        'PENDING': '#FFA500',    # Orange
        'ASSIGNED': '#4299e1',   # Bleu clair
        'CONFIRMED': '#48bb78',  # Vert
        'IN_PROGRESS': '#805ad5', # Violet
        'COMPLETED': '#718096',  # Gris
        'CANCELLED': '#f56565',  # Rouge
        'NO_SHOW': '#ed8936',    # Orange foncé
    }

    for assignment in assignments:
        events.append({
            'id': assignment.id,
            'title': f"{assignment.client.full_name} - {assignment.service_type.name}",
            'start': assignment.start_time.isoformat(),
            'end': assignment.end_time.isoformat(),
            'backgroundColor': status_colors[assignment.status],
            'borderColor': status_colors[assignment.status],
            'extendedProps': {
                'status': assignment.status,
                'location': assignment.location,
                'city': assignment.city,
                'languages': f"{assignment.source_language.name} → {assignment.target_language.name}",
                'rate': float(assignment.interpreter_rate),
                'hours': (assignment.end_time - assignment.start_time).total_seconds() / 3600,
                'total_payment': float(assignment.total_interpreter_payment or 0),
                'special_requirements': assignment.special_requirements or 'None'
            }
        })

    return JsonResponse(events, safe=False)
