"""Agent Queue viewset — manage AI-proposed actions awaiting admin approval."""
import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.models import AgentQueueItem, AgentAuditLog

logger = logging.getLogger(__name__)


class AgentQueueItemSerializer:
    pass  # inline below


from rest_framework import serializers as drf_serializers


class AgentQueueItemSerializer(drf_serializers.ModelSerializer):
    approved_by_name = drf_serializers.SerializerMethodField()

    class Meta:
        model = AgentQueueItem
        fields = (
            'id', 'gmail_id', 'email_subject', 'email_from',
            'category', 'confidence', 'extracted_data',
            'action_type', 'action_payload', 'ai_reasoning',
            'status', 'approved_by', 'approved_by_name', 'approved_at',
            'rejection_reason', 'executed_at', 'result', 'error_message',
            'linked_assignment_id', 'linked_client_id', 'linked_onboarding_id',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'approved_by', 'approved_at', 'executed_at', 'result', 'created_at', 'updated_at')

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
        return None


class AgentAuditLogSerializer(drf_serializers.ModelSerializer):
    performed_by_name = drf_serializers.SerializerMethodField()

    class Meta:
        model = AgentAuditLog
        fields = ('id', 'queue_item', 'action', 'entity_type', 'entity_id', 'success', 'details', 'performed_by', 'performed_by_name', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return f"{obj.performed_by.first_name} {obj.performed_by.last_name}".strip()
        return None


class AgentQueueViewSet(ModelViewSet):
    """CRUD + approve/reject for agent queue items."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'category', 'confidence', 'status']
    ordering = ['-created_at']
    serializer_class = AgentQueueItemSerializer

    def get_queryset(self):
        qs = AgentQueueItem.objects.select_related('approved_by')
        status_filter = self.request.query_params.get('status')
        category_filter = self.request.query_params.get('category')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)
        return qs

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Return count of PENDING items (for notification badge)."""
        pending = AgentQueueItem.objects.filter(status=AgentQueueItem.Status.PENDING).count()
        return Response({'pending': pending})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Admin approves a proposed action. The FastAPI service will execute it."""
        item = self.get_object()
        if item.status != AgentQueueItem.Status.PENDING:
            return Response(
                {'detail': f'Cannot approve item in status {item.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.status = AgentQueueItem.Status.APPROVED
        item.approved_by = request.user
        item.approved_at = timezone.now()
        item.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])

        AgentAuditLog.objects.create(
            queue_item=item,
            action='APPROVE',
            entity_type='AgentQueueItem',
            entity_id=str(item.id),
            success=True,
            details={'approved_by': request.user.email},
            performed_by=request.user,
        )
        return Response(AgentQueueItemSerializer(item).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Admin rejects a proposed action."""
        item = self.get_object()
        if item.status != AgentQueueItem.Status.PENDING:
            return Response(
                {'detail': f'Cannot reject item in status {item.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get('reason', '')
        item.status = AgentQueueItem.Status.REJECTED
        item.rejection_reason = reason
        item.save(update_fields=['status', 'rejection_reason', 'updated_at'])

        AgentAuditLog.objects.create(
            queue_item=item,
            action='REJECT',
            entity_type='AgentQueueItem',
            entity_id=str(item.id),
            success=True,
            details={'rejected_by': request.user.email, 'reason': reason},
            performed_by=request.user,
        )
        return Response(AgentQueueItemSerializer(item).data)


class AgentAuditLogViewSet(ModelViewSet):
    """Read-only audit log of all agent actions."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    serializer_class = AgentAuditLogSerializer
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        qs = AgentAuditLog.objects.select_related('queue_item', 'performed_by')
        action_filter = self.request.query_params.get('action')
        success_filter = self.request.query_params.get('success')
        if action_filter:
            qs = qs.filter(action=action_filter)
        if success_filter is not None:
            qs = qs.filter(success=success_filter.lower() == 'true')
        return qs
