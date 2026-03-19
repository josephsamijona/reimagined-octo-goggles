"""Quote request, quote, and public quote request viewsets."""
import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from app.api.filters import QuoteRequestFilter, PublicQuoteRequestFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.services import (
    QuoteRequestListSerializer,
    QuoteRequestDetailSerializer,
    QuoteRequestCreateSerializer,
    QuoteListSerializer,
    QuoteDetailSerializer,
    PublicQuoteRequestListSerializer,
)
from app.api.services.reference_service import generate_unique_reference
from app.models import QuoteRequest, Quote, PublicQuoteRequest

logger = logging.getLogger(__name__)


class QuoteRequestViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet):
    """Quote request management: list, create, retrieve, generate_quote."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = QuoteRequestFilter
    search_fields = ['client__company_name', 'city', 'state']
    ordering_fields = ['created_at', 'requested_date', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            QuoteRequest.objects
            .select_related(
                'client__user',
                'service_type',
                'source_language',
                'target_language',
            )
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return QuoteRequestListSerializer
        if self.action == 'create':
            return QuoteRequestCreateSerializer
        return QuoteRequestDetailSerializer

    @action(detail=True, methods=['post'], url_path='generate-quote')
    def generate_quote(self, request, pk=None):
        """Generate a quote from a quote request."""
        quote_request = self.get_object()

        if hasattr(quote_request, 'quote'):
            return Response(
                {'detail': 'A quote already exists for this request.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = request.data.get('amount')
        tax_amount = request.data.get('tax_amount', 0)
        valid_until = request.data.get('valid_until')
        terms = request.data.get('terms', '')

        if not amount or not valid_until:
            return Response(
                {'detail': 'amount and valid_until are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate collision-safe reference number
        ref = generate_unique_reference('QT', Quote)

        quote = Quote.objects.create(
            quote_request=quote_request,
            reference_number=ref,
            amount=amount,
            tax_amount=tax_amount,
            valid_until=valid_until,
            terms=terms,
            status=Quote.Status.DRAFT,
            created_by=request.user,
        )

        quote_request.status = QuoteRequest.Status.QUOTED
        quote_request.save()

        return Response({
            'id': quote.id,
            'reference_number': quote.reference_number,
            'amount': str(quote.amount),
            'tax_amount': str(quote.tax_amount),
            'valid_until': str(quote.valid_until),
            'status': quote.status,
        }, status=status.HTTP_201_CREATED)


class QuoteViewSet(ListModelMixin, GenericViewSet):
    """Quote management: list + send action."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            Quote.objects
            .select_related(
                'quote_request__client__user',
                'quote_request__service_type',
                'created_by',
            )
            .all()
        )

    def get_serializer_class(self):
        return QuoteListSerializer

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark a quote as SENT and notify the client."""
        quote = self.get_object()

        if quote.status != Quote.Status.DRAFT:
            return Response(
                {'detail': f'Cannot send quote in status {quote.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quote.status = Quote.Status.SENT
        quote.save()

        # Send email notification to client
        try:
            from app.models import Notification
            client_user = quote.quote_request.client.user
            Notification.objects.create(
                recipient=client_user,
                type='QUOTE_READY',
                title='Your quote is ready',
                content=f"Quote {quote.reference_number} for ${quote.amount} is ready for review.",
                link=f'/client/quotes/{quote.id}/',
            )
        except Exception as e:
            logger.error(f"Failed to notify client about quote {quote.id}: {e}")

        return Response({
            'id': quote.id,
            'status': quote.status,
            'reference_number': quote.reference_number,
        })


class PublicQuoteRequestViewSet(ListModelMixin, GenericViewSet):
    """Public quote requests: list + process action."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PublicQuoteRequestFilter
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            PublicQuoteRequest.objects
            .select_related('service_type', 'source_language', 'target_language', 'processed_by')
            .all()
        )

    def get_serializer_class(self):
        return PublicQuoteRequestListSerializer

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Mark a public quote request as processed."""
        pqr = self.get_object()

        if pqr.processed:
            return Response(
                {'detail': 'Already processed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pqr.processed = True
        pqr.processed_by = request.user
        pqr.processed_at = timezone.now()
        pqr.admin_notes = request.data.get('admin_notes', '')
        pqr.save()

        return Response({
            'id': pqr.id,
            'processed': pqr.processed,
            'processed_at': pqr.processed_at,
        })
