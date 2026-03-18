from django.contrib import admin
from app.models import Lead, Campaign


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_name', 'email', 'source', 'stage', 'estimated_monthly_value', 'assigned_to', 'created_at')
    list_filter = ('source', 'stage', 'assigned_to')
    search_fields = ('company_name', 'contact_name', 'email')
    list_editable = ('stage', 'assigned_to')
    readonly_fields = ('created_at', 'updated_at', 'converted_at')
    filter_horizontal = ('languages_needed',)
    raw_id_fields = ('converted_client', 'public_quote_request', 'contact_message', 'assigned_to')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel', 'status', 'budget', 'spent', 'leads_generated', 'conversions', 'start_date', 'end_date')
    list_filter = ('channel', 'status')
    search_fields = ('name',)
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('created_by',)
