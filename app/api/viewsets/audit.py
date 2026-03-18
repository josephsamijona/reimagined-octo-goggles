"""Audit log viewset: read-only list with CSV export."""
import csv
import logging

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from app.api.filters import AuditLogFilter
from app.api.pagination import LargePagination
from app.api.permissions import IsAdminUser
from app.api.serializers.communication import AuditLogSerializer
from app.models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogViewSet(ListModelMixin, GenericViewSet):
    """Read-only audit log with filtering and CSV export."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = LargePagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AuditLogFilter
    search_fields = ['action', 'model_name', 'object_id']
    ordering_fields = ['timestamp', 'action', 'model_name']
    ordering = ['-timestamp']
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        return (
            AuditLog.objects
            .select_related('user')
            .all()
        )

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export audit logs as CSV."""
        qs = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_log.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Timestamp', 'User', 'Action', 'Model', 'Object ID', 'Changes', 'IP Address',
        ])

        for log in qs.iterator(chunk_size=500):
            user_email = log.user.email if log.user else ''
            writer.writerow([
                log.timestamp.isoformat() if log.timestamp else '',
                user_email,
                log.action,
                log.model_name,
                log.object_id,
                str(log.changes) if log.changes else '',
                log.ip_address or '',
            ])

        return response
