"""Interpreter matching and availability service."""
from django.db.models import Q, Count, Avg
from django.utils import timezone
from app.models import Interpreter, Assignment


def find_available_interpreters(language=None, state=None, city=None, date=None, service_type=None):
    """Find interpreters available for a given set of criteria."""
    qs = Interpreter.objects.filter(active=True, is_manually_blocked=False)
    qs = qs.select_related('user')
    qs = qs.prefetch_related('languages')

    if language:
        qs = qs.filter(languages__id=language)
    if state:
        qs = qs.filter(state__iexact=state)
    if city:
        qs = qs.filter(city__icontains=city)

    if date:
        # Exclude interpreters who have assignments overlapping with the requested date
        busy_interpreters = Assignment.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS'],
            start_time__date=date,
        ).values_list('interpreter_id', flat=True)
        qs = qs.exclude(id__in=busy_interpreters)

    qs = qs.annotate(
        missions_count=Count('assignment', filter=Q(assignment__status='COMPLETED')),
        avg_rating=Avg('assignment__assignmentfeedback__rating'),
    )

    return qs.distinct()
