from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html, mark_safe
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
import pytz
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django import forms
from django.core.mail import send_mail
from datetime import datetime

from . import models

# =======================================================
# 1. UTILITAIRES POUR LE FUSEAU HORAIRE
# =======================================================
# On force ici l'heure du Massachusetts (America/New_York)
TZ_BOSTON = pytz.timezone('America/New_York')

def format_boston_datetime(dt):
    """
    Convertit une datetime (stockée en UTC) en heure locale de Boston
    et la formate au format US : MM/DD/YYYY HH:MM AM/PM TZ.
    Exemple : "03/25/2025 02:30 PM EDT"
    """
    if not dt:
        return ""
    local_dt = timezone.localtime(dt, TZ_BOSTON)
    return local_dt.strftime("%m/%d/%Y %I:%M %p %Z")

# =======================================================
# 2. WIDGET PERSONNALISÉ POUR LA SAISIE DE DATE/HEURE AVEC FLATPICKR
# =======================================================
class USDateTimePickerWidget(forms.MultiWidget):
    """
    Widget combinant deux champs de saisie (un pour la date et un pour l'heure)
    avec Flatpickr pour offrir un date picker et un time picker.
    Les formats utilisés sont au standard US :
       - Date : MM/DD/YYYY
       - Heure : 12h avec AM/PM
    Ce widget permet une saisie intuitive et limite les erreurs humaines.
    """
    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(attrs={'class': 'us-date-picker', 'placeholder': 'MM/DD/YYYY'}),
            forms.TextInput(attrs={'class': 'us-time-picker', 'placeholder': 'hh:mm AM/PM'}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.strftime('%m/%d/%Y'), value.strftime('%I:%M %p')]
        return [None, None]

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = [None, None]
        elif not isinstance(value, list):
            value = self.decompress(value)
        rendered = super().render(name, value, attrs, renderer)
        # Ajout d'un script inline pour initialiser Flatpickr sur les champs
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
    """
    Champ personnalisé combinant un DateField et un TimeField.
    Il utilise le widget USDateTimePickerWidget défini ci-dessus.
    Le champ compresse la saisie (une liste de [date, time])
    en un objet datetime aware localisé en heure du Massachusetts.
    """
    widget = USDateTimePickerWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.DateField(input_formats=['%m/%d/%Y']),
            forms.TimeField(input_formats=['%I:%M %p']),
        )
        super().__init__(fields, require_all_fields=True, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            if not data_list[0] or not data_list[1]:
                raise forms.ValidationError("Enter a valid date and time.")
            dt = datetime.combine(data_list[0], data_list[1])
            return TZ_BOSTON.localize(dt)
        return None

# =======================================================
# 3. FORMULAIRES PERSONNALISÉS POUR LES CHAMPS DATETIME
# =======================================================
class CustomAssignmentForm(forms.ModelForm):
    # Remplacement des champs start_time et end_time par le champ personnalisé
    start_time = USDateTimeField()
    end_time = USDateTimeField()

    class Meta:
        model = models.Assignment
        fields = '__all__'

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
class AssignmentAdmin(admin.ModelAdmin):
    form = CustomAssignmentForm
    list_display = ('id', 'get_client', 'get_interpreter', 'formatted_start_time', 'status')
    list_filter = ('status', 'service_type', 'start_time')
    search_fields = ('client__company_name', 'interpreter__user__first_name', 'interpreter__user__last_name')
    raw_id_fields = ('quote', 'interpreter', 'client')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('Assignment Information', {'fields': (('quote', 'service_type'), ('interpreter', 'client'))}),
        ('Language Details', {'fields': ('source_language', 'target_language')}),
        ('Schedule', {'fields': ('start_time', 'end_time')}),
        ('Location', {'fields': ('location', ('city', 'state', 'zip_code'))}),
        ('Financial Information', {'fields': ('interpreter_rate', 'minimum_hours', 'total_interpreter_payment'),
                                     'classes': ('collapse',)}),
        ('Status and Notes', {'fields': ('status', 'notes', 'special_requirements')}),
        ('System Information', {'fields': ('created_at', 'updated_at', 'completed_at'),
                                  'classes': ('collapse',)}),
    )
    def get_client(self, obj):
        return obj.client.company_name
    get_client.short_description = 'Client'
    def get_interpreter(self, obj):
        if obj.interpreter:
            return f"{obj.interpreter.user.first_name} {obj.interpreter.user.last_name}"
        return "-"
    get_interpreter.short_description = 'Interpreter'
    def formatted_start_time(self, obj):
        return format_boston_datetime(obj.start_time)
    formatted_start_time.short_description = "Start Time (Boston)"
    def save_model(self, request, obj, form, change):
        print("\n" + "="*50)
        print("SAVE MODEL PROCESS STARTED")
        print("="*50)
        print(f"Operation type: {'Modification' if change else 'New Creation'}")
        print(f"Form changed fields: {form.changed_data}")
        print(f"Current Assignment ID: {obj.pk}")
        print(f"Current Status: {obj.status}")
       
        try:
            print("\nCHECKING INTERPRETER")
            if obj.interpreter:
                print(f"Interpreter assigned: {obj.interpreter.user.get_full_name()}")
                print(f"Interpreter email: {obj.interpreter.user.email}")
            else:
                print("No interpreter assigned")
           
            should_send = False
           
            if not change:  # New creation
                print("\nNEW APPOINTMENT CREATION")
                should_send = (obj.status == models.Assignment.Status.PENDING and obj.interpreter is not None)
                print(f"Should send email (new): {should_send}")
                if should_send:
                    print("Reason: New appointment with PENDING status and interpreter assigned")
                else:
                    print("Reason for not sending:")
                    if obj.status != models.Assignment.Status.PENDING:
                        print(f"- Status is not PENDING (current: {obj.status})")
                    if not obj.interpreter:
                        print("- No interpreter assigned")
           
            else:  # Modification
                print("\nAPPOINTMENT MODIFICATION")
                old_obj = self.model.objects.get(pk=obj.pk)
                print(f"Old status: {old_obj.status}")
                print(f"New status: {obj.status}")
               
                should_send = (old_obj.status != obj.status and 
                               obj.status == models.Assignment.Status.PENDING and 
                               obj.interpreter is not None)
                print(f"Should send email (modification): {should_send}")
                if should_send:
                    print("Reason: Status changed to PENDING with interpreter assigned")
                else:
                    print("Reason for not sending:")
                    if old_obj.status == obj.status:
                        print("- Status not changed")
                    if obj.status != models.Assignment.Status.PENDING:
                        print(f"- New status is not PENDING (current: {obj.status})")
                    if not obj.interpreter:
                        print("- No interpreter assigned")
           
            if should_send:
                print("\nPREPARING EMAIL")
                try:
                    context = {
                        'interpreter_name': f"{obj.interpreter.user.first_name} {obj.interpreter.user.last_name}",
                        'assignment_id': obj.id,
                        'start_time': format_boston_datetime(obj.start_time),
                        'end_time': format_boston_datetime(obj.end_time),
                        'location': obj.location,
                        'city': obj.city,
                        'state': obj.state,
                        'client_name': obj.client.company_name,
                        'service_type': obj.service_type.name,
                        'source_language': obj.source_language.name,
                        'target_language': obj.target_language.name,
                        'interpreter_rate': obj.interpreter_rate,
                        'special_requirements': obj.special_requirements or "No special requirements"
                    }
                    print("Email context prepared successfully")
                   
                    print("\nEMAIL SETTINGS")
                    print(f"From email: {settings.DEFAULT_FROM_EMAIL}")
                    print(f"Email backend: {settings.EMAIL_BACKEND}")
                   
                    print("\nRENDERING EMAIL TEMPLATE")
                    html_message = render_to_string(
                        'emails/new_assignment_notification.html',
                        context,
                        request=request
                    )
                    print("Template rendered successfully")
                   
                    print("\nSENDING EMAIL")
                    print(f"To: {obj.interpreter.user.email}")
                    send_mail(
                        subject=_('New Appointment to Confirm - Action Required'),
                        message=strip_tags(html_message),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[obj.interpreter.user.email],
                        html_message=html_message,
                        fail_silently=False
                    )
                    print("EMAIL SENT SUCCESSFULLY ✓")
                   
                except Exception as email_error:
                    print("\nEMAIL ERROR")
                    print(f"Error type: {type(email_error)}")
                    print(f"Error message: {str(email_error)}")
                    if hasattr(email_error, '__dict__'):
                        print(f"Error details: {email_error.__dict__}")
                   
        except Exception as e:
            print("\nGENERAL ERROR")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            if hasattr(e, '__dict__'):
                print(f"Error details: {e.__dict__}")
       
        print("\nSAVING MODEL")
        super().save_model(request, obj, form, change)
        print("Model saved successfully")
        print("="*50 + "\n")

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
