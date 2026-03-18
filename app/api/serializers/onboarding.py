from rest_framework import serializers
from django.utils import timezone

from app.models import (
    OnboardingInvitation, OnboardingTrackingEvent, User,
)


# ---------------------------------------------------------------------------
# Tracking events
# ---------------------------------------------------------------------------

class OnboardingTrackingEventSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTrackingEvent
        fields = (
            'id', 'invitation', 'event_type',
            'timestamp', 'metadata',
            'performed_by', 'performed_by_name',
        )
        read_only_fields = ('id', 'timestamp')

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return f"{obj.performed_by.first_name} {obj.performed_by.last_name}".strip()
        return None


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class OnboardingListSerializer(serializers.ModelSerializer):
    """Lightweight onboarding invitation for table views."""

    full_name = serializers.CharField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingInvitation
        fields = (
            'id', 'invitation_number', 'email',
            'first_name', 'last_name', 'full_name', 'phone',
            'current_phase', 'version',
            'created_by', 'created_by_name',
            'created_at', 'expires_at',
            'is_expired', 'days_remaining',
        )

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_days_remaining(self, obj):
        if obj.current_phase in ('COMPLETED', 'VOIDED', 'EXPIRED'):
            return 0
        delta = obj.expires_at - timezone.now()
        return max(0, delta.days)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('created_by')


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class OnboardingDetailSerializer(serializers.ModelSerializer):
    """Full onboarding invitation with timeline events."""

    full_name = serializers.CharField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    voided_by_name = serializers.SerializerMethodField()
    tracking_events = OnboardingTrackingEventSerializer(many=True, read_only=True)
    is_expired = serializers.SerializerMethodField()

    # Linked entity info
    user_email = serializers.EmailField(source='user.email', read_only=True, default=None)
    interpreter_id = serializers.IntegerField(source='interpreter.id', read_only=True, default=None)
    contract_invitation_id = serializers.UUIDField(
        source='contract_invitation.id', read_only=True, default=None
    )
    languages = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingInvitation
        fields = (
            'id', 'invitation_number',
            'email', 'first_name', 'last_name', 'full_name', 'phone',
            'current_phase', 'version', 'token',
            # Linked entities
            'user', 'user_email',
            'interpreter', 'interpreter_id',
            'contract_invitation', 'contract_invitation_id',
            'languages',
            # Admin
            'created_by', 'created_by_name',
            'voided_by', 'voided_by_name',
            'void_reason',
            # Timestamps
            'created_at', 'email_sent_at', 'email_opened_at',
            'welcome_viewed_at', 'account_created_at',
            'profile_completed_at', 'contract_started_at',
            'completed_at', 'voided_at', 'expires_at',
            'is_expired',
            # Timeline
            'tracking_events',
        )

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_voided_by_name(self, obj):
        if obj.voided_by:
            return f"{obj.voided_by.first_name} {obj.voided_by.last_name}".strip()
        return None

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_languages(self, obj):
        if obj.interpreter:
            return list(obj.interpreter.languages.values_list('name', flat=True))
        return []

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'created_by', 'voided_by', 'user', 'interpreter', 'contract_invitation',
        ).prefetch_related('tracking_events__performed_by', 'interpreter__languages')


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class OnboardingCreateSerializer(serializers.ModelSerializer):
    """Create a new onboarding invitation."""

    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    class Meta:
        model = OnboardingInvitation
        fields = (
            'id', 'email', 'first_name', 'last_name', 'phone',
            'created_by',
        )
        read_only_fields = ('id',)

    def validate_email(self, value):
        # Check for active (non-voided, non-expired, non-completed) invitations
        active_exists = OnboardingInvitation.objects.filter(
            email__iexact=value,
            current_phase__in=['INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED',
                               'ACCOUNT_CREATED', 'PROFILE_COMPLETED',
                               'CONTRACT_STARTED'],
        ).exists()
        if active_exists:
            raise serializers.ValidationError(
                'An active onboarding invitation already exists for this email.'
            )
        return value


# ---------------------------------------------------------------------------
# Pipeline (non-model serializer for Kanban / funnel view)
# ---------------------------------------------------------------------------

class OnboardingPipelineSerializer(serializers.Serializer):
    """
    Returns onboarding invitations grouped by phase for pipeline view.
    The view is responsible for building the data dict; this serializer
    validates / renders it.
    """

    INVITED = OnboardingListSerializer(many=True)
    EMAIL_OPENED = OnboardingListSerializer(many=True)
    WELCOME_VIEWED = OnboardingListSerializer(many=True)
    ACCOUNT_CREATED = OnboardingListSerializer(many=True)
    PROFILE_COMPLETED = OnboardingListSerializer(many=True)
    CONTRACT_STARTED = OnboardingListSerializer(many=True)
    COMPLETED = OnboardingListSerializer(many=True)
    VOIDED = OnboardingListSerializer(many=True)
    EXPIRED = OnboardingListSerializer(many=True)
