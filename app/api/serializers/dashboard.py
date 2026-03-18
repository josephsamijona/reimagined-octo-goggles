from rest_framework import serializers

from app.models import Assignment


# ---------------------------------------------------------------------------
# Dashboard KPIs
# ---------------------------------------------------------------------------

class DashboardKPISerializer(serializers.Serializer):
    """Top-level KPI cards for the admin dashboard."""

    # Missions
    total_missions = serializers.IntegerField()
    missions_today = serializers.IntegerField()
    missions_this_week = serializers.IntegerField()
    missions_this_month = serializers.IntegerField()

    # Status breakdown
    pending_missions = serializers.IntegerField()
    confirmed_missions = serializers.IntegerField()
    in_progress_missions = serializers.IntegerField()
    completed_missions = serializers.IntegerField()
    cancelled_missions = serializers.IntegerField()

    # Financial
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_payments = serializers.DecimalField(max_digits=12, decimal_places=2)

    # People
    active_interpreters = serializers.IntegerField()
    active_clients = serializers.IntegerField()

    # Onboarding
    pending_onboarding = serializers.IntegerField()

    # Quotes
    pending_quotes = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertSerializer(serializers.Serializer):
    """System alert / action-required item for the dashboard."""

    id = serializers.CharField()
    level = serializers.ChoiceField(choices=['info', 'warning', 'error', 'success'])
    title = serializers.CharField()
    message = serializers.CharField()
    link = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Today's Missions
# ---------------------------------------------------------------------------

class TodayMissionSerializer(serializers.ModelSerializer):
    """Lightweight serializer for today's mission cards on the dashboard."""

    interpreter_name = serializers.SerializerMethodField()
    client_display = serializers.SerializerMethodField()
    service_type_name = serializers.StringRelatedField(source='service_type')
    source_language_name = serializers.StringRelatedField(source='source_language')
    target_language_name = serializers.StringRelatedField(source='target_language')

    class Meta:
        model = Assignment
        fields = (
            'id', 'status',
            'client_display', 'interpreter_name',
            'service_type_name',
            'source_language_name', 'target_language_name',
            'start_time', 'end_time',
            'city', 'state', 'location',
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

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'interpreter__user', 'client',
            'service_type', 'source_language', 'target_language',
        )
