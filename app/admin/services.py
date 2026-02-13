from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.contrib import messages
from django.core.exceptions import ValidationError
from decimal import Decimal
import re

from app import models
from .utils import USDateTimeField, format_boston_datetime, BOSTON_TZ
from app.mixins.assignment_mixins import AssignmentAdminMixin

class CustomAssignmentForm(forms.ModelForm):
    start_time = USDateTimeField()
    end_time = USDateTimeField()

    class Meta:
        model = models.Assignment
        fields = '__all__'
        # Spécifier explicitement ces champs comme non requis
        # (en supposant que d'autres champs obligatoires sont correctement configurés)
        required = {
            'client': False,
            'client_name': False,
            'client_email': False,
            'client_phone': False,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # S'assurer que les champs client ne sont pas obligatoires
        self.fields['client'].required = False
        self.fields['client_name'].required = False
        self.fields['client_email'].required = False
        self.fields['client_phone'].required = False

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        client_email = cleaned_data.get('client_email')
        client_phone = cleaned_data.get('client_phone')

        # Time validation
        if start_time and end_time:
            if end_time <= start_time:
                raise ValidationError({'end_time': 'End time must be after start time.'})
        
        # Only validate format of email and phone if they are provided
        if client_email and not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', client_email):
            self.add_error('client_email', 'Please enter a valid email address.')
        
        if client_phone and not re.match(r'^\+?[0-9\s\-\(\)]+$', client_phone):
            self.add_error('client_phone', 'Please enter a valid phone number.')

        return cleaned_data

class CustomQuoteRequestForm(forms.ModelForm):
    requested_date = USDateTimeField()

    class Meta:
        model = models.QuoteRequest
        fields = '__all__'

class CustomPublicQuoteRequestForm(forms.ModelForm):
    requested_date = USDateTimeField()

    class Meta:
        model = models.PublicQuoteRequest
        fields = '__all__'

@admin.register(models.ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_rate', 'minimum_hours', 'requires_certification', 'active')
    list_filter = ('active', 'requires_certification')
    search_fields = ('name', 'description')

@admin.register(models.QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    form = CustomQuoteRequestForm
    list_display = ('id', 'client', 'service_type', 'formatted_requested_date', 'status', 'created_at')
    list_filter = ('status', 'service_type', 'created_at')
    search_fields = ('client__company_name', 'location')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('client',)
    fieldsets = (
        ('Client Information', {'fields': ('client', 'service_type')}),
        ('Service Details', {'fields': ('requested_date', 'duration', ('source_language', 'target_language'))}),
        ('Location', {'fields': ('location', ('city', 'state', 'zip_code'))}),
        ('Additional Information', {'fields': ('special_requirements', 'status')}),
        ('System Information', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    def formatted_requested_date(self, obj):
        return format_boston_datetime(obj.requested_date)
    formatted_requested_date.short_description = "Requested Date (Boston)"
    def response_change(self, request, obj):
        if "_create-quote" in request.POST:
            messages.success(request, 'Quote successfully created.')
        return super().response_change(request, obj)

@admin.register(models.Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'get_client', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reference_number', 'quote_request__client__company_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('quote_request', 'created_by')
    fieldsets = (
        ('Quote Information', {'fields': ('quote_request', 'reference_number', 'status')}),
        ('Financial Details', {'fields': ('amount', 'tax_amount', 'valid_until')}),
        ('Additional Information', {'fields': ('terms', 'created_by')}),
    )
    def get_client(self, obj):
        return obj.quote_request.client.company_name
    get_client.short_description = 'Client'

@admin.register(models.Assignment)
class AssignmentAdmin(AssignmentAdminMixin, admin.ModelAdmin):
    form = CustomAssignmentForm
    list_display = (
        'id', 
        'get_client_display', 
        'get_interpreter', 
        'get_languages',
        'get_service_type',
        'formatted_start_time',
        'formatted_end_time',
        'get_status_display',
        'get_payment_status'
    )
    list_filter = (
        'status', 
        'service_type',
        'source_language',
        'target_language',
        'start_time',
        'is_paid'
    )
    search_fields = (
        'client__company_name', 
        'client_name', 
        'client_email',
        'interpreter__user__first_name', 
        'interpreter__user__last_name'
    )
    raw_id_fields = ('quote', 'interpreter', 'client')
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'completed_at', 
        'total_interpreter_payment',
        'formatted_start_time_detail',
        'formatted_end_time_detail'
    )

    fieldsets = (
        ('Assignment Information', {
            'fields': (
                ('quote', 'service_type'), 
                ('interpreter',),
                ('client',),  # Existing client
                ('client_name', 'client_email', 'client_phone')  # New client
            ),
            'description': 'You can either select an existing client or manually enter client information. All client fields are optional.'
        }),
        ('Language Details', {
            'fields': ('source_language', 'target_language')
        }),
        ('Schedule', {
            'fields': (
                ('start_time', 'formatted_start_time_detail'),
                ('end_time', 'formatted_end_time_detail')
            ),
            'description': 'All times are displayed in Boston (EDT/EST) timezone'
        }),
        ('Location', {
            'fields': ('location', ('city', 'state', 'zip_code'))
        }),
        ('Financial Information', {
            'fields': ('interpreter_rate', 'minimum_hours', 'total_interpreter_payment', 'is_paid'),
            'classes': ('collapse',),
            'description': 'Total amount is automatically calculated based on hourly rate and billable hours'
        }),
        ('Status and Notes', {
            'fields': ('status', 'notes', 'special_requirements'),
            'description': '''
                Status Information:
                • PENDING: When you first assign an interpreter, set status to PENDING (awaiting interpreter confirmation)
                • CONFIRMED: Interpreter has accepted the assignment
                • IN_PROGRESS: Assignment is currently being executed
                • COMPLETED: Assignment has been successfully completed
                • CANCELLED: Assignment was cancelled or rejected by interpreter
                • NO_SHOW: Client or interpreter did not show up
                
                Note: When creating a new assignment with an interpreter, you must set the status to PENDING.
            '''
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def get_languages(self, obj):
        """Display languages"""
        return f"{obj.source_language.name} → {obj.target_language.name}"
    get_languages.short_description = "Languages"
    get_languages.admin_order_field = 'source_language__name'

    def get_service_type(self, obj):
        """Display service type"""
        return obj.service_type.name
    get_service_type.short_description = "Service Type"
    get_service_type.admin_order_field = 'service_type__name'

    def get_status_display(self, obj):
        """Display status with color coding"""
        status_colors = {
            'PENDING': '#FFA500',      # Orange
            'CONFIRMED': '#4169E1',    # Royal Blue
            'IN_PROGRESS': '#32CD32',  # Lime Green
            'COMPLETED': '#008000',    # Green
            'CANCELLED': '#FF0000',    # Red
            'NO_SHOW': '#8B0000',      # Dark Red
        }
        
        status_icons = {
            'PENDING': '⏳',       # Hourglass
            'CONFIRMED': '✓',      # Check mark
            'IN_PROGRESS': '🔄',   # Rotating arrows
            'COMPLETED': '✅',      # Green check
            'CANCELLED': '❌',      # Red X
            'NO_SHOW': '⚠️',       # Warning
        }
        
        color = status_colors.get(obj.status, 'black')
        icon = status_icons.get(obj.status, '')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )
    get_status_display.short_description = 'Status'

    def get_payment_status(self, obj):
        """Display payment status with icon and color"""
        if obj.is_paid:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Paid</span>'
            )
        elif obj.is_paid is False:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Unpaid</span>'
            )
        return format_html(
            '<span style="color: gray;">- Pending</span>'
        )
    get_payment_status.short_description = 'Payment Status'

    def get_client_display(self, obj):
        """Display client information"""
        if obj.client:
            return obj.client.company_name
        if obj.client_name:
            return obj.client_name
        return "Unspecified Client"
    get_client_display.short_description = 'Client'

    def get_interpreter(self, obj):
        """Display interpreter information"""
        if obj.interpreter:
            return f"{obj.interpreter.user.first_name} {obj.interpreter.user.last_name}"
        return "-"
    get_interpreter.short_description = 'Interpreter'

    def formatted_start_time(self, obj):
        """Pour l'affichage en liste"""
        if obj.start_time:
            boston_time = obj.start_time.astimezone(BOSTON_TZ)
            return boston_time.strftime("%m/%d/%Y %I:%M %p")
        return "-"
    formatted_start_time.short_description = "Start Time (Boston)"

    def formatted_end_time(self, obj):
        """Pour l'affichage en liste"""
        if obj.end_time:
            boston_time = obj.end_time.astimezone(BOSTON_TZ)
            return boston_time.strftime("%m/%d/%Y %I:%M %p")
        return "-"
    formatted_end_time.short_description = "End Time (Boston)"

    def formatted_start_time_detail(self, obj):
        """Pour l'affichage en détail"""
        if obj.start_time:
            boston_time = obj.start_time.astimezone(BOSTON_TZ)
            return format_html(
                '<span style="color: #666;">{} EDT</span>',
                boston_time.strftime("%m/%d/%Y %I:%M %p")
            )
        return "-"
    formatted_start_time_detail.short_description = "Start Time (Boston)"

    def formatted_end_time_detail(self, obj):
        """Pour l'affichage en détail"""
        if obj.end_time:
            boston_time = obj.end_time.astimezone(BOSTON_TZ)
            return format_html(
                '<span style="color: #666;">{} EDT</span>',
                boston_time.strftime("%m/%d/%Y %I:%M %p")
            )
        return "-"
    formatted_end_time_detail.short_description = "End Time (Boston)"

    actions = ['mark_as_paid', 'mark_as_confirmed', 'mark_as_completed', 'mark_as_cancelled', 'mark_as_no_show']

    def mark_as_paid(self, request, queryset):
        rows_updated = queryset.update(is_paid=True)
        self.message_user(request, f"{rows_updated} assignment(s) successfully marked as paid.")
    mark_as_paid.short_description = "💰 Mark selected assignments as Paid"

    def mark_as_confirmed(self, request, queryset):
        rows_updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f"{rows_updated} assignment(s) successfully marked as confirmed.")
    mark_as_confirmed.short_description = "✅ Mark selected assignments as Confirmed"

    def mark_as_completed(self, request, queryset):
        rows_updated = queryset.update(status='COMPLETED')
        self.message_user(request, f"{rows_updated} assignment(s) successfully marked as completed.")
    mark_as_completed.short_description = "🏁 Mark selected assignments as Completed"

    def mark_as_cancelled(self, request, queryset):
        rows_updated = queryset.update(status='CANCELLED')
        self.message_user(request, f"{rows_updated} assignment(s) successfully marked as cancelled.")
    mark_as_cancelled.short_description = "❌ Mark selected assignments as Cancelled"

    def mark_as_no_show(self, request, queryset):
        rows_updated = queryset.update(status='NO_SHOW')
        self.message_user(request, f"{rows_updated} assignment(s) successfully marked as No Show")
    mark_as_no_show.short_description = "⚠️ Mark selected assignments as No Show"

    def save_model(self, request, obj, form, change):
        """
        Save model with total payment calculation and flexible client handling
        """
        if form.is_valid():
            # Calculate total payment
            if obj.interpreter_rate and obj.start_time and obj.end_time:
                duration = (obj.end_time - obj.start_time).total_seconds() / 3600
                billable_hours = max(duration, float(obj.minimum_hours))
                obj.total_interpreter_payment = obj.interpreter_rate * Decimal(str(billable_hours))
            
            # If an existing client is selected, clear the manual fields
            if obj.client:
                obj.client_name = None
                obj.client_email = None
                obj.client_phone = None
            
            # No need to set "Anonymous Client" or any default value
            # All client fields can remain empty

        super().save_model(request, obj, form, change)

@admin.register(models.PublicQuoteRequest)
class PublicQuoteRequestAdmin(admin.ModelAdmin):
    form = CustomPublicQuoteRequestForm  # Utilisation du formulaire personnalisé pour 'requested_date'
    list_display = (
        'full_name', 
        'company_name', 
        'get_languages', 
        'service_type', 
        'formatted_requested_date', 
        'created_at', 
        'processed'
    )
    list_filter = (
        'processed',
        'service_type',
        'source_language',
        'target_language',
        'state',
        'created_at'
    )
    search_fields = (
        'full_name',
        'email',
        'phone',
        'company_name',
        'location',
        'city'
    )
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Contact Information', {'fields': (('full_name', 'company_name'), ('email', 'phone')), 'classes': ('wide',)}),
        ('Service Details', {'fields': ('service_type', ('source_language', 'target_language'), ('requested_date', 'duration'))}),
        ('Location', {'fields': ('location', ('city', 'state', 'zip_code'))}),
        ('Additional Information', {'fields': ('special_requirements',)}),
        ('Processing Status', {'fields': ('processed', 'processed_by', 'processed_at', 'admin_notes'), 'classes': ('collapse',)}),
        ('System Information', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )
    def get_languages(self, obj):
        return f"{obj.source_language} → {obj.target_language}"
    get_languages.short_description = 'Languages'
    def formatted_requested_date(self, obj):
        return format_boston_datetime(obj.requested_date)
    formatted_requested_date.short_description = "Requested Date (Boston)"
    actions = ['mark_as_processed', 'export_as_csv']
    def mark_as_processed(self, request, queryset):
        queryset.update(
            processed=True,
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f"{queryset.count()} quote request(s) marked as processed.")
    mark_as_processed.short_description = "Mark selected requests as processed"
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=quote_requests_{datetime.now().strftime("%Y%m%d")}.csv'
        writer = csv.writer(response)
        writer.writerow(field_names)  # header
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                if hasattr(value, 'strftime'):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                row.append(str(value))
            writer.writerow(row)
        return response
    export_as_csv.short_description = "Export selected requests to CSV"
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.processed:
            return [f.name for f in self.model._meta.fields if f.name not in ['processed', 'processed_by', 'processed_at', 'admin_notes']]
        return self.readonly_fields
    def save_model(self, request, obj, form, change):
        if 'processed' in form.changed_data and obj.processed:
            obj.processed_by = request.user
            obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)
