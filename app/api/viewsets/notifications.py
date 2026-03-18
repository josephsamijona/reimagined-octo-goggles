"""Notification viewset for all authenticated users."""
import logging   ## what about automatique email sending and 

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin

from app.api.pagination import SmallPagination
from app.api.serializers.communication import NotificationSerializer
from app.models import Notification

logger = logging.getLogger(__name__)


class NotificationViewSet(ListModelMixin, GenericViewSet):
    """
    Notifications for the current user.
    list, mark_read (single), mark_all_read.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = SmallPagination
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return (
            Notification.objects
            .filter(recipient=self.request.user)
            .order_by('-created_at')
        )

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        try:
            notification = self.get_queryset().get(pk=pk)
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        notification.read = True
        notification.save(update_fields=['read'])

        return Response({'id': notification.id, 'read': True})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user."""
        count = self.get_queryset().filter(read=False).update(read=True)
        return Response({'detail': f'{count} notifications marked as read.', 'count': count})
