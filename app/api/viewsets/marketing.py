"""Marketing viewset: leads, campaigns, and analytics."""
import logging
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth, ExtractMonth
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.api.filters import LeadFilter, CampaignFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.marketing import (
    LeadListSerializer,
    LeadDetailSerializer,
    LeadCreateSerializer,
    LeadUpdateSerializer,
    CampaignListSerializer,
    CampaignDetailSerializer,
    CampaignCreateSerializer,
    CampaignUpdateSerializer,
)
from app.models import (
    Lead, Campaign, Client, User, QuoteRequest, Assignment, Language,
    PublicQuoteRequest,
)

logger = logging.getLogger(__name__)


class LeadViewSet(ModelViewSet):
    """Lead management with conversion to client."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LeadFilter
    search_fields = ['company_name', 'contact_name', 'email', 'phone']
    ordering_fields = ['created_at', 'stage', 'estimated_monthly_value']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            Lead.objects
            .select_related(
                'assigned_to', 'converted_client', 'public_quote_request', 'contact_message',
            )
            .prefetch_related('languages_needed')
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        if self.action == 'create':
            return LeadCreateSerializer
        if self.action in ('partial_update', 'update'):
            return LeadUpdateSerializer
        return LeadDetailSerializer

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """Convert a lead into a Client."""
        lead = self.get_object()

        if lead.stage == 'CONVERTED':
            return Response(
                {'detail': 'Lead is already converted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lead.converted_client:
            return Response(
                {'detail': 'Lead already has a linked client.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create user account for the client
        try:
            user = User.objects.create_user(
                username=lead.email,
                email=lead.email,
                first_name=lead.contact_name.split()[0] if lead.contact_name else '',
                last_name=' '.join(lead.contact_name.split()[1:]) if lead.contact_name else '',
                role='CLIENT',
                password=User.objects.make_random_password(),
            )

            client = Client.objects.create(
                user=user,
                company_name=lead.company_name,
                address=request.data.get('address', ''),
                city=request.data.get('city', ''),
                state=request.data.get('state', ''),
                zip_code=request.data.get('zip_code', ''),
                phone=lead.phone,
                email=lead.email,
            )

            lead.converted_client = client
            lead.converted_at = timezone.now()
            lead.stage = 'CONVERTED'
            lead.save()

            return Response({
                'detail': 'Lead converted to client.',
                'client_id': client.id,
                'user_id': user.id,
            })
        except Exception as e:
            logger.error(f"Failed to convert lead {pk}: {e}")
            return Response(
                {'detail': f'Conversion failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CampaignViewSet(ModelViewSet):
    """Campaign management."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CampaignFilter
    search_fields = ['name']
    ordering_fields = ['created_at', 'start_date', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return Campaign.objects.select_related('created_by').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return CampaignListSerializer
        if self.action == 'create':
            return CampaignCreateSerializer
        if self.action in ('partial_update', 'update'):
            return CampaignUpdateSerializer
        return CampaignDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MarketingAnalyticsViewSet(ModelViewSet):
    """
    Marketing analytics endpoints.
    Registered separately to provide /marketing/analytics/ namespace.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    # We don't need a real queryset; this is a pure analytics viewset
    def get_queryset(self):
        return Lead.objects.none()

    @action(detail=False, methods=['get'], url_path='top-languages')
    def top_languages(self, request):
        """Top languages by demand (from completed assignments)."""
        data = (
            Assignment.objects
            .filter(status='COMPLETED')
            .values('source_language__name', 'target_language__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='demand-by-state')
    def demand_by_state(self, request):
        """Service demand by state."""
        data = (
            Assignment.objects
            .values('state')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='seasonal-trend')
    def seasonal_trend(self, request):
        """Monthly assignment volume (seasonal trend)."""
        data = (
            Assignment.objects
            .annotate(month=TruncMonth('start_time'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='conversion-funnel')
    def conversion_funnel(self, request):
        """Lead conversion funnel metrics."""
        total_leads = Lead.objects.count()
        contacted = Lead.objects.filter(stage__in=['CONTACTED', 'QUOTE_SENT', 'NEGOTIATING', 'CONVERTED']).count()
        quote_sent = Lead.objects.filter(stage__in=['QUOTE_SENT', 'NEGOTIATING', 'CONVERTED']).count()
        negotiating = Lead.objects.filter(stage__in=['NEGOTIATING', 'CONVERTED']).count()
        converted = Lead.objects.filter(stage='CONVERTED').count()
        lost = Lead.objects.filter(stage='LOST').count()

        return Response({
            'total_leads': total_leads,
            'contacted': contacted,
            'quote_sent': quote_sent,
            'negotiating': negotiating,
            'converted': converted,
            'lost': lost,
            'conversion_rate': round(converted / total_leads * 100, 1) if total_leads > 0 else 0,
        })
