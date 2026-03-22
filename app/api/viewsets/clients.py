"""Client management viewset with history, invoices, and assignments sub-resources."""
import logging
import secrets
from itertools import chain
from operator import attrgetter

from django.db.models import Count, Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.users import (
    ClientListSerializer,
    ClientDetailSerializer,
    ClientCreateSerializer,
    ClientUpdateSerializer,
)
from app.models import (
    Client, QuoteRequest, Assignment, ClientPayment, Invoice, User,
)

logger = logging.getLogger(__name__)


class ClientViewSet(ModelViewSet):
    """Client CRUD with annotated metrics and sub-resource actions."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        'company_name',
        'user__first_name',
        'user__last_name',
        'user__email',
        'city',
        'state',
    ]
    ordering_fields = ['company_name', 'user__last_name']
    ordering = ['company_name']

    def get_queryset(self):
        return (
            Client.objects
            .select_related('user', 'preferred_language')
            .annotate(
                missions_count=Count(
                    'assignment',
                    filter=Q(assignment__status='COMPLETED'),
                ),
                total_revenue=Sum(
                    'clientpayment__total_amount',
                    filter=Q(clientpayment__status='COMPLETED'),
                ),
            )
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ClientListSerializer
        if self.action == 'create':
            return ClientCreateSerializer
        if self.action in ('partial_update', 'update'):
            return ClientUpdateSerializer
        return ClientDetailSerializer

    # ------------------------------------------------------------------
    # Create — admin creates User + Client in one call
    # ------------------------------------------------------------------
    def create(self, request, *args, **kwargs):
        """
        Admin-side client creation.
        Accepts user fields (first_name, last_name, email, phone) + client fields.
        Creates the User if the email is not yet registered, then creates the Client.
        """
        first_name = request.data.get('first_name', '').strip()
        last_name  = request.data.get('last_name', '').strip()
        email      = request.data.get('email', '').strip().lower()
        phone      = request.data.get('phone', '').strip()

        if not email:
            return Response(
                {'detail': 'email is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Re-use existing user or create a new one
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone or None,
                role=User.Roles.CLIENT,
                is_active=True,
                password=secrets.token_urlsafe(20),
            )
        elif Client.objects.filter(user=user).exists():
            return Response(
                {'detail': f'A client profile already exists for {email}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build client data with resolved user FK
        client_data = {k: v for k, v in request.data.items()
                       if k not in ('first_name', 'last_name', 'email', 'phone')}
        client_data['user'] = user.id

        serializer = ClientCreateSerializer(data=client_data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()

        return Response(
            ClientDetailSerializer(client).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # History timeline
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Unified timeline of a client's QuoteRequests, Assignments,
        ClientPayments, and Invoices sorted by date descending.
        """
        client = self.get_object()

        quotes = list(
            QuoteRequest.objects.filter(client=client)
            .values('id', 'status', 'created_at', 'service_type__name')
            .order_by('-created_at')[:50]
        )
        for q in quotes:
            q['type'] = 'quote_request'
            q['date'] = q.pop('created_at')

        assignments = list(
            Assignment.objects.filter(client=client)
            .values('id', 'status', 'start_time', 'service_type__name')
            .order_by('-start_time')[:50]
        )
        for a in assignments:
            a['type'] = 'assignment'
            a['date'] = a.pop('start_time')

        payments = list(
            ClientPayment.objects.filter(client=client)
            .values('id', 'status', 'payment_date', 'total_amount')
            .order_by('-payment_date')[:50]
        )
        for p in payments:
            p['type'] = 'payment'
            p['date'] = p.pop('payment_date')

        invoices = list(
            Invoice.objects.filter(client=client)
            .values('id', 'invoice_number', 'status', 'issued_date', 'total')
            .order_by('-issued_date')[:50]
        )
        for i in invoices:
            i['type'] = 'invoice'
            i['date'] = i.pop('issued_date')

        timeline = sorted(
            quotes + assignments + payments + invoices,
            key=lambda x: x.get('date') or '',
            reverse=True,
        )

        return Response(timeline[:100])

    # ------------------------------------------------------------------
    # Invoices sub-resource
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """List invoices for a specific client."""
        client = self.get_object()
        invoices = (
            Invoice.objects
            .filter(client=client)
            .order_by('-issued_date')
        )
        data = list(invoices.values(
            'id', 'invoice_number', 'status', 'subtotal', 'tax_amount',
            'total', 'issued_date', 'due_date', 'paid_date',
        ))
        return Response(data)

    # ------------------------------------------------------------------
    # Assignments sub-resource
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """List assignments for a specific client."""
        client = self.get_object()
        assignments = (
            Assignment.objects
            .filter(client=client)
            .select_related('interpreter__user', 'service_type', 'source_language', 'target_language')
            .order_by('-start_time')
        )

        data = []
        for a in assignments[:100]:
            interpreter_name = ''
            if a.interpreter and a.interpreter.user:
                interpreter_name = f"{a.interpreter.user.first_name} {a.interpreter.user.last_name}"
            data.append({
                'id': a.id,
                'status': a.status,
                'start_time': a.start_time,
                'end_time': a.end_time,
                'interpreter': interpreter_name,
                'service_type': a.service_type.name if a.service_type else '',
                'source_language': a.source_language.name if a.source_language else '',
                'target_language': a.target_language.name if a.target_language else '',
                'city': a.city,
                'state': a.state,
            })

        return Response(data)
