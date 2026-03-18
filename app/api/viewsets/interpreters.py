"""Interpreter management viewset with performance, availability, and map endpoints."""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Avg, Sum, Q, Subquery, OuterRef
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from app.api.filters import InterpreterFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.users import (
    InterpreterListSerializer,
    InterpreterDetailSerializer,
    InterpreterUpdateSerializer,
)
from app.models import (
    Interpreter, InterpreterLocation, Assignment, AssignmentFeedback,
    InterpreterPayment,
)

logger = logging.getLogger(__name__)


class InterpreterViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """
    Interpreter management: list, retrieve, partial_update plus custom actions
    for blocking, availability checking, performance stats, and map data.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InterpreterFilter
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'city',
        'state',
    ]
    ordering_fields = ['user__first_name', 'user__last_name', 'city', 'state']
    ordering = ['user__last_name']

    def get_queryset(self):
        return (
            Interpreter.objects
            .select_related('user')
            .prefetch_related('languages')
            .annotate(
                missions_count=Count(
                    'assignment',
                    filter=Q(assignment__status='COMPLETED'),
                ),
                avg_rating=Avg(
                    'assignment__assignmentfeedback__rating',
                    filter=Q(assignment__status='COMPLETED'),
                ),
            )
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return InterpreterListSerializer
        if self.action in ('partial_update', 'update'):
            return InterpreterUpdateSerializer
        return InterpreterDetailSerializer

    # ------------------------------------------------------------------
    # Block / Unblock
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block an interpreter manually."""
        interpreter = self.get_object()
        reason = request.data.get('reason', '')
        interpreter.is_manually_blocked = True
        interpreter.blocked_reason = reason
        interpreter.blocked_at = timezone.now()
        interpreter.blocked_by = request.user
        interpreter.save(update_fields=[
            'is_manually_blocked', 'blocked_reason', 'blocked_at', 'blocked_by',
        ])
        return Response({'detail': 'Interpreter blocked.'})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        """Unblock an interpreter."""
        interpreter = self.get_object()
        interpreter.is_manually_blocked = False
        interpreter.blocked_reason = None
        interpreter.blocked_at = None
        interpreter.blocked_by = None
        interpreter.save(update_fields=[
            'is_manually_blocked', 'blocked_reason', 'blocked_at', 'blocked_by',
        ])
        return Response({'detail': 'Interpreter unblocked.'})

    # ------------------------------------------------------------------
    # Available interpreters (filtered by criteria)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Find interpreters available for a given set of criteria.
        Query params: language, state, city, date, service_type
        """
        qs = Interpreter.objects.filter(active=True, is_manually_blocked=False).select_related('user')

        language_id = request.query_params.get('language')
        if language_id:
            qs = qs.filter(languages__id=language_id)

        state = request.query_params.get('state')
        if state:
            qs = qs.filter(state__iexact=state)

        city = request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)

        # Exclude interpreters already on mission at the given date
        date_str = request.query_params.get('date')
        if date_str:
            try:
                from django.utils.dateparse import parse_datetime, parse_date
                parsed_date = parse_date(date_str)
                if parsed_date:
                    busy_ids = Assignment.objects.filter(
                        status__in=['CONFIRMED', 'IN_PROGRESS'],
                        start_time__date=parsed_date,
                        interpreter__isnull=False,
                    ).values_list('interpreter_id', flat=True)
                    qs = qs.exclude(id__in=busy_ids)
            except (ValueError, TypeError):
                pass

        qs = qs.distinct()
        data = []
        for interp in qs[:100]:
            data.append({
                'id': interp.id,
                'first_name': interp.user.first_name,
                'last_name': interp.user.last_name,
                'email': interp.user.email,
                'phone': interp.user.phone,
                'city': interp.city,
                'state': interp.state,
                'hourly_rate': str(interp.hourly_rate) if interp.hourly_rate else None,
                'languages': list(interp.languages.values_list('name', flat=True)),
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Performance stats for a single interpreter
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Performance metrics for a single interpreter."""
        interpreter = self.get_object()

        assignments_qs = Assignment.objects.filter(interpreter=interpreter)

        missions_completed = assignments_qs.filter(status='COMPLETED').count()

        total_decided = assignments_qs.filter(
            status__in=['CONFIRMED', 'COMPLETED', 'CANCELLED']
        ).count()
        accepted = assignments_qs.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).count()
        acceptance_rate = (
            round(accepted / total_decided * 100, 1) if total_decided > 0 else 0
        )

        total_possible_show = assignments_qs.filter(
            status__in=['COMPLETED', 'NO_SHOW']
        ).count()
        no_shows = assignments_qs.filter(status='NO_SHOW').count()
        no_show_rate = (
            round(no_shows / total_possible_show * 100, 1) if total_possible_show > 0 else 0
        )

        avg_rating = (
            AssignmentFeedback.objects
            .filter(assignment__interpreter=interpreter)
            .aggregate(avg=Avg('rating'))['avg']
        )

        total_earned = (
            InterpreterPayment.objects
            .filter(interpreter=interpreter, status='COMPLETED')
            .aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )

        return Response({
            'missions_completed': missions_completed,
            'acceptance_rate': acceptance_rate,
            'no_show_rate': no_show_rate,
            'avg_rating': round(avg_rating, 2) if avg_rating else None,
            'total_earned': str(total_earned),
        })

    # ------------------------------------------------------------------
    # Payments for a single interpreter
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """List interpreter payments for a specific interpreter."""
        interpreter = self.get_object()
        payments = (
            InterpreterPayment.objects
            .filter(interpreter=interpreter)
            .select_related('assignment', 'transaction')
            .order_by('-created_at')[:50]
        )

        data = []
        for p in payments:
            data.append({
                'id': p.id,
                'reference_number': p.reference_number,
                'amount': str(p.amount),
                'status': p.status,
                'payment_method': p.payment_method,
                'scheduled_date': p.scheduled_date,
                'processed_date': p.processed_date,
                'assignment_id': p.assignment_id,
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Live locations (latest per active interpreter)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='live-locations')
    def live_locations(self, request):
        """Latest GPS location per active interpreter."""
        # Subquery to get the latest location per interpreter
        latest_location = (
            InterpreterLocation.objects
            .filter(interpreter=OuterRef('pk'))
            .order_by('-timestamp')
            .values('id')[:1]
        )

        locations = (
            InterpreterLocation.objects
            .filter(
                id__in=Subquery(latest_location),
                interpreter__active=True,
            )
            .select_related('interpreter__user', 'current_assignment')
        )

        data = []
        for loc in locations:
            interp = loc.interpreter
            data.append({
                'interpreter_id': interp.id,
                'name': f"{interp.user.first_name} {interp.user.last_name}",
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'accuracy': loc.accuracy,
                'is_on_mission': loc.is_on_mission,
                'current_assignment_id': loc.current_assignment_id,
                'timestamp': loc.timestamp,
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Map data (all interpreters with city/state for geocoding)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def map(self, request):
        """All interpreters with city/state for map plotting."""
        interpreters = (
            Interpreter.objects
            .filter(active=True)
            .select_related('user')
            .values(
                'id',
                'user__first_name',
                'user__last_name',
                'city',
                'state',
                'is_manually_blocked',
            )
        )

        return Response(list(interpreters))
