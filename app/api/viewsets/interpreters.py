"""Interpreter management viewset with performance, availability, and map endpoints."""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Avg, Sum, Q, Subquery, OuterRef
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from app.api.filters import InterpreterFilter
from app.api.pagination import StandardPagination
from app.api.permissions import IsAdminUser
from app.api.serializers.users import (
    InterpreterListSerializer,
    InterpreterDetailSerializer,
    InterpreterUpdateSerializer,
)
from app.models import (
    Interpreter, InterpreterLocation, Assignment, AssignmentFeedback,
    InterpreterPayment,
)
from app.models.documents import InterpreterContractSignature


def _decrypt_banking(value):
    """Decrypt a Fernet-encrypted banking field stored on the Interpreter model."""
    if not value:
        return None
    try:
        raw = value.encode() if isinstance(value, str) else value
        return InterpreterContractSignature.decrypt_data(raw) or value
    except Exception:
        return value

logger = logging.getLogger(__name__)


class InterpreterViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """
    Interpreter management: list, retrieve, partial_update plus custom actions
    for blocking, availability checking, performance stats, and map data.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InterpreterFilter
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'city',
        'state',
    ]
    ordering_fields = ['user__first_name', 'user__last_name', 'city', 'state']
    ordering = ['user__last_name']

    def get_queryset(self):
        return (
            Interpreter.objects
            .select_related('user')
            .prefetch_related('languages', 'locations')   # locations needed for lat/lng/is_on_mission
            .annotate(
                missions_count=Count(
                    'assignment',
                    filter=Q(assignment__status='COMPLETED'),
                    distinct=True,
                ),
                avg_rating=Avg(
                    'assignment__assignmentfeedback__rating',
                    filter=Q(assignment__status='COMPLETED'),
                ),
            )
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return InterpreterListSerializer
        if self.action in ('partial_update', 'update'):
            return InterpreterUpdateSerializer
        return InterpreterDetailSerializer

    # ------------------------------------------------------------------
    # Block / Unblock
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block an interpreter manually."""
        interpreter = self.get_object()
        reason = request.data.get('reason', '')
        interpreter.is_manually_blocked = True
        interpreter.blocked_reason = reason
        interpreter.blocked_at = timezone.now()
        interpreter.blocked_by = request.user
        interpreter.save(update_fields=[
            'is_manually_blocked', 'blocked_reason', 'blocked_at', 'blocked_by',
        ])
        return Response({'detail': 'Interpreter blocked.'})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        """Unblock an interpreter."""
        interpreter = self.get_object()
        interpreter.is_manually_blocked = False
        interpreter.blocked_reason = None
        interpreter.blocked_at = None
        interpreter.blocked_by = None
        interpreter.save(update_fields=[
            'is_manually_blocked', 'blocked_reason', 'blocked_at', 'blocked_by',
        ])
        return Response({'detail': 'Interpreter unblocked.'})

    # ------------------------------------------------------------------
    # Secure Banking Details (Admin Only)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def banking(self, request, pk=None):
        """Secure endpoint to view unmasked banking information (Admins only)."""
        interpreter = self.get_object()
        
        try:
            # Fetch directly from DB using values() to bypass any model-level property masking if it exists
            values = Interpreter.objects.filter(pk=interpreter.pk).values(
                'bank_name', 'account_holder_name', 'account_type', 'routing_number', 'account_number'
            ).first()
        except Exception as e:
            logger.error(f"Error fetching banking info for interpreter {pk}: {str(e)}")
            values = {}

        return Response({
            'bank_name': values.get('bank_name'),
            'account_holder_name': values.get('account_holder_name'),
            'account_type': values.get('account_type'),
            'routing_number': _decrypt_banking(values.get('routing_number')),
            'account_number': _decrypt_banking(values.get('account_number')),
        })

    # ------------------------------------------------------------------
    # Send password reset email (manual token — project uses custom auth URLs)
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='send-password-reset')
    def send_password_reset(self, request, pk=None):
        """Send a password reset link to the interpreter via the project email backend."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.conf import settings as django_settings

        interpreter = self.get_object()
        user = interpreter.user

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        site_url = getattr(django_settings, 'SITE_URL', 'https://portal.jhbridgetranslation.com').rstrip('/')
        reset_url = f"{site_url}/accounts/reset/{uid}/{token}/"

        try:
            send_mail(
                subject='Reset your JHBridge password',
                message=(
                    f"Hello {user.first_name},\n\n"
                    f"A password reset was requested for your JHBridge interpreter account.\n\n"
                    f"Click the link below to reset your password (valid for 24 hours):\n{reset_url}\n\n"
                    f"If you did not request this, you can safely ignore this email.\n\n"
                    f"— JHBridge Team"
                ),
                from_email='JHBridge <noreply@jhbridgetranslation.com>',
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {user.email} by admin {request.user.email}")
            return Response({'detail': 'Password reset email sent.'})
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {e}")
            return Response({'detail': 'Failed to send email.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ------------------------------------------------------------------
    # Partial update — also allows updating User-level fields
    # ------------------------------------------------------------------
    def partial_update(self, request, *args, **kwargs):
        interpreter = self.get_object()
        user_fields = {}
        for field in ('first_name', 'last_name', 'email', 'phone'):
            if field in request.data:
                user_fields[field] = request.data[field]
        if user_fields:
            for attr, val in user_fields.items():
                setattr(interpreter.user, attr, val)
            interpreter.user.save(update_fields=list(user_fields.keys()))
        return super().partial_update(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Send direct message (email) to interpreter — supports attachment
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        """Send a direct email with optional file attachment to the interpreter."""
        from django.core.mail import EmailMessage

        interpreter = self.get_object()
        user = interpreter.user

        subject = request.data.get('subject', '').strip()
        body = request.data.get('body', '').strip()

        if not subject or not body:
            return Response({'detail': 'Subject and body are required.'}, status=status.HTTP_400_BAD_REQUEST)

        sender_name = f"{request.user.first_name} {request.user.last_name}".strip() or "JHBridge Admin"

        try:
            email = EmailMessage(
                subject=subject,
                body=f"Message from {sender_name} (JHBridge Admin):\n\n{body}",
                from_email='JHBridge Admin <noreply@jhbridgetranslation.com>',
                to=[user.email],
            )
            attachment = request.FILES.get('attachment')
            if attachment:
                email.attach(attachment.name, attachment.read(), attachment.content_type)
            email.send(fail_silently=False)
            logger.info(f"Message {'with attachment' if attachment else ''} sent to {user.email} by {request.user.email}")
            return Response({'detail': 'Message sent.'})
        except Exception as e:
            logger.error(f"Failed to send message to {user.email}: {e}")
            return Response({'detail': 'Failed to send email.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ------------------------------------------------------------------
    # Bulk actions (mirrors Django admin actions, usable from frontend)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='bulk-action')
    def bulk_action(self, request):
        """
        Perform a bulk action on a list of interpreter IDs.
        Body: { action: str, ids: [int], reason?: str, subject?: str, body?: str }
        Supported actions:
          activate | deactivate | block | unblock |
          send_contract | send_onboarding |
          send_reminder_1 | send_reminder_2 | send_reminder_3 |
          suspend | send_password_reset | send_message
        """
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail, EmailMessage
        from django.conf import settings as django_settings

        action_name = request.data.get('action', '').strip()
        ids = request.data.get('ids', [])
        reason = request.data.get('reason', 'Bulk action via Admin').strip()
        subject = request.data.get('subject', '').strip()
        body_text = request.data.get('body', '').strip()

        if not action_name or not ids:
            return Response({'detail': 'action and ids are required.'}, status=status.HTTP_400_BAD_REQUEST)

        interpreters = Interpreter.objects.filter(id__in=ids).select_related('user')
        if not interpreters.exists():
            return Response({'detail': 'No matching interpreters found.'}, status=status.HTTP_404_NOT_FOUND)

        results = {'success': 0, 'skipped': 0, 'failed': 0}

        if action_name == 'activate':
            updated = interpreters.update(active=True)
            results['success'] = updated

        elif action_name == 'deactivate':
            updated = interpreters.update(active=False)
            results['success'] = updated

        elif action_name == 'block':
            updated = interpreters.update(
                is_manually_blocked=True,
                blocked_at=timezone.now(),
                blocked_by=request.user,
                blocked_reason=reason or 'Bulk block via Admin',
            )
            results['success'] = updated

        elif action_name == 'unblock':
            updated = interpreters.update(
                is_manually_blocked=False,
                blocked_at=None,
                blocked_by=None,
                blocked_reason=None,
            )
            results['success'] = updated

        elif action_name == 'send_contract':
            from app.models import ContractInvitation, ContractTrackingEvent
            from app.services.email_service import ContractEmailService
            for interp in interpreters:
                if ContractInvitation.objects.filter(interpreter=interp, status__in=['SENT', 'OPENED', 'REVIEWING']).exists():
                    results['skipped'] += 1
                    continue
                try:
                    inv = ContractInvitation.objects.create(
                        interpreter=interp, created_by=request.user,
                        expires_at=timezone.now() + timedelta(days=30),
                    )
                    ContractTrackingEvent.objects.create(
                        invitation=inv, event_type='EMAIL_SENT',
                        performed_by=request.user, metadata={'source': 'admin_bulk_api'},
                    )
                    if ContractEmailService.send_invitation_email(inv, request):
                        inv.email_sent_at = timezone.now()
                        inv.save(update_fields=['email_sent_at'])
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f"Bulk send_contract failed for {interp.id}: {e}")
                    results['failed'] += 1

        elif action_name == 'send_onboarding':
            from app.models import OnboardingInvitation, OnboardingTrackingEvent
            from app.services.email_service import OnboardingEmailService
            for interp in interpreters:
                if OnboardingInvitation.objects.filter(interpreter=interp, current_phase__in=[
                    'INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED', 'ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED'
                ]).exists():
                    results['skipped'] += 1
                    continue
                try:
                    inv = OnboardingInvitation.objects.create(
                        email=interp.user.email, first_name=interp.user.first_name,
                        last_name=interp.user.last_name, phone=getattr(interp.user, 'phone', ''),
                        user=interp.user, interpreter=interp, created_by=request.user,
                        email_sent_at=timezone.now(),
                    )
                    OnboardingTrackingEvent.objects.create(
                        invitation=inv, event_type='EMAIL_SENT',
                        performed_by=request.user, metadata={'source': 'admin_bulk_api'},
                    )
                    if OnboardingEmailService.send_invitation_email(inv, request):
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f"Bulk send_onboarding failed for {interp.id}: {e}")
                    results['failed'] += 1

        elif action_name in ('send_reminder_1', 'send_reminder_2', 'send_reminder_3'):
            from app.models import ContractInvitation
            from app.services.email_service import ContractReminderService
            level = int(action_name[-1])
            method = getattr(ContractReminderService, f"send_level_{level}")
            for interp in interpreters:
                inv = ContractInvitation.objects.filter(interpreter=interp, status__in=['SENT', 'OPENED', 'REVIEWING']).last()
                try:
                    if method(interp, inv, triggered_by=request.user):
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f"Bulk reminder_{level} failed for {interp.id}: {e}")
                    results['failed'] += 1

        elif action_name == 'suspend':
            from app.services.email_service import ContractViolationService
            for interp in interpreters:
                try:
                    ContractViolationService.send_suspension_email(interp, reason or "Administrative Decision", triggered_by=request.user)
                    interp.is_manually_blocked = True
                    interp.blocked_reason = "Administrative Suspension"
                    interp.blocked_by = request.user
                    interp.blocked_at = timezone.now()
                    interp.save(update_fields=['is_manually_blocked', 'blocked_reason', 'blocked_by', 'blocked_at'])
                    results['success'] += 1
                except Exception as e:
                    logger.error(f"Bulk suspend failed for {interp.id}: {e}")
                    results['failed'] += 1

        elif action_name == 'send_password_reset':
            site_url = getattr(django_settings, 'SITE_URL', 'https://portal.jhbridgetranslation.com').rstrip('/')
            for interp in interpreters:
                user = interp.user
                try:
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = default_token_generator.make_token(user)
                    reset_url = f"{site_url}/accounts/reset/{uid}/{token}/"
                    send_mail(
                        subject='Reset your JHBridge password',
                        message=(
                            f"Hello {user.first_name},\n\n"
                            f"A password reset was requested for your account.\n\n"
                            f"Reset link: {reset_url}\n\n— JHBridge Team"
                        ),
                        from_email='JHBridge <noreply@jhbridgetranslation.com>',
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    results['success'] += 1
                except Exception as e:
                    logger.error(f"Bulk password_reset failed for {user.email}: {e}")
                    results['failed'] += 1

        elif action_name == 'send_message':
            if not subject or not body_text:
                return Response({'detail': 'subject and body are required for send_message.'}, status=status.HTTP_400_BAD_REQUEST)
            sender_name = f"{request.user.first_name} {request.user.last_name}".strip() or "JHBridge Admin"
            attachment = request.FILES.get('attachment')
            for interp in interpreters:
                try:
                    email = EmailMessage(
                        subject=subject,
                        body=f"Message from {sender_name} (JHBridge Admin):\n\n{body_text}",
                        from_email='JHBridge Admin <noreply@jhbridgetranslation.com>',
                        to=[interp.user.email],
                    )
                    if attachment:
                        attachment.seek(0)
                        email.attach(attachment.name, attachment.read(), attachment.content_type)
                    email.send(fail_silently=False)
                    results['success'] += 1
                except Exception as e:
                    logger.error(f"Bulk send_message failed for {interp.user.email}: {e}")
                    results['failed'] += 1

        else:
            return Response({'detail': f'Unknown action: {action_name}'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Bulk action '{action_name}' on {len(ids)} interpreters by {request.user.email}: {results}")
        return Response({
            'detail': f"Action '{action_name}' completed.",
            'results': results,
        })

    # ------------------------------------------------------------------
    # Available interpreters (filtered by criteria)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Find interpreters available for a given set of criteria.
        Query params: language, state, city, date, service_type
        """
        qs = Interpreter.objects.filter(active=True, is_manually_blocked=False).select_related('user')

        language_id = request.query_params.get('language')
        if language_id:
            qs = qs.filter(languages__id=language_id)

        state = request.query_params.get('state')
        if state:
            qs = qs.filter(state__iexact=state)

        city = request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)

        # Exclude interpreters already on mission at the given date
        date_str = request.query_params.get('date')
        if date_str:
            try:
                from django.utils.dateparse import parse_datetime, parse_date
                parsed_date = parse_date(date_str)
                if parsed_date:
                    busy_ids = Assignment.objects.filter(
                        status__in=['CONFIRMED', 'IN_PROGRESS'],
                        start_time__date=parsed_date,
                        interpreter__isnull=False,
                    ).values_list('interpreter_id', flat=True)
                    qs = qs.exclude(id__in=busy_ids)
            except (ValueError, TypeError):
                pass

        qs = qs.distinct()
        data = []
        for interp in qs[:100]:
            data.append({
                'id': interp.id,
                'first_name': interp.user.first_name,
                'last_name': interp.user.last_name,
                'email': interp.user.email,
                'phone': interp.user.phone,
                'city': interp.city,
                'state': interp.state,
                'hourly_rate': str(interp.hourly_rate) if interp.hourly_rate else None,
                'languages': list(interp.languages.values_list('name', flat=True)),
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Performance stats for a single interpreter
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Performance metrics for a single interpreter."""
        interpreter = self.get_object()

        assignments_qs = Assignment.objects.filter(interpreter=interpreter)

        missions_completed = assignments_qs.filter(status='COMPLETED').count()

        total_decided = assignments_qs.filter(
            status__in=['CONFIRMED', 'COMPLETED', 'CANCELLED']
        ).count()
        accepted = assignments_qs.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).count()
        acceptance_rate = (
            round(accepted / total_decided * 100, 1) if total_decided > 0 else 0
        )

        total_possible_show = assignments_qs.filter(
            status__in=['COMPLETED', 'NO_SHOW']
        ).count()
        no_shows = assignments_qs.filter(status='NO_SHOW').count()
        no_show_rate = (
            round(no_shows / total_possible_show * 100, 1) if total_possible_show > 0 else 0
        )

        avg_rating = (
            AssignmentFeedback.objects
            .filter(assignment__interpreter=interpreter)
            .aggregate(avg=Avg('rating'))['avg']
        )

        total_earned = (
            InterpreterPayment.objects
            .filter(interpreter=interpreter, status='COMPLETED')
            .aggregate(total=Sum('amount'))['total'] or Decimal('0')
        )

        return Response({
            'missions_completed': missions_completed,
            'acceptance_rate': acceptance_rate,
            'no_show_rate': no_show_rate,
            'avg_rating': round(avg_rating, 2) if avg_rating else None,
            'total_earned': str(total_earned),
        })

    # ------------------------------------------------------------------
    # Payments for a single interpreter
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """List interpreter payments for a specific interpreter."""
        interpreter = self.get_object()
        payments = (
            InterpreterPayment.objects
            .filter(interpreter=interpreter)
            .select_related('assignment', 'transaction')
            .order_by('-created_at')[:50]
        )

        data = []
        for p in payments:
            data.append({
                'id': p.id,
                'reference_number': p.reference_number,
                'amount': str(p.amount),
                'status': p.status,
                'payment_method': p.payment_method,
                'scheduled_date': p.scheduled_date,
                'processed_date': p.processed_date,
                'assignment_id': p.assignment_id,
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Live locations (latest per active interpreter)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'], url_path='live-locations')
    def live_locations(self, request):
        """Latest GPS location per active interpreter."""
        # Subquery to get the latest location per interpreter
        latest_location = (
            InterpreterLocation.objects
            .filter(interpreter=OuterRef('pk'))
            .order_by('-timestamp')
            .values('id')[:1]
        )

        locations = (
            InterpreterLocation.objects
            .filter(
                id__in=Subquery(latest_location),
                interpreter__active=True,
            )
            .select_related('interpreter__user', 'current_assignment')
        )

        data = []
        for loc in locations:
            interp = loc.interpreter
            data.append({
                'interpreter_id': interp.id,
                'name': f"{interp.user.first_name} {interp.user.last_name}",
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'accuracy': loc.accuracy,
                'is_on_mission': loc.is_on_mission,
                'current_assignment_id': loc.current_assignment_id,
                'timestamp': loc.timestamp,
            })

        return Response(data)

    # ------------------------------------------------------------------
    # Map data (all interpreters with city/state for geocoding)
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def map(self, request):
        """All interpreters with location data, radius and cities for strategic map visualization."""
        qs = (
            Interpreter.objects
            .filter(active=True)
            .select_related('user')
            .prefetch_related('languages')
            .values(
                'id',
                'user__first_name',
                'user__last_name',
                'address',
                'city',
                'state',
                'zip_code',
                'radius_of_service',
                'cities_willing_to_cover',
                'is_manually_blocked',
            )
        )

        data = []
        for interp in qs:
            langs = list(
                Interpreter.objects.get(pk=interp['id']).languages.values_list('name', flat=True)[:5]
            )
            data.append({
                'id': interp['id'],
                'first_name': interp['user__first_name'],
                'last_name': interp['user__last_name'],
                'address': interp['address'],
                'city': interp['city'],
                'state': interp['state'],
                'zip_code': interp['zip_code'],
                'radius_of_service': interp['radius_of_service'],
                'cities_willing_to_cover': interp['cities_willing_to_cover'],
                'is_manually_blocked': interp['is_manually_blocked'],
                'languages': langs,
            })

        return Response(data)
