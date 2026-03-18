"""Onboarding viewset: invitation lifecycle management."""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.api.filters import OnboardingFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.onboarding import (
    OnboardingListSerializer,
    OnboardingDetailSerializer,
    OnboardingCreateSerializer,
)
from app.models import OnboardingInvitation
import app.services.onboarding_service as onboarding_svc

logger = logging.getLogger(__name__)


class OnboardingViewSet(ModelViewSet):
    """
    Onboarding invitation management.
    list, create (auto-sends email), retrieve, resend, void, advance, extend, pipeline.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OnboardingFilter
    search_fields = ['first_name', 'last_name', 'email', 'invitation_number']
    ordering_fields = ['created_at', 'current_phase']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return (
            OnboardingInvitation.objects
            .select_related('user', 'interpreter', 'created_by', 'voided_by')
            .prefetch_related('tracking_events')
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return OnboardingListSerializer
        if self.action == 'create':
            return OnboardingCreateSerializer
        return OnboardingDetailSerializer

    def perform_create(self, serializer):
        """Create invitation and automatically send email via service."""
        data = serializer.validated_data
        try:
            onboarding_svc.create_invitation(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data.get('phone', ''),
                created_by=self.request.user,
                request=self.request,
            )
        except Exception as e:
            logger.error("Failed to create onboarding invitation: %s", e, exc_info=True)
            # Fall back to plain save so the object is at least persisted
            serializer.save(created_by=self.request.user)

    # ------------------------------------------------------------------
    # Resend: voids old + creates new (consistent with admin behaviour)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Void this invitation and create a fresh one with the next version.

        Uses the phase-appropriate nudge template so the email content matches
        where the interpreter is stuck in the funnel.
        """
        invitation = self.get_object()

        if invitation.current_phase in ('COMPLETED', 'VOIDED', 'EXPIRED'):
            return Response(
                {'detail': f'Cannot resend for invitation in phase {invitation.current_phase}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_type = onboarding_svc.PHASE_TEMPLATE_MAP.get(invitation.current_phase, 'RESEND_ISSUE')

        try:
            new_inv = onboarding_svc.resend_invitation(
                invitation,
                created_by=request.user,
                template_type=template_type,
                request=request,
            )
            return Response({
                'detail': 'New invitation created and email sent.',
                'new_invitation_number': new_inv.invitation_number,
                'template_type': template_type,
            })
        except Exception as e:
            logger.error("Failed to resend onboarding invitation: %s", e, exc_info=True)
            return Response(
                {'detail': 'Failed to resend invitation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Void invitation
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Void an onboarding invitation."""
        invitation = self.get_object()
        reason = request.data.get('reason', '')
        try:
            onboarding_svc.void_invitation(invitation, voided_by=request.user, reason=reason)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Invitation voided.', 'current_phase': invitation.current_phase})

    # ------------------------------------------------------------------
    # Advance to next phase (manual)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def advance(self, request, pk=None):
        """Manually advance an invitation to the next phase."""
        invitation = self.get_object()
        try:
            onboarding_svc.advance_invitation(invitation)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': f'Advanced to {invitation.current_phase}.',
            'current_phase': invitation.current_phase,
        })

    # ------------------------------------------------------------------
    # Extend expiration
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """Extend the expiration date of an invitation."""
        invitation = self.get_object()
        days = int(request.data.get('days', 14))
        onboarding_svc.extend_invitation(invitation, days=days)
        return Response({
            'detail': f'Expiration extended by {days} days.',
            'expires_at': invitation.expires_at,
        })

    # ------------------------------------------------------------------
    # Pipeline (kanban data)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """Group active onboarding invitations by phase for kanban display."""
        invitations = (
            OnboardingInvitation.objects
            .exclude(current_phase__in=['COMPLETED', 'VOIDED', 'EXPIRED'])
            .values(
                'id', 'invitation_number', 'first_name', 'last_name',
                'email', 'current_phase', 'created_at', 'expires_at',
            )
            .order_by('created_at')
        )

        from collections import defaultdict
        grouped = defaultdict(list)
        for inv in invitations:
            grouped[inv['current_phase']].append(inv)

        return Response(dict(grouped))
