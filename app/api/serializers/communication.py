from rest_framework import serializers

from app.models import (
    Notification, ContactMessage, AssignmentFeedback, EmailLog,
    User, Assignment, AuditLog,
)


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class NotificationSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id', 'recipient', 'recipient_email',
            'type', 'title', 'content',
            'read', 'link', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('recipient')


# ---------------------------------------------------------------------------
# ContactMessage
# ---------------------------------------------------------------------------

class ContactMessageSerializer(serializers.ModelSerializer):
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ContactMessage
        fields = (
            'id', 'name', 'email', 'subject', 'message',
            'created_at', 'processed', 'processed_by',
            'processed_by_name', 'processed_at', 'notes',
        )
        read_only_fields = ('id', 'created_at')

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip()
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('processed_by')


# ---------------------------------------------------------------------------
# AssignmentFeedback
# ---------------------------------------------------------------------------

class AssignmentFeedbackSerializer(serializers.ModelSerializer):
    assignment_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    assignment = serializers.PrimaryKeyRelatedField(
        queryset=Assignment.objects.all()
    )
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    class Meta:
        model = AssignmentFeedback
        fields = (
            'id', 'assignment', 'assignment_display',
            'rating', 'comments',
            'created_at', 'created_by', 'created_by_name',
        )
        read_only_fields = ('id', 'created_at')

    def get_assignment_display(self, obj):
        return str(obj.assignment) if obj.assignment else None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('assignment', 'created_by')


# ---------------------------------------------------------------------------
# EmailLog
# ---------------------------------------------------------------------------

class EmailLogListSerializer(serializers.ModelSerializer):
    """Lightweight email log for list/inbox views."""

    class Meta:
        model = EmailLog
        fields = (
            'id', 'gmail_id', 'gmail_thread_id',
            'from_email', 'from_name', 'subject',
            'received_at',
            'category', 'priority', 'ai_confidence',
            'is_read', 'is_processed', 'has_attachments',
            'created_at',
        )

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.only(
            'id', 'gmail_id', 'gmail_thread_id',
            'from_email', 'from_name', 'subject',
            'received_at', 'category', 'priority', 'ai_confidence',
            'is_read', 'is_processed', 'has_attachments', 'created_at',
        )


class EmailLogDetailSerializer(serializers.ModelSerializer):
    """Full email log with body, AI data, and linked entities."""

    processed_by_name = serializers.SerializerMethodField()
    linked_client_name = serializers.SerializerMethodField()
    linked_assignment_display = serializers.SerializerMethodField()

    class Meta:
        model = EmailLog
        fields = (
            'id', 'gmail_id', 'gmail_thread_id',
            'from_email', 'from_name', 'subject', 'body_preview',
            'received_at',
            'category', 'priority',
            'ai_confidence', 'ai_extracted_data', 'ai_suggested_actions',
            'is_read', 'is_processed',
            'processed_by', 'processed_by_name', 'processed_at',
            'linked_client', 'linked_client_name',
            'linked_assignment', 'linked_assignment_display',
            'linked_quote_request', 'linked_onboarding',
            'has_attachments',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip()
        return None

    def get_linked_client_name(self, obj):
        if obj.linked_client:
            return obj.linked_client.company_name or str(obj.linked_client)
        return None

    def get_linked_assignment_display(self, obj):
        if obj.linked_assignment:
            return str(obj.linked_assignment)
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'processed_by', 'linked_client',
            'linked_assignment', 'linked_quote_request',
            'linked_onboarding',
        )


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'user_email',
            'action', 'model_name', 'object_id',
            'changes', 'ip_address', 'timestamp',
        )
        read_only_fields = ('id', 'timestamp')
