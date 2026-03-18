from rest_framework import serializers

from app.models import ContractInvitation, ContractTrackingEvent


# ---------------------------------------------------------------------------
# Tracking Event (nested helper)
# ---------------------------------------------------------------------------

class ContractTrackingEventSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ContractTrackingEvent
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
# ContractInvitation
# ---------------------------------------------------------------------------

class ContractInvitationSerializer(serializers.ModelSerializer):
    """Read serializer for contract invitations with timeline events."""

    interpreter_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    voided_by_name = serializers.SerializerMethodField()
    tracking_events = ContractTrackingEventSerializer(many=True, read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = ContractInvitation
        fields = (
            'id', 'invitation_number',
            'interpreter', 'interpreter_name',
            'contract_signature',
            'status', 'version',
            'created_by', 'created_by_name',
            'voided_by', 'voided_by_name', 'void_reason',
            # Timestamps
            'created_at', 'email_sent_at', 'email_opened_at',
            'link_clicked_at', 'link_clicked_type',
            'signed_at', 'voided_at', 'expires_at',
            'is_expired',
            # PDF
            'pdf_s3_key',
            # Timeline
            'tracking_events',
        )

    def get_interpreter_name(self, obj):
        if obj.interpreter and obj.interpreter.user:
            u = obj.interpreter.user
            return f"{u.first_name} {u.last_name}".strip()
        return None

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

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'interpreter__user', 'created_by', 'voided_by',
            'contract_signature',
        ).prefetch_related('tracking_events__performed_by')
