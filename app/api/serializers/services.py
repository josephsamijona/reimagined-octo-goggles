from rest_framework import serializers

from app.models import (
    ServiceType, Language, QuoteRequest, Quote, PublicQuoteRequest,
    Client, User,
)


# ---------------------------------------------------------------------------
# ServiceType
# ---------------------------------------------------------------------------

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = (
            'id', 'name', 'description', 'base_rate',
            'minimum_hours', 'cancellation_policy',
            'requires_certification', 'active',
        )
        read_only_fields = ('id',)


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'name', 'code', 'is_active')
        read_only_fields = ('id',)


# ---------------------------------------------------------------------------
# QuoteRequest
# ---------------------------------------------------------------------------

class QuoteRequestListSerializer(serializers.ModelSerializer):
    """Lightweight QuoteRequest for list views."""

    client_name = serializers.SerializerMethodField()
    service_type_name = serializers.StringRelatedField(source='service_type')
    source_language_name = serializers.StringRelatedField(source='source_language')
    target_language_name = serializers.StringRelatedField(source='target_language')

    class Meta:
        model = QuoteRequest
        fields = (
            'id', 'client', 'client_name',
            'service_type_name', 'source_language_name', 'target_language_name',
            'requested_date', 'duration', 'city', 'state',
            'status', 'created_at',
        )

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or str(obj.client)
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'client', 'service_type', 'source_language', 'target_language',
        )


class QuoteRequestDetailSerializer(serializers.ModelSerializer):
    """Full detail QuoteRequest with nested quote info."""

    client_name = serializers.SerializerMethodField()
    service_type_name = serializers.StringRelatedField(source='service_type')
    source_language_name = serializers.StringRelatedField(source='source_language')
    target_language_name = serializers.StringRelatedField(source='target_language')
    quote = serializers.SerializerMethodField()

    class Meta:
        model = QuoteRequest
        fields = (
            'id', 'client', 'client_name',
            'service_type', 'service_type_name',
            'source_language', 'source_language_name',
            'target_language', 'target_language_name',
            'requested_date', 'duration',
            'location', 'city', 'state', 'zip_code',
            'special_requirements', 'status',
            'quote',
            'created_at', 'updated_at',
        )

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company_name or str(obj.client)
        return None

    def get_quote(self, obj):
        try:
            q = obj.quote
            return {
                'id': q.id,
                'reference_number': q.reference_number,
                'amount': str(q.amount) if q.amount else None,
                'status': q.status,
            }
        except Quote.DoesNotExist:
            return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'client', 'service_type', 'source_language', 'target_language',
        ).prefetch_related('quote')


class QuoteRequestCreateSerializer(serializers.ModelSerializer):
    """Create / update a QuoteRequest."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    service_type = serializers.PrimaryKeyRelatedField(queryset=ServiceType.objects.all())
    source_language = serializers.PrimaryKeyRelatedField(queryset=Language.objects.all())
    target_language = serializers.PrimaryKeyRelatedField(queryset=Language.objects.all())

    class Meta:
        model = QuoteRequest
        fields = (
            'id',
            'client', 'service_type',
            'requested_date', 'duration',
            'location', 'city', 'state', 'zip_code',
            'source_language', 'target_language',
            'special_requirements', 'status',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        src = data.get('source_language')
        tgt = data.get('target_language')
        if src and tgt and src == tgt:
            raise serializers.ValidationError(
                'Source and target languages must be different.'
            )
        return data


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

class QuoteSerializer(serializers.ModelSerializer):
    """Read serializer for Quote with nested quote request summary."""

    quote_request_summary = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = (
            'id', 'quote_request', 'quote_request_summary',
            'reference_number',
            'amount', 'tax_amount', 'valid_until', 'terms',
            'status',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        )

    def get_quote_request_summary(self, obj):
        qr = obj.quote_request
        if not qr:
            return None
        return {
            'id': qr.id,
            'client_id': qr.client_id,
            'service_type': str(qr.service_type),
            'requested_date': qr.requested_date.isoformat() if qr.requested_date else None,
            'status': qr.status,
        }

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'quote_request__client', 'quote_request__service_type',
            'created_by',
        )


# Aliases for viewsets that use separate list/detail naming
QuoteListSerializer = QuoteSerializer
QuoteDetailSerializer = QuoteSerializer


class QuoteCreateSerializer(serializers.ModelSerializer):
    """Create / update a Quote."""

    quote_request = serializers.PrimaryKeyRelatedField(
        queryset=QuoteRequest.objects.all()
    )
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    class Meta:
        model = Quote
        fields = (
            'id',
            'quote_request', 'reference_number',
            'amount', 'tax_amount', 'valid_until', 'terms',
            'status', 'created_by',
        )
        read_only_fields = ('id',)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


# ---------------------------------------------------------------------------
# PublicQuoteRequest
# ---------------------------------------------------------------------------

class PublicQuoteRequestSerializer(serializers.ModelSerializer):
    """Serializer for public (unauthenticated) quote requests."""

    source_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.filter(is_active=True)
    )
    target_language = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.filter(is_active=True)
    )
    service_type = serializers.PrimaryKeyRelatedField(
        queryset=ServiceType.objects.filter(active=True)
    )
    source_language_name = serializers.StringRelatedField(
        source='source_language', read_only=True
    )
    target_language_name = serializers.StringRelatedField(
        source='target_language', read_only=True
    )
    service_type_name = serializers.StringRelatedField(
        source='service_type', read_only=True
    )

    class Meta:
        model = PublicQuoteRequest
        fields = (
            'id',
            'full_name', 'email', 'phone', 'company_name',
            'source_language', 'source_language_name',
            'target_language', 'target_language_name',
            'service_type', 'service_type_name',
            'requested_date', 'duration',
            'location', 'city', 'state', 'zip_code',
            'special_requirements',
            'created_at', 'processed', 'processed_by',
            'processed_at', 'admin_notes',
        )
        read_only_fields = (
            'id', 'created_at', 'processed', 'processed_by',
            'processed_at', 'admin_notes',
        )

    def validate(self, data):
        src = data.get('source_language')
        tgt = data.get('target_language')
        if src and tgt and src == tgt:
            raise serializers.ValidationError(
                'Source and target languages must be different.'
            )
        return data


# Alias for viewsets that use list-specific naming
PublicQuoteRequestListSerializer = PublicQuoteRequestSerializer
