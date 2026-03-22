"""Assignment CRUD and lifecycle management (confirm, cancel, complete, reassign, etc.)."""
import csv
import logging
from collections import defaultdict

from django.db.models import Count, Q
from django.http import StreamingHttpResponse
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
    AssignmentCalendarSerializer,
)
from app.api.services.assignment_service import (
    create_interpreter_payment,
    cancel_interpreter_payment,
    create_expense_for_assignment,
    add_assignment_to_google_calendar,
)
import app.services.assignment_email_service as email_svc
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
        if self.action == 'create':
            return AssignmentCreateSerializer
        if self.action in ('partial_update', 'update'):
            return AssignmentUpdateSerializer
        return AssignmentDetailSerializer

    # ------------------------------------------------------------------
    # Confirm  (PENDING → CONFIRMED)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a PENDING assignment and create interpreter payment."""
        assignment = self.get_object()
        if not assignment.can_be_confirmed():
            return Response(
                {'detail': f'Cannot confirm assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = Assignment.Status.CONFIRMED
        assignment.save()

        if assignment.interpreter and assignment.total_interpreter_payment:
            try:
                create_interpreter_payment(assignment, created_by=request.user)
            except Exception as e:
                logger.error('Failed to create interpreter payment for assignment %s: %s', pk, e)

        add_assignment_to_google_calendar(assignment.id)
        email_svc.send_assignment_email(assignment, 'confirmed')

        return Response(AssignmentDetailSerializer(assignment).data)

    # ------------------------------------------------------------------
    # Start  (CONFIRMED → IN_PROGRESS)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Mark a CONFIRMED assignment as in-progress."""
        assignment = self.get_object()
        if not assignment.can_be_started():
            return Response(
                {'detail': f'Cannot start assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.start()
        return Response(AssignmentDetailSerializer(assignment).data)

    # ------------------------------------------------------------------
    # Cancel  (PENDING / CONFIRMED → CANCELLED)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an assignment, void payment, and notify interpreter."""
        assignment = self.get_object()
        if not assignment.can_be_cancelled():
            return Response(
                {'detail': f'Cannot cancel assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.cancel()
        cancel_interpreter_payment(assignment)
        email_svc.send_assignment_email(assignment, 'cancelled')

        return Response(AssignmentDetailSerializer(assignment).data)

    # ------------------------------------------------------------------
    # Complete  (CONFIRMED / IN_PROGRESS → COMPLETED)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark assignment completed, create expense, and notify interpreter."""
        assignment = self.get_object()
        if not assignment.can_be_completed():
            return Response(
                {'detail': f'Cannot complete assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = Assignment.Status.COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save()

        if assignment.interpreter and assignment.total_interpreter_payment:
            try:
                create_expense_for_assignment(assignment)
            except Exception as e:
                logger.error('Failed to create expense for completed assignment %s: %s', pk, e)

        email_svc.send_assignment_email(assignment, 'completed')
        return Response(AssignmentDetailSerializer(assignment).data)

    # ------------------------------------------------------------------
    # No-Show  (CONFIRMED / IN_PROGRESS → NO_SHOW)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, pk=None):
        """Mark assignment as no-show, void payment, and notify all parties."""
        assignment = self.get_object()
        allowed = {Assignment.Status.CONFIRMED, Assignment.Status.IN_PROGRESS}
        if assignment.status not in allowed:
            return Response(
                {'detail': f'Cannot mark no-show for assignment in status {assignment.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = Assignment.Status.NO_SHOW
        assignment.save()

        cancel_interpreter_payment(assignment)

        try:
            email_svc.send_assignment_email(assignment, 'no_show')
        except Exception as e:
            logger.warning('no_show email failed for assignment %s: %s', pk, e)

        if assignment.interpreter:
            try:
                Notification.objects.create(
                    recipient=assignment.interpreter.user,
                    type='ASSIGNMENT_NO_SHOW',
                    title='Mission No-Show Recorded',
                    content=(
                        f"Mission #{assignment.id} on "
                        f"{assignment.start_time.strftime('%m/%d/%Y')} has been marked as no-show."
                    ),
                    link=f'/interpreter/assignments/{assignment.id}/',
                )
            except Exception as e:
                logger.error('Failed to create no-show notification for assignment %s: %s', pk, e)

        return Response(AssignmentDetailSerializer(assignment).data)

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
            return Response({'detail': 'interpreter_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_interpreter = Interpreter.objects.select_related('user').get(pk=new_interpreter_id)
        except Interpreter.DoesNotExist:
            return Response({'detail': 'Interpreter not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Cancel old payment before reassigning
        if assignment.interpreter:
            cancel_interpreter_payment(assignment)

        assignment.interpreter = new_interpreter
        if assignment.status == Assignment.Status.CANCELLED:
            assignment.status = Assignment.Status.PENDING
        assignment.save()

        try:
            Notification.objects.create(
                recipient=new_interpreter.user,
                type='ASSIGNMENT_OFFER',
                title='New Assignment Offer',
                content=(
                    f"You have been assigned to mission #{assignment.id} "
                    f"on {assignment.start_time.strftime('%m/%d/%Y')}."
                ),
                link=f'/interpreter/assignments/{assignment.id}/',
            )
        except Exception as e:
            logger.error('Failed to create notification for reassignment: %s', e)

        email_svc.send_assignment_email(assignment, 'new')
        return Response(AssignmentDetailSerializer(assignment).data)

    # ------------------------------------------------------------------
    # Send Reminder
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='send-reminder')
    def send_reminder(self, request, pk=None):
        """Send an email reminder to the assigned interpreter."""
        assignment = self.get_object()
        if not assignment.interpreter:
            return Response({'detail': 'No interpreter assigned.'}, status=status.HTTP_400_BAD_REQUEST)

        active_statuses = {Assignment.Status.CONFIRMED, Assignment.Status.IN_PROGRESS}
        if assignment.status not in active_statuses:
            return Response(
                {'detail': 'Can only send reminders for CONFIRMED or IN_PROGRESS assignments.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            email_svc.send_assignment_email(assignment, 'confirmed')
        except Exception as e:
            logger.error('Failed to send reminder for assignment %s: %s', pk, e)
            return Response({'detail': 'Failed to send reminder email.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'detail': f'Reminder sent to {assignment.interpreter.user.email}.'})

    # ------------------------------------------------------------------
    # Duplicate
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a copy of this assignment with PENDING status (dates cleared)."""
        src = self.get_object()

        new_assignment = Assignment(
            interpreter=src.interpreter,
            client=src.client,
            client_name=src.client_name,
            client_email=src.client_email,
            client_phone=src.client_phone,
            service_type=src.service_type,
            source_language=src.source_language,
            target_language=src.target_language,
            start_time=src.start_time,
            end_time=src.end_time,
            location=src.location,
            city=src.city,
            state=src.state,
            zip_code=src.zip_code,
            status=Assignment.Status.PENDING,
            interpreter_rate=src.interpreter_rate,
            minimum_hours=src.minimum_hours,
            total_interpreter_payment=src.total_interpreter_payment,
            notes=src.notes,
            special_requirements=src.special_requirements,
        )
        new_assignment.save()
        return Response(AssignmentDetailSerializer(new_assignment).data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Add Note
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='add-note')
    def add_note(self, request, pk=None):
        """Append a timestamped note to the assignment's notes field."""
        assignment = self.get_object()
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'detail': 'text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        author = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
        entry = f"[{timestamp} — {author}] {text}"

        existing = (assignment.notes or '').strip()
        assignment.notes = f"{existing}\n{entry}".strip()
        assignment.save(update_fields=['notes', 'updated_at'])

        return Response({'detail': 'Note added.', 'notes': assignment.notes})

    # ------------------------------------------------------------------
    # Timeline  (audit log for this assignment)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Return structured audit timeline for this assignment."""
        assignment = self.get_object()
        entries = []

        # Creation
        entries.append({
            'time': assignment.created_at.isoformat(),
            'action': 'Mission created',
            'actor': None,
        })

        # Parse notes for timestamped entries
        if assignment.notes:
            import re
            pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) — ([^\]]+)\] (.+)')
            for line in assignment.notes.splitlines():
                m = pattern.match(line.strip())
                if m:
                    entries.append({
                        'time': m.group(1),
                        'action': f'Note: {m.group(3)}',
                        'actor': m.group(2),
                    })

        # Status milestones from model timestamps
        if assignment.completed_at:
            entries.append({
                'time': assignment.completed_at.isoformat(),
                'action': f'Status changed to {assignment.status}',
                'actor': None,
            })

        # AuditLog entries if available
        try:
            from app.models import AuditLog
            logs = (
                AuditLog.objects
                .filter(model_name='Assignment', object_id=str(assignment.id))
                .select_related('user')
                .order_by('timestamp')
            )
            for log in logs:
                actor = None
                if log.user:
                    actor = f"{log.user.first_name} {log.user.last_name}".strip() or log.user.email
                entries.append({
                    'time': log.timestamp.isoformat(),
                    'action': log.action,
                    'actor': actor,
                })
        except Exception:
            pass

        entries.sort(key=lambda e: e['time'])
        return Response(entries)

    # ------------------------------------------------------------------
    # Check Conflict
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='check-conflict')
    def check_conflict(self, request):
        """Check if an interpreter has a conflicting assignment in the given time window."""
        interpreter_id = request.query_params.get('interpreter_id')
        start = request.query_params.get('start_time')
        end = request.query_params.get('end_time')
        exclude_id = request.query_params.get('exclude_id')

        if not all([interpreter_id, start, end]):
            return Response({'detail': 'interpreter_id, start_time, end_time are required.'}, status=400)

        active_statuses = [
            Assignment.Status.PENDING,
            Assignment.Status.CONFIRMED,
            Assignment.Status.IN_PROGRESS,
        ]
        qs = Assignment.objects.filter(
            interpreter_id=interpreter_id,
            status__in=active_statuses,
            start_time__lt=end,
            end_time__gt=start,
        )
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)

        conflicts = list(
            qs.values('id', 'start_time', 'end_time', 'status', 'city')
        )
        return Response({'has_conflict': bool(conflicts), 'conflicts': conflicts})

    # ------------------------------------------------------------------
    # Bulk Action
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='bulk-action')
    def bulk_action(self, request):
        """
        Perform a bulk lifecycle action on multiple assignments.
        Payload: { action: 'confirm' | 'cancel' | 'complete', ids: [1, 2, 3] }
        """
        act = request.data.get('action')
        ids = request.data.get('ids', [])

        if act not in ('confirm', 'cancel', 'complete'):
            return Response({'detail': 'action must be confirm, cancel, or complete.'}, status=400)
        if not ids:
            return Response({'detail': 'ids list is required.'}, status=400)

        assignments = Assignment.objects.filter(pk__in=ids).select_related('interpreter__user')
        results = {'succeeded': [], 'failed': []}

        for assignment in assignments:
            try:
                if act == 'confirm' and assignment.can_be_confirmed():
                    assignment.status = Assignment.Status.CONFIRMED
                    assignment.save()
                    if assignment.interpreter and assignment.total_interpreter_payment:
                        create_interpreter_payment(assignment, created_by=request.user)
                    add_assignment_to_google_calendar(assignment.id)
                    email_svc.send_assignment_email(assignment, 'confirmed')
                    results['succeeded'].append(assignment.id)
                elif act == 'cancel' and assignment.can_be_cancelled():
                    assignment.cancel()
                    cancel_interpreter_payment(assignment)
                    email_svc.send_assignment_email(assignment, 'cancelled')
                    results['succeeded'].append(assignment.id)
                elif act == 'complete' and assignment.can_be_completed():
                    assignment.status = Assignment.Status.COMPLETED
                    assignment.completed_at = timezone.now()
                    assignment.save()
                    if assignment.interpreter and assignment.total_interpreter_payment:
                        create_expense_for_assignment(assignment)
                    email_svc.send_assignment_email(assignment, 'completed')
                    results['succeeded'].append(assignment.id)
                else:
                    results['failed'].append({'id': assignment.id, 'reason': f'Cannot {act} in status {assignment.status}'})
            except Exception as e:
                logger.error('Bulk action %s failed for assignment %s: %s', act, assignment.id, e)
                results['failed'].append({'id': assignment.id, 'reason': str(e)})

        return Response(results)

    # ------------------------------------------------------------------
    # Export CSV
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Stream filtered assignments as a CSV file."""
        qs = self.filter_queryset(self.get_queryset()).order_by('start_time')

        def stream():
            yield '\ufeff'  # UTF-8 BOM for Excel
            headers = [
                'ID', 'Status', 'Client', 'Interpreter', 'Service Type',
                'Source Language', 'Target Language',
                'Start Time', 'End Time', 'Location', 'City', 'State', 'ZIP',
                'Rate ($/hr)', 'Min Hours', 'Total Payment', 'Is Paid',
                'Notes', 'Created At',
            ]
            yield ','.join(f'"{h}"' for h in headers) + '\r\n'

            for a in qs.iterator(chunk_size=200):
                interpreter_name = ''
                if a.interpreter and a.interpreter.user:
                    u = a.interpreter.user
                    interpreter_name = f"{u.first_name} {u.last_name}".strip()
                client_display = a.client.company_name if a.client else (a.client_name or '')

                row = [
                    str(a.id),
                    a.status,
                    client_display,
                    interpreter_name,
                    a.service_type.name if a.service_type else '',
                    a.source_language.name if a.source_language else '',
                    a.target_language.name if a.target_language else '',
                    a.start_time.isoformat() if a.start_time else '',
                    a.end_time.isoformat() if a.end_time else '',
                    a.location or '',
                    a.city or '',
                    a.state or '',
                    a.zip_code or '',
                    str(a.interpreter_rate or ''),
                    str(a.minimum_hours or ''),
                    str(a.total_interpreter_payment or ''),
                    'Yes' if a.is_paid else 'No',
                    (a.notes or '').replace('"', '""').replace('\n', ' '),
                    a.created_at.isoformat() if a.created_at else '',
                ]
                yield ','.join(f'"{v}"' for v in row) + '\r\n'

        response = StreamingHttpResponse(stream(), content_type='text/csv; charset=utf-8')
        filename = f"assignments-{timezone.now().strftime('%Y%m%d-%H%M')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # ------------------------------------------------------------------
    # Calendar view
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Return assignments filtered by date range for calendar display."""
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        qs = AssignmentCalendarSerializer.setup_eager_loading(self.get_queryset())
        if start:
            qs = qs.filter(start_time__gte=start)
        if end:
            qs = qs.filter(start_time__lte=end)

        qs = qs.order_by('start_time')
        serializer = AssignmentCalendarSerializer(qs, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Kanban view
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def kanban(self, request):
        """Group assignments by status for kanban-style display."""
        qs = self.filter_queryset(
            AssignmentListSerializer.setup_eager_loading(self.get_queryset())
        ).order_by('start_time')

        grouped = defaultdict(list)
        serializer = AssignmentListSerializer(qs, many=True)
        for item in serializer.data:
            grouped[item['status']].append(item)

        # Ensure all statuses present even if empty
        for s in ('PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'):
            if s not in grouped:
                grouped[s] = []

        return Response(dict(grouped))

    # ------------------------------------------------------------------
    # Create / Update overrides — with audit logging
    # ------------------------------------------------------------------
    def _get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')

    def _write_audit(self, request, action, object_id, changes):
        """Write an AuditLog entry; fail silently."""
        try:
            from app.models import AuditLog
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=action,
                model_name='Assignment',
                object_id=str(object_id),
                changes=changes,
                ip_address=self._get_client_ip(request),
            )
        except Exception as audit_err:
            logger.warning('Could not write AuditLog: %s', audit_err)

    def create(self, request, *args, **kwargs):
        """Override to capture and log validation failures before returning errors."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            logger.error(
                'Assignment creation FAILED — user=%s errors=%s payload=%s',
                getattr(request.user, 'email', '?'),
                errors,
                {k: v for k, v in request.data.items() if k not in ('password',)},
            )
            self._write_audit(request, 'CREATE_FAILED', '0', {
                'errors': errors,
                'payload_keys': list(request.data.keys()),
            })
            from rest_framework.response import Response as DRFResponse
            from rest_framework import status as drf_status
            return DRFResponse(errors, status=drf_status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            self._write_audit(self.request, 'CREATED', instance.id, {
                'status': instance.status,
                'city': instance.city,
                'state': instance.state,
                'start_time': instance.start_time.isoformat() if instance.start_time else None,
                'interpreter_id': instance.interpreter_id,
            })
            logger.info('Assignment #%s created by %s', instance.id, getattr(self.request.user, 'email', '?'))
        except Exception as e:
            logger.warning('Post-create audit failed for assignment %s: %s', instance.id, e)

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            self._write_audit(self.request, 'UPDATED', instance.id, {
                'status': instance.status,
                'updated_fields': list(serializer.validated_data.keys()),
            })
        except Exception as e:
            logger.warning('Post-update audit failed for assignment %s: %s', instance.id, e)

    # ------------------------------------------------------------------
    # Failure Logs  (admin-visible recent errors)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='failure-logs')
    def failure_logs(self, request):
        """Return recent failed assignment creation/update attempts for admin review."""
        try:
            from app.models import AuditLog
            logs = (
                AuditLog.objects
                .filter(model_name='Assignment', action__in=['CREATE_FAILED', 'UPDATE_FAILED'])
                .select_related('user')
                .order_by('-timestamp')[:50]
            )
            data = []
            for log in logs:
                actor = None
                if log.user:
                    actor = f"{log.user.first_name} {log.user.last_name}".strip() or log.user.email
                data.append({
                    'id': log.id,
                    'time': log.timestamp.isoformat(),
                    'action': log.action,
                    'actor': actor,
                    'ip': log.ip_address,
                    'details': log.changes,
                })
            return Response(data)
        except Exception as e:
            logger.error('Failed to retrieve failure logs: %s', e)
            return Response([])

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Aggregate global counts by status, service type, language, plus KPI extras.
        Always returns global counts regardless of any query filters applied.
        """
        qs = self.get_queryset()  # intentionally not filtered — KPI tiles are always global
        today = timezone.localtime(timezone.now()).date()

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

        unassigned_count = qs.filter(
            status=Assignment.Status.PENDING,
            interpreter__isnull=True,
        ).count()

        today_count = qs.filter(start_time__date=today).count()

        return Response({
            'by_status': by_status,
            'by_service_type': by_service_type,
            'by_language': by_language,
            'total': qs.count(),
            'unassigned_count': unassigned_count,
            'today_count': today_count,
        })
