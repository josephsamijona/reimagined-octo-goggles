from rest_framework import serializers

from app.models import (
    Lead, Campaign, Language, Client, User,
    PublicQuoteRequest, ContactMessage,
)


# ---------------------------------------------------------------------------
# Lightweight helpers
# ---------------------------------------------------------------------------

class _LanguageTinySerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'name', 'code')


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------

class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight lead for table / pipeline views."""

    assigned_to_name = serializers.SerializerMethodField()
    languages_needed = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = (
            'id', 'company_name', 'contact_name', 'email', 'phone',
            'source', 'stage',
            'languages_needed', 'estimated_monthly_value',
            'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at',
        )

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None

    def get_languages_needed(self, obj):
        return list(obj.languages_needed.values_list('name', flat=True))

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('assigned_to').prefetch_related('languages_needed')


class LeadDetailSerializer(serializers.ModelSerializer):
    """Full lead with linked entities."""

    assigned_to_name = serializers.SerializerMethodField()
    languages_needed = _LanguageTinySerializer(many=True, read_only=True)
    converted_client_name = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = (
            'id', 'company_name', 'contact_name', 'email', 'phone',
            'source', 'stage',
            'languages_needed', 'estimated_monthly_value',
            'notes',
            'converted_client', 'converted_client_name', 'converted_at',
            'public_quote_request', 'contact_message',
            'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at',
        )

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
        return None

    def get_converted_client_name(self, obj):
        if obj.converted_client:
            return obj.converted_client.company_name or str(obj.converted_client)
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'assigned_to', 'converted_client',
            'public_quote_request', 'contact_message',
        ).prefetch_related('languages_needed')


class LeadCreateSerializer(serializers.ModelSerializer):
    """Create / update a lead."""

    languages_needed = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), many=True, required=False
    )
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    public_quote_request = serializers.PrimaryKeyRelatedField(
        queryset=PublicQuoteRequest.objects.all(), required=False, allow_null=True
    )
    contact_message = serializers.PrimaryKeyRelatedField(
        queryset=ContactMessage.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Lead
        fields = (
            'id', 'company_name', 'contact_name', 'email', 'phone',
            'source', 'stage',
            'languages_needed', 'estimated_monthly_value',
            'notes',
            'public_quote_request', 'contact_message',
            'assigned_to',
        )
        read_only_fields = ('id',)


class LeadUpdateSerializer(serializers.ModelSerializer):
    """Update fields on an existing lead."""

    languages_needed = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), many=True, required=False
    )
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Lead
        fields = (
            'id', 'company_name', 'contact_name', 'email', 'phone',
            'source', 'stage',
            'languages_needed', 'estimated_monthly_value',
            'notes', 'assigned_to',
        )
        read_only_fields = ('id',)


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

class CampaignListSerializer(serializers.ModelSerializer):
    """Lightweight campaign for table views."""
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            'id', 'name', 'channel', 'status',
            'budget', 'spent',
            'leads_generated', 'conversions',
            'start_date', 'end_date',
            'created_by', 'created_by_name',
            'created_at',
        )

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('created_by')


class CampaignSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    roi = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            'id', 'name', 'channel', 'status',
            'budget', 'spent',
            'leads_generated', 'conversions',
            'start_date', 'end_date',
            'notes',
            'created_by', 'created_by_name',
            'roi',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_roi(self, obj):
        """Return ROI percentage. None if no spend."""
        if not obj.spent or obj.spent == 0:
            return None
        # ROI = (conversions value estimate - spent) / spent * 100
        # Since we do not have conversion value, return cost-per-lead instead.
        return None

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('created_by')


# ---------------------------------------------------------------------------
# Market Analytics (non-model serializer)
# ---------------------------------------------------------------------------

class MarketAnalyticsSerializer(serializers.Serializer):
    """Aggregated marketing analytics for the dashboard."""

    total_leads = serializers.IntegerField()
    leads_by_source = serializers.DictField(child=serializers.IntegerField())
    leads_by_stage = serializers.DictField(child=serializers.IntegerField())
    conversion_rate = serializers.FloatField()
    avg_lead_value = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    active_campaigns = serializers.IntegerField()
    total_campaign_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    period_start = serializers.DateField()
    period_end = serializers.DateField()


# Aliases used by viewsets that need separate list/detail/create/update
CampaignDetailSerializer = CampaignSerializer


class CampaignCreateSerializer(serializers.ModelSerializer):
    """Create a campaign."""

    class Meta:
        model = Campaign
        fields = (
            'id', 'name', 'channel', 'status',
            'budget', 'spent',
            'leads_generated', 'conversions',
            'start_date', 'end_date',
            'notes',
        )
        read_only_fields = ('id',)


class CampaignUpdateSerializer(serializers.ModelSerializer):
    """Update a campaign."""

    class Meta:
        model = Campaign
        fields = (
            'id', 'name', 'channel', 'status',
            'budget', 'spent',
            'leads_generated', 'conversions',
            'start_date', 'end_date',
            'notes',
        )
        read_only_fields = ('id',)
