from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
import pytz
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django import forms
from django.core.mail import send_mail
from datetime import datetime
from django.utils.html import mark_safe
from .utils.datetime_handlers import DateTimeHandler
from .mixins.assignment_mixins import AssignmentAdminMixin
from . import models
from django.core.exceptions import ValidationError
# =======================================================
# 1. UTILITAIRES POUR LE FUSEAU HORAIRE
# =======================================================
# On force ici l'heure du Massachusetts (America/New_York)
BOSTON_TZ = pytz.timezone('America/New_York')

def format_boston_datetime(dt):
    """
    Convertit une datetime (stockée en UTC) en heure locale de Boston
    et la formate au format US : MM/DD/YYYY HH:MM AM/PM TZ.
    Exemple : "03/25/2025 02:30 PM EDT"
    """
    if not dt:
        return ""
    local_dt = timezone.localtime(dt, BOSTON_TZ)
    return local_dt.strftime("%m/%d/%Y %I:%M %p %Z")

# =======================================================
# 2. WIDGET PERSONNALISÉ POUR LA SAISIE DE DATE/HEURE AVEC FLATPICKR
# =======================================================
class USDateTimePickerWidget(forms.MultiWidget):
    """
    Widget combinant deux champs de saisie (un pour la date et un pour l'heure)
    avec Flatpickr pour offrir un date picker et un time picker.
    """
    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(attrs={'class': 'us-date-picker', 'placeholder': 'MM/DD/YYYY'}),
            forms.TextInput(attrs={'class': 'us-time-picker', 'placeholder': 'hh:mm AM/PM'}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        """
        Décompose une datetime en date et heure
        Convertit de UTC vers Boston pour l'affichage dans le formulaire
        """
        if value:
            # Convertir de UTC vers Boston pour l'affichage
            boston_time = value.astimezone(BOSTON_TZ)
            return [
                boston_time.strftime('%m/%d/%Y'),
                boston_time.strftime('%I:%M %p')
            ]
        return [None, None]

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = [None, None]
        elif not isinstance(value, list):
            value = self.decompress(value)
        rendered = super().render(name, value, attrs, renderer)
        
        js = """
        <script type="text/javascript">
        (function($) {
            $(document).ready(function(){
                $('.us-date-picker').flatpickr({
                    dateFormat: "m/d/Y",
                    allowInput: true
                });
                $('.us-time-picker').flatpickr({
                    enableTime: true,
                    noCalendar: true,
                    dateFormat: "h:i K",
                    time_24hr: false,
                    allowInput: true
                });
            });
        })(django.jQuery);
        </script>
        """
        return mark_safe(rendered + js)

    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',)
        }
        js = ('https://cdn.jsdelivr.net/npm/flatpickr',)

