from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from . import models

# Custom actions
def mark_as_active(modeladmin, request, queryset):
    queryset.update(active=True)
mark_as_active.short_description = "Mark as active"

def mark_as_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
mark_as_inactive.short_description = "Mark as inactive"

def reset_password(modeladmin, request, queryset):
    for user in queryset:
        # Password reset logic
        pass
reset_password.short_description = "Reset password"

# Inline Models
class InterpreterLanguageInline(admin.TabularInline):
    model = models.InterpreterLanguage
    extra = 1
    classes = ['collapse']

class AssignmentInline(admin.TabularInline):
    model = models.Assignment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    classes = ['collapse']

@admin.register(models.User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'last_login', 'date_joined', 'registration_complete')
    list_filter = ('role', 'is_active', 'groups', 'registration_complete')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = [reset_password, mark_as_active, mark_as_inactive]

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal Information'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (_('Role and Status'), {'fields': ('role', 'is_active', 'registration_complete')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important Dates'), {'fields': ('last_login', 'date_joined')}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser
        if not is_superuser:
            form.base_fields['role'].disabled = True
        return form

@admin.register(models.Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)
    actions = [mark_as_active, mark_as_inactive]

@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'company_name', 'city', 'state', 'active')
    list_filter = ('active', 'state', 'preferred_language')
    search_fields = ('company_name', 'user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    readonly_fields = ('credit_limit',)

    fieldsets = (
        ('Basic Information', {
            'fields': (('user', 'active'), 'company_name', 'preferred_language')
        }),
        ('Primary Address', {
            'fields': ('address', ('city', 'state', 'zip_code'))
        }),
        ('Billing Information', {
            'fields': ('billing_address', ('billing_city', 'billing_state', 'billing_zip_code'),
                      'tax_id', 'credit_limit'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Full Name'

class InterpreterLanguageInline(admin.TabularInline):
    model = models.InterpreterLanguage
    extra = 1
    classes = ['collapse']
    fields = ('language', 'proficiency', 'is_primary', 'certified', 'certification_details')

@admin.register(models.Interpreter)
class InterpreterAdmin(admin.ModelAdmin):
    list_display = (
        'get_full_name',
        'get_languages',
        'city', 
        'state',
        'active',
        'w9_on_file',
        'background_check_status',
        'hourly_rate'
    )
    list_filter = (
        'active',
        'state',
        'w9_on_file',
        'background_check_status',
        'languages'
    )
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'city',
        'state',
        'zip_code'
    )
    inlines = [InterpreterLanguageInline]

    fieldsets = (
        ('Status', {
            'fields': (
                ('user', 'active'),
            )
        }),
        ('Contact Information', {
            'fields': (
                'address',
                ('city', 'state', 'zip_code'),
                'radius_of_service'
            )
        }),
        ('Professional Information', {
            'fields': (
                'hourly_rate',
                'certifications',
                'specialties',
                'availability'
            )
        }),
        ('Compliance', {
            'fields': (
                ('background_check_date', 'background_check_status'),
                'w9_on_file'
            ),
            'classes': ('collapse',)
        }),
        ('Banking Information (ACH)', {
            'fields': (
                'bank_name',
                'account_holder_name',
                'routing_number',
                'account_number',
                'account_type'
            ),
            'classes': ('collapse',),
            'description': 'Secure banking information for ACH payments.'
        })
    )

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Interpreter Name'
    get_full_name.admin_order_field = 'user__last_name'

    def get_languages(self, obj):
        languages = obj.interpreterlanguage_set.all()
        language_list = []
        for lang in languages:
            cert_icon = '✓' if lang.certified else ''
            primary_icon = '★' if lang.is_primary else ''
            language_list.append(
                f"{lang.language.name} ({lang.get_proficiency_display()})"
                f"{cert_icon}{primary_icon}"
            )
        return mark_safe("<br>".join(language_list))
    get_languages.short_description = 'Languages'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('user',)
        return ()

    def save_model(self, request, obj, form, change):
        if not change:  # If this is a new interpreter
            obj.active = True
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            restricted_fields = [
                'routing_number', 
                'account_number',
                'hourly_rate'
            ]
            for field in restricted_fields:
                if field in form.base_fields:
                    form.base_fields[field].disabled = True
        return form

    actions = ['activate_interpreters', 'deactivate_interpreters']

    def activate_interpreters(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(
            request,
            f'{updated} interpreter(s) have been successfully activated.'
        )
    activate_interpreters.short_description = "Activate selected interpreters"

    def deactivate_interpreters(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(
            request,
            f'{updated} interpreter(s) have been successfully deactivated.'
        )
    deactivate_interpreters.short_description = "Deactivate selected interpreters"

@admin.register(models.ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_rate', 'minimum_hours', 'requires_certification', 'active')
    list_filter = ('active', 'requires_certification')
    search_fields = ('name', 'description')

@admin.register(models.QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'service_type', 'requested_date', 'status', 'created_at')
    list_filter = ('status', 'service_type', 'created_at')
    search_fields = ('client__company_name', 'location')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('client',)

    fieldsets = (
        ('Client Information', {
            'fields': ('client', 'service_type')
        }),
        ('Service Details', {
            'fields': ('requested_date', 'duration', ('source_language', 'target_language'))
        }),
        ('Location', {
            'fields': ('location', ('city', 'state', 'zip_code'))
        }),
        ('Additional Information', {
            'fields': ('special_requirements', 'status')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

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
        ('Quote Information', {
            'fields': ('quote_request', 'reference_number', 'status')
        }),
        ('Financial Details', {
            'fields': ('amount', 'tax_amount', 'valid_until')
        }),
        ('Additional Information', {
            'fields': ('terms', 'created_by')
        })
    )

    def get_client(self, obj):
        return obj.quote_request.client.company_name
    get_client.short_description = 'Client'

@admin.register(models.Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_client', 'get_interpreter', 'start_time', 'status')
    list_filter = ('status', 'service_type', 'start_time')
    search_fields = ('client__company_name', 'interpreter__user__first_name', 'interpreter__user__last_name')
    raw_id_fields = ('quote', 'interpreter', 'client')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')

    fieldsets = (
        ('Assignment Information', {
            'fields': (('quote', 'service_type'), ('interpreter', 'client'))
        }),
        ('Language Details', {
            'fields': ('source_language', 'target_language')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time')
        }),
        ('Location', {
            'fields': ('location', ('city', 'state', 'zip_code'))
        }),
        ('Financial Information', {
            'fields': ('interpreter_rate', 'minimum_hours', 'total_interpreter_payment'),
            'classes': ('collapse',)
        }),
        ('Status and Notes', {
            'fields': ('status', 'notes', 'special_requirements')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )

    def get_client(self, obj):
        return obj.client.company_name
    get_client.short_description = 'Client'

    def get_interpreter(self, obj):
        return f"{obj.interpreter.user.first_name} {obj.interpreter.user.last_name}"
    get_interpreter.short_description = 'Interpreter'

@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'payment_type', 'amount', 'status', 'payment_date')
    list_filter = ('status', 'payment_type', 'payment_date')
    search_fields = ('transaction_id', 'assignment__client__company_name')
    readonly_fields = ('payment_date', 'last_updated')

    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_type', 'amount', 'payment_method')
        }),
        ('Related Records', {
            'fields': ('quote', 'assignment')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'status', 'notes')
        }),
        ('System Information', {
            'fields': ('payment_date', 'last_updated'),
            'classes': ('collapse',)
        })
    )

@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'type', 'title', 'read', 'created_at')
    list_filter = ('type', 'read', 'created_at')
    search_fields = ('recipient__email', 'title', 'content')
    readonly_fields = ('created_at',)

@admin.register(models.ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'created_at', 'processed')
    list_filter = ('processed', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)

    def mark_as_processed(self, request, queryset):
        queryset.update(
            processed=True,
            processed_by=request.user,
            processed_at=timezone.now()
        )
    mark_as_processed.short_description = "Mark as processed"

    actions = [mark_as_processed]

@admin.register(models.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__email', 'action', 'changes')
    readonly_fields = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'changes', 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

 
@admin.register(models.PublicQuoteRequest)
class PublicQuoteRequestAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 
        'company_name', 
        'get_languages', 
        'service_type', 
        'requested_date', 
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
        ('Contact Information', {
            'fields': (
                ('full_name', 'company_name'),
                ('email', 'phone')
            ),
            'classes': ('wide',)
        }),
        ('Service Details', {
            'fields': (
                'service_type',
                ('source_language', 'target_language'),
                ('requested_date', 'duration')
            )
        }),
        ('Location', {
            'fields': (
                'location',
                ('city', 'state', 'zip_code')
            )
        }),
        ('Additional Information', {
            'fields': ('special_requirements',)
        }),
        ('Processing Status', {
            'fields': (
                'processed',
                'processed_by',
                'processed_at',
                'admin_notes'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def get_languages(self, obj):
        return f"{obj.source_language} → {obj.target_language}"
    get_languages.short_description = 'Languages'

    actions = ['mark_as_processed', 'export_as_csv']

    def mark_as_processed(self, request, queryset):
        queryset.update(
            processed=True,
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(
            request,
            f"{queryset.count()} quote request(s) marked as processed."
        )
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

        # Write header
        writer.writerow(field_names)
        
        # Write data
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                row.append(str(value))
            writer.writerow(row)

        return response
    export_as_csv.short_description = "Export selected requests to CSV"

    def get_readonly_fields(self, request, obj=None):
        # Make most fields readonly if the request has been processed
        if obj and obj.processed:
            return [f.name for f in self.model._meta.fields if f.name not in [
                'processed', 'processed_by', 'processed_at', 'admin_notes'
            ]]
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if 'processed' in form.changed_data and obj.processed:
            obj.processed_by = request.user
            obj.processed_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    
    
    
    

# Admin site configuration
admin.site.site_header = "JHBRIDGE Administration"
admin.site.site_title = "JHBRIDGE Admin Portal"
admin.site.index_title = "Welcome to JHBRIDGE Administration"