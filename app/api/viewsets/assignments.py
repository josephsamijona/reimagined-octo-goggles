"""Assignment CRUD and lifecycle management (confirm, cancel, complete, reassign)."""
import logging
from collections import defaultdict

from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.api.filters import AssignmentFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.assignments import (
    AssignmentListSerializer,
    AssignmentDetailSerializer,
    AssignmentCreateSerializer,
    AssignmentUpdateSerializer,
)
from app.api.services.assignment_service import (
    create_interpreter_payment,
    cancel_interpreter_payment,
    create_expense_for_assignment,
    add_assignment_to_google_calendar,
)
from app.models import Assignment, Notification

logger = logging.getLogger(__name__)


class AssignmentViewSet(ModelViewSet):
    """Full CRUD plus lifecycle actions for assignments."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AssignmentFilter
    search_fields = [
        'client__company_name',
        'client_name',
        'interpreter__user__first_name',
        'interpreter__user__last_name',
        'city',
    ]
    ordering_fields = ['start_time', 'created_at', 'status']
    ordering = ['-start_time']

    def get_queryset(self):
        return (
            Assignment.objects
            .select_related(
                'interpreter__user',
                'client',
                'service_type',
                'source_language',
                'target_language',
                'quote',
            )
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return AssignmentListSerializer
        if self.action in ('create',):
            return AssignmentCreateSerializer
        if self.action in ('partial_update', 'update'):
            return AssignmentUpdateSerializer
        return AssignmentDetailSerializer

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):                   # est ce que c'est dans ce viewset que l'on cree appointment
        """Confirm a PENDING assignment and create interpreter payment."""
        assignment = self.get_object()
        if not assignment.can_be_confirmed():
            return Response(
                {'detail': f'Cannot confirm assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = Assignment.Status.CONFIRMED   # I definitly dont have any prob with the fact 
        assignment.save()

        # Create pending interpreter payment + push to company Google Calendar
        if assignment.interpreter and assignment.total_interpreter_payment:
            try:
                create_interpreter_payment(assignment, created_by=request.user)
            except Exception as e:
                logger.error(f"Failed to create interpreter payment for assignment {pk}: {e}")

        add_assignment_to_google_calendar(assignment.id)

        serializer = AssignmentDetailSerializer(assignment)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an assignment and void any pending payment."""
        assignment = self.get_object()
        if not assignment.can_be_cancelled():
            return Response(
                {'detail': f'Cannot cancel assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_interpreter = assignment.cancel()

        # Cancel interpreter payment
        cancel_interpreter_payment(assignment)

        serializer = AssignmentDetailSerializer(assignment)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Complete
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark an assignment as completed, update payment, create expense."""
        assignment = self.get_object()
        if not assignment.can_be_completed():
            return Response(
                {'detail': f'Cannot complete assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = Assignment.Status.COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save()

        # Create expense; payment stays PENDING — admin changes payout status manually
        if assignment.interpreter and assignment.total_interpreter_payment:
            try:
                create_expense_for_assignment(assignment)
            except Exception as e:
                logger.error(f"Failed to create expense for completed assignment {pk}: {e}")

        serializer = AssignmentDetailSerializer(assignment)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Reassign
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def reassign(self, request, pk=None):
        """Reassign an assignment to a different interpreter."""
        from app.models import Interpreter

        assignment = self.get_object()
        new_interpreter_id = request.data.get('interpreter_id')
        if not new_interpreter_id:
            return Response(
                {'detail': 'interpreter_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_interpreter = Interpreter.objects.select_related('user').get(pk=new_interpreter_id)
        except Interpreter.DoesNotExist:
            return Response(
                {'detail': 'Interpreter not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_interpreter = assignment.interpreter
        assignment.interpreter = new_interpreter
        if assignment.status == Assignment.Status.CANCELLED:
            assignment.status = Assignment.Status.PENDING
        assignment.save()

        # Send notification to new interpreter     # we need to use the view and template we already have
        try:
            Notification.objects.create(
                recipient=new_interpreter.user,
                type='ASSIGNMENT_OFFER',
                title='New Assignment Offer',
                content=f"You have been assigned to mission #{assignment.id} on {assignment.start_time.strftime('%m/%d/%Y')}.",
                link=f'/interpreter/assignments/{assignment.id}/',
            )
        except Exception as e:
            logger.error(f"Failed to create notification for reassignment: {e}")

        serializer = AssignmentDetailSerializer(assignment)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Calendar view
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Return assignments filtered by date range for calendar display."""
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        qs = self.get_queryset()
        if start:
            qs = qs.filter(start_time__gte=start)
        if end:
            qs = qs.filter(start_time__lte=end)

        qs = qs.order_by('start_time')
        data = []
        for a in qs:
            interpreter_name = ''
            if a.interpreter and a.interpreter.user:
                interpreter_name = f"{a.interpreter.user.first_name} {a.interpreter.user.last_name}"
            client_display = a.client.company_name if a.client else (a.client_name or '')

            data.append({
                'id': a.id,
                'title': f"{a.service_type.name} - {client_display}" if a.service_type else client_display,
                'start': a.start_time,
                'end': a.end_time,
                'status': a.status,
                'interpreter': interpreter_name,
                'client': client_display,
                'city': a.city,
                'state': a.state,
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Kanban view (group by status)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def kanban(self, request):
        """Group assignments by status for kanban-style display."""
        qs = self.filter_queryset(self.get_queryset())

        grouped = defaultdict(list)
        for a in qs.order_by('start_time'):
            interpreter_name = ''
            if a.interpreter and a.interpreter.user:
                interpreter_name = f"{a.interpreter.user.first_name} {a.interpreter.user.last_name}"
            client_display = a.client.company_name if a.client else (a.client_name or '')

            grouped[a.status].append({
                'id': a.id,
                'start_time': a.start_time,
                'end_time': a.end_time,          #adding adresse would be good too
                'interpreter': interpreter_name,
                'client': client_display,
                'service_type': a.service_type.name if a.service_type else '',
                'city': a.city,
            })

        return Response(dict(grouped))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Aggregate counts by status, service type, and language."""
        qs = self.filter_queryset(self.get_queryset())

        by_status = dict(
            qs.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        by_service_type = list(
            qs.values('service_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        by_language = list(
            qs.values('source_language__name', 'target_language__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        return Response({
            'by_status': by_status,
            'by_service_type': by_service_type,
            'by_language': by_language,
            'total': qs.count(),
        })