# =======================================================
# 2.1. CHAMP PERSONNALISÉ : USDateTimeField
# =======================================================
class USDateTimeField(forms.MultiValueField):
    widget = USDateTimePickerWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.DateField(input_formats=['%m/%d/%Y']),
            forms.TimeField(input_formats=['%I:%M %p']),
        )
        super().__init__(fields, require_all_fields=True, *args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
            
        if data_list[0] is None or data_list[1] is None:
            raise ValidationError("Enter a valid date and time.")

        try:
            # 1. Créer la datetime naïve
            naive_dt = datetime.combine(data_list[0], data_list[1])
            
            # 2. La localiser explicitement dans le fuseau Boston
            boston_dt = BOSTON_TZ.localize(naive_dt)
            
            # 3. La convertir en UTC pour le stockage
            utc_dt = boston_dt.astimezone(pytz.UTC)
            
            return utc_dt
            
        except (AttributeError, ValueError) as e:
            raise ValidationError("Enter a valid date and time.")
# =======================================================
# 3. FORMULAIRES PERSONNALISÉS POUR LES CHAMPS DATETIME
# =======================================================
class CustomAssignmentForm(forms.ModelForm):
    start_time = USDateTimeField()
    end_time = USDateTimeField()

    class Meta:
        model = models.Assignment
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise ValidationError({'end_time': 'End time must be after start time.'})

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

# =======================================================
# 4. ACTIONS PERSONNALISÉES
# =======================================================
def mark_as_active(modeladmin, request, queryset):
    queryset.update(active=True)
mark_as_active.short_description = "Mark as active"

def mark_as_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
mark_as_inactive.short_description = "Mark as inactive"

def reset_password(modeladmin, request, queryset):
    for user in queryset:
        # Implémenter ici la logique de réinitialisation de mot de passe
        pass
reset_password.short_description = "Reset password"

# =======================================================
# 5. INLINES
# =======================================================
class InterpreterLanguageInline(admin.TabularInline):
    model = models.InterpreterLanguage
    extra = 1
    classes = ['collapse']
    fields = ('language', 'proficiency', 'is_primary', 'certified', 'certification_details')

class AssignmentInline(admin.TabularInline):
    model = models.Assignment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    classes = ['collapse']

# =======================================================
# 6. ADMINISTRATION DES MODÈLES
# =======================================================
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
        if not request.user.is_superuser:
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
        ('Basic Information', {'fields': (('user', 'active'), 'company_name', 'preferred_language')}),
        ('Primary Address', {'fields': ('address', ('city', 'state', 'zip_code'))}),
        ('Billing Information', {'fields': ('billing_address', ('billing_city', 'billing_state', 'billing_zip_code'),
                                              'tax_id', 'credit_limit'), 'classes': ('collapse',)}),
        ('Additional Information', {'fields': ('notes',), 'classes': ('collapse',)}),
    )
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Full Name'

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
        ('Status', {'fields': (('user', 'active'),)}),
        ('Profile Information', {'fields': ('profile_image', 'bio')}),
        ('Contact Information', {'fields': ('address', ('city', 'state', 'zip_code'), 'radius_of_service')}),
        ('Professional Information', {'fields': ('hourly_rate', 'certifications', 'specialties', 'availability')}),
        ('Compliance', {'fields': (('background_check_date', 'background_check_status'), 'w9_on_file'),
                        'classes': ('collapse',)}),
        ('Banking Information (ACH)', {'fields': ('bank_name', 'account_holder_name', 'routing_number', 'account_number', 'account_type'),
                                         'classes': ('collapse',),
                                         'description': 'Secure banking information for ACH payments.'}),
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
            language_list.append(f"{lang.language.name} ({lang.get_proficiency_display()}){cert_icon}{primary_icon}")
        return mark_safe("<br>".join(language_list))
    get_languages.short_description = 'Languages'
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('user',)
        return ()
    def save_model(self, request, obj, form, change):
        if not change:
            obj.active = True
        super().save_model(request, obj, form, change)
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            for field in ['routing_number', 'account_number', 'hourly_rate']:
                if field in form.base_fields:
                    form.base_fields[field].disabled = True
        return form
    actions = ['activate_interpreters', 'deactivate_interpreters']
    def activate_interpreters(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} interpreter(s) have been successfully activated.')
    activate_interpreters.short_description = "Activate selected interpreters"
    def deactivate_interpreters(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} interpreter(s) have been successfully deactivated.')
    deactivate_interpreters.short_description = "Deactivate selected interpreters"

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
        'get_status_display'
    )
    list_filter = (
        'status', 
        'service_type',
        'source_language',
        'target_language',
        'start_time'
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
            'description': 'If the client is not registered in the system, please enter their information manually using the fields below (name, email, phone)'
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
            'fields': ('interpreter_rate', 'minimum_hours', 'total_interpreter_payment'),
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

    def get_client_display(self, obj):
        """Display client information"""
        if obj.client:
            return obj.client.company_name
        return f"{obj.client_name} (Manual)"
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

    def save_model(self, request, obj, form, change):
        """
        Sauvegarde du modèle avec calcul du paiement total
        """
        if form.is_valid():
            if obj.interpreter_rate and obj.start_time and obj.end_time:
                duration = (obj.end_time - obj.start_time).total_seconds() / 3600
                billable_hours = max(duration, float(obj.minimum_hours))
                obj.total_interpreter_payment = obj.interpreter_rate * Decimal(str(billable_hours))

        super().save_model(request, obj, form, change)
@admin.register(models.Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'payment_type', 'amount', 'status', 'formatted_payment_date')
    list_filter = ('status', 'payment_type', 'payment_date')
    search_fields = ('transaction_id', 'assignment__client__company_name')
    readonly_fields = ('payment_date', 'last_updated')
    fieldsets = (
        ('Payment Information', {'fields': ('payment_type', 'amount', 'payment_method')}),
        ('Related Records', {'fields': ('quote', 'assignment')}),
        ('Transaction Details', {'fields': ('transaction_id', 'status', 'notes')}),
        ('System Information', {'fields': ('payment_date', 'last_updated'), 'classes': ('collapse',)}),
    )
    def formatted_payment_date(self, obj):
        return format_boston_datetime(obj.payment_date)
    formatted_payment_date.short_description = "Payment Date (Boston)"

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

# =======================================================
# 7. CONFIGURATION DU SITE ADMIN
# =======================================================
admin.site.site_header = "JHBRIDGE Administration"
admin.site.site_title = "JHBRIDGE Admin Portal"
admin.site.index_title = "Welcome to JHBRIDGE Administration"
