"""Settings viewsets: ServiceType, Language, CompanyInfo, APIKey."""
import logging
import secrets

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from app.api.permissions import IsAdminUser
from app.api.serializers.services import ServiceTypeSerializer, LanguageSerializer
from app.api.serializers.settings import (
    APIKeySerializer, APIKeyCreateSerializer, CompanyInfoSerializer,
)
from app.models import ServiceType, Language, APIKey

logger = logging.getLogger(__name__)


class ServiceTypeViewSet(ModelViewSet):
    """CRUD for service types."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = ServiceTypeSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'base_rate', 'active']
    ordering = ['name']

    def get_queryset(self):
        return ServiceType.objects.all()

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle active status."""
        service_type = self.get_object()
        service_type.active = not service_type.active
        service_type.save(update_fields=['active'])
        return Response({
            'id': service_type.id,
            'active': service_type.active,
        })


class LanguageViewSet(ModelViewSet):
    """CRUD for languages."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = LanguageSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code', 'is_active']
    ordering = ['name']
    pagination_class = None  # languages are reference data — always return full list

    def get_queryset(self):
        return Language.objects.all()

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle is_active status."""
        language = self.get_object()
        language.is_active = not language.is_active
        language.save(update_fields=['is_active'])
        return Response({
            'id': language.id,
            'is_active': language.is_active,
        })


class CompanyInfoView(APIView):
    """Read-only company/environment info from Django settings."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        serializer = CompanyInfoSerializer({})
        return Response(serializer.data)


class APIKeyViewSet(ModelViewSet):
    """API key management for the authenticated admin user."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return APIKeyCreateSerializer
        return APIKeySerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def rotate(self, request, pk=None):
        """Generate a new key value, invalidating the old one."""
        api_key = self.get_object()
        api_key.key = secrets.token_hex(32)
        api_key.save(update_fields=['key'])
        return Response({
            'id': str(api_key.id),
            'key': api_key.key,
            'detail': 'Key rotated. Store it now — it will not be shown again.',
        })
