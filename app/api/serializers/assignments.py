from decimal import Decimal
from math import ceil

from rest_framework import serializers

from app.models import (
    Assignment, Client, Interpreter, ServiceType, Language,
)


# ---------------------------------------------------------------------------
# Lightweight nested helpers (avoid circular imports)
# ---------------------------------------------------------------------------

class _LanguageTinySerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'name', 'code')


class _ServiceTypeTinySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ('id', 'name')


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def _local_isoformat(dt, interpreter):
    """Convert a UTC datetime to the interpreter's local timezone ISO string."""
    if not dt:
        return None
    from app.utils.timezone import get_interpreter_timezone, BOSTON_TZ
    tz = get_interpreter_timezone(interpreter) if interpreter else BOSTON_TZ
    return dt.astimezone(tz).isoformat()


class AssignmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for table / list views."""

    interpreter_name = serializers.SerializerMethodField()
    interpreter_id = serializers.PrimaryKeyRelatedField(source='interpreter', read_only=True)
    client_display = serializers.SerializerMethodField()
    service_type_name = serializers.StringRelatedField(source='service_type')
    source_language_name = serializers.StringRelatedField(source='source_language')
    target_language_name = serializers.StringRelatedField(source='target_language')
    start_time_local = serializers.SerializerMethodField()
    end_time_local = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = (
            'id', 'status',
            'client_display', 'interpreter_name', 'interpreter_id',
            'service_type_name', 'source_language_name', 'target_language_name',
            'start_time', 'end_time',
            'start_time_local', 'end_time_local',
            'location', 'city', 'state', 'zip_code',
            'interpreter_rate', 'minimum_hours', 'total_interpreter_payment',
            'is_paid', 'created_at',
        )

    def get_interpreter_name(self, obj):
        if obj.interpreter and obj.interpreter.user:
            u = obj.interpreter.user
            return f"{u.first_name} {u.last_name}".strip()
        return None

    def get_client_display(self, obj):
        if obj.client:
            return obj.client.company_name or str(obj.client)
        return obj.client_name or 'N/A'

    def get_start_time_local(self, obj):
        return _local_isoformat(obj.start_time, obj.interpreter)

    def get_end_time_local(self, obj):
        return _local_isoformat(obj.end_time, obj.interpreter)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'interpreter__user', 'client',
            'service_type', 'source_language', 'target_language',
        )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class AssignmentDetailSerializer(serializers.ModelSerializer):
    """Full assignment representation with nested relations."""

    interpreter_name = serializers.SerializerMethodField()
    interpreter_id = serializers.PrimaryKeyRelatedField(source='interpreter', read_only=True)
    interpreter_detail = serializers.SerializerMethodField()
    client_detail = serializers.SerializerMethodField()
    service_type = _ServiceTypeTinySerializer(read_only=True)
    source_language = _LanguageTinySerializer(read_only=True)
    target_language = _LanguageTinySerializer(read_only=True)
    feedback = serializers.SerializerMethodField()
    interpreter_payment = serializers.SerializerMethodField()
    start_time_local = serializers.SerializerMethodField()
    end_time_local = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = (
            'id', 'status',
            'quote',
            'interpreter_id', 'interpreter_name', 'interpreter_detail',
            'client', 'client_detail',
            'client_name', 'client_email', 'client_phone',
            'service_type', 'source_language', 'target_language',
            'start_time', 'end_time',
            'start_time_local', 'end_time_local',
            'location', 'city', 'state', 'zip_code',
            'is_paid',
            'interpreter_rate', 'minimum_hours', 'total_interpreter_payment',
            'interpreter_payment',
            'notes', 'special_requirements',
            'created_at', 'updated_at', 'completed_at',
            'feedback',
        )

    def get_interpreter_name(self, obj):
        if obj.interpreter and obj.interpreter.user:
            u = obj.interpreter.user
            return f"{u.first_name} {u.last_name}".strip()
        return None

    def get_interpreter_detail(self, obj):
        """Full interpreter contact + profile info for the detail modal."""
        i = obj.interpreter
        if not i:
            return None
        u = i.user if hasattr(i, 'user') else None
        langs = []
        try:
            langs = [il.language.name for il in i.interpreterlanguage_set.select_related('language').all()]
        except Exception:
            pass
        return {
            'id': i.id,
            'first_name': u.first_name if u else '',
            'last_name': u.last_name if u else '',
            'email': u.email if u else '',
            'phone': u.phone if u else '',
            'city': i.city or '',
            'state': i.state or '',
            'address': i.address or '',
            'hourly_rate': str(i.hourly_rate) if i.hourly_rate else None,
            'radius_of_service': i.radius_of_service,
            'languages': langs,
            'is_manually_blocked': i.is_manually_blocked,
            'active': i.active,
        }

    def get_client_detail(self, obj):
        if not obj.client:
            return None
        return {
            'id': obj.client.id,
            'company_name': obj.client.company_name,
            'email': obj.client.email,
            'phone': obj.client.phone,
        }

    def get_interpreter_payment(self, obj):
        """Return the linked InterpreterPayment status if it exists."""
        try:
            from app.models import InterpreterPayment
            payment = InterpreterPayment.objects.filter(assignment=obj).order_by('-created_at').first()
            if payment:
                return {
                    'id': payment.id,
                    'status': payment.status,
                    'amount': str(payment.amount),
                    'reference_number': payment.reference_number,
                }
        except Exception:
            pass
        return None

    def get_feedback(self, obj):
        from app.models import AssignmentFeedback
        try:
            fb = obj.assignmentfeedback
            return {
                'rating': fb.rating,
                'comments': fb.comments,
                'created_at': fb.created_at.isoformat() if fb.created_at else None,
            }
        except AssignmentFeedback.DoesNotExist:
            return None

    def get_start_time_local(self, obj):
        return _local_isoformat(obj.start_time, obj.interpreter)

    def get_end_time_local(self, obj):
        return _local_isoformat(obj.end_time, obj.interpreter)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'interpreter__user', 'client',
            'service_type', 'source_language', 'target_language',
            'quote', 'assignmentfeedback',
        ).prefetch_related('interpreter__interpreterlanguage_set__language')


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class AssignmentCreateSerializer(serializers.ModelSerializer):
    """
    Create an assignment.
    - If ``client`` FK is provided, ``client_name``, ``client_email``, and
      ``client_phone`` are cleared automatically (mirrors model.save behaviour).
    - ``total_interpreter_payment`` is auto-calculated when not provided.
    """

    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False, allow_null=True
    )
    interpreter = serializers.PrimaryKeyRelatedField(
        queryset=Interpreter.objects.all(), required=False, allow_null=True
    )
    service_type = serializers.PrimaryKeyRelatedField(
        queryset=ServiceType.objects.all()
    )
    source_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all()
    )
    target_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all()
    )

    class Meta:
        model = Assignment
        fields = (
            'id',
            'quote', 'interpreter', 'client',
            'client_name', 'client_email', 'client_phone',
            'service_type', 'source_language', 'target_language',
            'start_time', 'end_time',
            'location', 'city', 'state', 'zip_code',
            'status',
            'interpreter_rate', 'minimum_hours', 'total_interpreter_payment',
            'notes', 'special_requirements',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        # If client FK is set, clear manual client fields
        if data.get('client'):
            data['client_name'] = None
            data['client_email'] = None
            data['client_phone'] = None

        # Auto-calculate total_interpreter_payment when not explicitly given
        if not data.get('total_interpreter_payment'):
            rate = data.get('interpreter_rate')
            start = data.get('start_time')
            end = data.get('end_time')
            minimum_hours = data.get('minimum_hours', 2)

            if rate and start and end:
                duration_seconds = (end - start).total_seconds()
                duration_hours = Decimal(str(duration_seconds / 3600))
                billable_hours = max(duration_hours, Decimal(str(minimum_hours)))
                data['total_interpreter_payment'] = rate * billable_hours

        return data


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class AssignmentUpdateSerializer(serializers.ModelSerializer):
    """Partial-update serializer for existing assignments."""

    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), required=False, allow_null=True
    )
    interpreter = serializers.PrimaryKeyRelatedField(
        queryset=Interpreter.objects.all(), required=False, allow_null=True
    )
    service_type = serializers.PrimaryKeyRelatedField(
        queryset=ServiceType.objects.all(), required=False
    )
    source_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), required=False
    )
    target_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), required=False
    )

    class Meta:
        model = Assignment
        fields = (
            'id',
            'interpreter', 'client',
            'client_name', 'client_email', 'client_phone',
            'service_type', 'source_language', 'target_language',
            'start_time', 'end_time',
            'location', 'city', 'state', 'zip_code',
            'status', 'is_paid',
            'interpreter_rate', 'minimum_hours', 'total_interpreter_payment',
            'notes', 'special_requirements',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        if data.get('client'):
            data['client_name'] = None
            data['client_email'] = None
            data['client_phone'] = None
        return data


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    'PENDING': '#FFA500',      # orange
    'CONFIRMED': '#3B82F6',    # blue
    'IN_PROGRESS': '#8B5CF6',  # purple
    'COMPLETED': '#10B981',    # green
    'CANCELLED': '#EF4444',    # red
    'NO_SHOW': '#6B7280',      # gray
}


class AssignmentCalendarSerializer(serializers.ModelSerializer):
    """FullCalendar-compatible event serializer."""

    title = serializers.SerializerMethodField()
    start = serializers.DateTimeField(source='start_time')
    end = serializers.DateTimeField(source='end_time')
    color = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ('id', 'title', 'start', 'end', 'status', 'color')

    def get_title(self, obj):
        client = obj.client.company_name if obj.client else (obj.client_name or 'N/A')
        src = obj.source_language.code if obj.source_language else '?'
        tgt = obj.target_language.code if obj.target_language else '?'
        return f"{client} ({src} > {tgt})"

    def get_color(self, obj):
        return STATUS_COLORS.get(obj.status, '#6B7280')

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'client', 'source_language', 'target_language',
        )


# ---------------------------------------------------------------------------
# Kanban
# ---------------------------------------------------------------------------

class AssignmentKanbanSerializer(serializers.Serializer):
    """
    Returns assignments grouped by status for a Kanban board.
    This is a non-model serializer; the view feeds the data.
    """

    PENDING = AssignmentListSerializer(many=True)
    CONFIRMED = AssignmentListSerializer(many=True)
    IN_PROGRESS = AssignmentListSerializer(many=True)
    COMPLETED = AssignmentListSerializer(many=True)
    CANCELLED = AssignmentListSerializer(many=True)
    NO_SHOW = AssignmentListSerializer(many=True)
