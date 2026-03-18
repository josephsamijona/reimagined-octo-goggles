from rest_framework import serializers
from django.db.models import Count, Avg, Sum, Max, Q

from app.models import (
    User, Client, Interpreter, InterpreterLocation,
    Language, InterpreterLanguage, Assignment, Invoice,
)


# ---------------------------------------------------------------------------
# Lightweight nested helpers
# ---------------------------------------------------------------------------

class _LanguageMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'name', 'code')


class _InterpreterLanguageSerializer(serializers.ModelSerializer):
    language = _LanguageMinimalSerializer(read_only=True)

    class Meta:
        model = InterpreterLanguage
        fields = ('id', 'language', 'proficiency', 'is_primary', 'certified')


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'is_active', 'registration_complete',
            'is_dashboard_enabled', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ClientListSerializer(serializers.ModelSerializer):
    """Lightweight client representation for list endpoints."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    preferred_language_name = serializers.StringRelatedField(
        source='preferred_language', read_only=True
    )
    mission_count = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    last_mission_date = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            'id', 'user_email', 'user_name', 'company_name',
            'city', 'state', 'phone', 'active',
            'preferred_language_name',
            'mission_count', 'total_revenue', 'last_mission_date',
        )

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_mission_count(self, obj):
        return Assignment.objects.filter(client=obj).count()

    def get_total_revenue(self, obj):
        result = Invoice.objects.filter(client=obj).aggregate(total=Sum('total_amount'))
        return result['total'] or 0

    def get_last_mission_date(self, obj):
        last = Assignment.objects.filter(client=obj).order_by('-start_time').values_list('start_time', flat=True).first()
        return last.isoformat() if last else None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('user', 'preferred_language')


class ClientDetailSerializer(serializers.ModelSerializer):
    """Full client representation with recent assignments and invoices."""

    user = UserSerializer(read_only=True)
    preferred_language = _LanguageMinimalSerializer(read_only=True)
    preferred_language_id = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(),
        source='preferred_language',
        write_only=True,
        required=False,
        allow_null=True,
    )
    recent_assignments = serializers.SerializerMethodField()
    recent_invoices = serializers.SerializerMethodField()
    mission_count = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    last_mission_date = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            'id', 'user',
            'company_name', 'address', 'city', 'state', 'zip_code',
            'phone', 'email',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip_code',
            'tax_id', 'preferred_language', 'preferred_language_id',
            'notes', 'credit_limit', 'active',
            'mission_count', 'total_revenue', 'last_mission_date',
            'recent_assignments', 'recent_invoices',
        )
        read_only_fields = ('id',)

    def get_recent_assignments(self, obj):
        from app.api.serializers.assignments import AssignmentListSerializer
        qs = Assignment.objects.filter(client=obj).order_by('-created_at')[:5]
        return AssignmentListSerializer(qs, many=True).data

    def get_recent_invoices(self, obj):
        from app.api.serializers.finance import InvoiceListSerializer
        qs = Invoice.objects.filter(client=obj).order_by('-created_at')[:5]
        return InvoiceListSerializer(qs, many=True).data

    def get_mission_count(self, obj):
        return Assignment.objects.filter(client=obj).count()

    def get_total_revenue(self, obj):
        result = Invoice.objects.filter(client=obj).aggregate(total=Sum('total_amount'))
        return result['total'] or 0

    def get_last_mission_date(self, obj):
        last = Assignment.objects.filter(client=obj).order_by('-start_time').values_list('start_time', flat=True).first()
        return last.isoformat() if last else None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('user', 'preferred_language')


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class InterpreterListSerializer(serializers.ModelSerializer):
    """Lightweight interpreter for list/table views."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    languages = serializers.SerializerMethodField()
    missions_count = serializers.IntegerField(read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    is_on_mission = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = Interpreter
        fields = (
            'id', 'user_email', 'first_name', 'last_name', 'phone',
            'city', 'state', 'hourly_rate', 'active',
            'has_accepted_contract', 'is_dashboard_enabled',
            'is_manually_blocked', 'languages',
            'missions_count', 'avg_rating',
            'is_on_mission', 'lat', 'lng',
        )

    def get_languages(self, obj):
        langs = obj.languages.all()[:5]
        return [{'id': l.id, 'name': l.name, 'code': l.code} for l in langs]

    def get_is_on_mission(self, obj):
        loc = obj.locations.first()
        return loc.is_on_mission if loc else False

    def get_lat(self, obj):
        loc = obj.locations.first()
        return float(loc.latitude) if loc else None

    def get_lng(self, obj):
        loc = obj.locations.first()
        return float(loc.longitude) if loc else None

    @staticmethod
    def setup_eager_loading(queryset):
        """Annotate computed fields and optimise relations."""
        return (
            queryset
            .select_related('user')
            .prefetch_related('languages', 'locations')
            .annotate(
                missions_count=Count(
                    'assignment',
                    filter=Q(assignment__status='COMPLETED'),
                ),
                avg_rating=Avg('assignment__assignmentfeedback__rating'),
            )
        )


class InterpreterDetailSerializer(serializers.ModelSerializer):
    """Full interpreter profile. Masks sensitive banking fields."""

    user = UserSerializer(read_only=True)
    interpreter_languages = _InterpreterLanguageSerializer(
        source='interpreterlanguage_set', many=True, read_only=True
    )
    missions_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    is_on_mission = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    # Masked banking fields
    routing_number = serializers.SerializerMethodField()
    account_number = serializers.SerializerMethodField()

    class Meta:
        model = Interpreter
        fields = (
            'id', 'user', 'interpreter_languages',
            'profile_image', 'bio',
            'address', 'city', 'state', 'zip_code',
            'certifications', 'specialties', 'availability',
            'radius_of_service', 'hourly_rate',
            'bank_name', 'account_holder_name',
            'routing_number', 'account_number', 'account_type',
            'background_check_date', 'background_check_status', 'w9_on_file',
            'active', 'date_of_birth', 'years_of_experience',
            'assignment_types', 'preferred_assignment_type',
            'cities_willing_to_cover',
            'contract_acceptance_date', 'has_accepted_contract',
            'is_dashboard_enabled',
            'is_manually_blocked', 'blocked_reason', 'blocked_at',
            'missions_count', 'avg_rating',
            'is_on_mission', 'lat', 'lng',
        )
        read_only_fields = ('id',)

    # -- Mask helpers --
    @staticmethod
    def _mask(value):
        """Show only last 4 characters, rest replaced with asterisks."""
        if not value:
            return None
        s = str(value)
        if len(s) <= 4:
            return s
        return '*' * (len(s) - 4) + s[-4:]

    def get_routing_number(self, obj):
        raw = obj.__class__.routing_number.field.value_from_object(obj) if obj.pk else None
        # Access the raw DB value, not the property
        try:
            raw = Interpreter.objects.filter(pk=obj.pk).values_list('routing_number', flat=True).first()
        except Exception:
            raw = None
        return self._mask(raw)

    def get_account_number(self, obj):
        try:
            raw = Interpreter.objects.filter(pk=obj.pk).values_list('account_number', flat=True).first()
        except Exception:
            raw = None
        return self._mask(raw)

    def get_missions_count(self, obj):
        return Assignment.objects.filter(
            interpreter=obj, status='COMPLETED'
        ).count()

    def get_avg_rating(self, obj):
        from app.models import AssignmentFeedback
        result = AssignmentFeedback.objects.filter(
            assignment__interpreter=obj
        ).aggregate(avg=Avg('rating'))
        return result['avg']

    def get_is_on_mission(self, obj):
        loc = obj.locations.first()
        return loc.is_on_mission if loc else False

    def get_lat(self, obj):
        loc = obj.locations.first()
        return float(loc.latitude) if loc else None

    def get_lng(self, obj):
        loc = obj.locations.first()
        return float(loc.longitude) if loc else None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('user', 'blocked_by').prefetch_related(
            'interpreterlanguage_set__language',
            'locations',
        )


# ---------------------------------------------------------------------------
# Interpreter Map & Location
# ---------------------------------------------------------------------------

class InterpreterMapSerializer(serializers.ModelSerializer):
    """Minimal interpreter data for map pin display."""

    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    languages = serializers.SerializerMethodField()
    latest_location = serializers.SerializerMethodField()

    class Meta:
        model = Interpreter
        fields = (
            'id', 'first_name', 'last_name',
            'city', 'state', 'active',
            'languages', 'latest_location',
        )

    def get_languages(self, obj):
        return list(obj.languages.values_list('name', flat=True)[:5])

    def get_latest_location(self, obj):
        loc = obj.locations.first()  # ordered by -timestamp
        if not loc:
            return None
        return {
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'is_on_mission': loc.is_on_mission,
            'timestamp': loc.timestamp.isoformat(),
        }

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('user').prefetch_related(
            'languages', 'locations'
        )


class InterpreterLocationSerializer(serializers.ModelSerializer):
    interpreter_id = serializers.PrimaryKeyRelatedField(
        queryset=Interpreter.objects.all(), source='interpreter'
    )

    class Meta:
        model = InterpreterLocation
        fields = (
            'id', 'interpreter_id',
            'latitude', 'longitude', 'accuracy',
            'is_on_mission', 'current_assignment',
            'timestamp',
        )
        read_only_fields = ('id', 'timestamp')


# ---------------------------------------------------------------------------
# Client Create / Update
# ---------------------------------------------------------------------------

class ClientCreateSerializer(serializers.ModelSerializer):
    """Create a client record (user must exist)."""

    preferred_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Client
        fields = (
            'id', 'user',
            'company_name', 'address', 'city', 'state', 'zip_code',
            'phone', 'email',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip_code',
            'tax_id', 'preferred_language',
            'notes', 'credit_limit', 'active',
        )
        read_only_fields = ('id',)


class ClientUpdateSerializer(serializers.ModelSerializer):
    """Update a client record."""

    preferred_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Client
        fields = (
            'id',
            'company_name', 'address', 'city', 'state', 'zip_code',
            'phone', 'email',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip_code',
            'tax_id', 'preferred_language',
            'notes', 'credit_limit', 'active',
        )
        read_only_fields = ('id',)


# ---------------------------------------------------------------------------
# Interpreter Update
# ---------------------------------------------------------------------------

class InterpreterUpdateSerializer(serializers.ModelSerializer):
    """Update interpreter profile fields."""

    class Meta:
        model = Interpreter
        fields = (
            'id',
            'address', 'city', 'state', 'zip_code',
            'bio', 'certifications', 'specialties', 'availability',
            'radius_of_service', 'hourly_rate',
            'years_of_experience', 'assignment_types',
            'preferred_assignment_type', 'cities_willing_to_cover',
            'active',
        )
        read_only_fields = ('id',)
