from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from app import models
from .utils import mark_as_active, mark_as_inactive, reset_password

class InterpreterLanguageInline(admin.TabularInline):
    model = models.InterpreterLanguage
    extra = 1
    classes = ['collapse']
    fields = ('language', 'proficiency', 'is_primary', 'certified', 'certification_details')

@admin.register(models.User)
class CustomUserAdmin(UserAdmin):
    # AJOUT DES NOUVELLES COLONNES DEMANDÉES
    list_display = ('username', 'email', 'role', 'is_active', 'last_login', 'date_joined', 'registration_complete', 'contract_acceptance_date', 'is_dashboard_enabled')
    list_filter = ('role', 'is_active', 'groups', 'registration_complete', 'is_dashboard_enabled')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = [reset_password, mark_as_active, mark_as_inactive]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal Information'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (_('Role and Status'), {'fields': ('role', 'is_active', 'registration_complete', 'contract_acceptance_date', 'is_dashboard_enabled')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important Dates'), {'fields': ('last_login', 'date_joined')}),
    )
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields['role'].disabled = True
        return form

@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'get_full_name', 'city', 'state', 'active')
    list_filter = ('active', 'state', 'preferred_language')
    search_fields = ('company_name', 'user__username', 'user__email', 'phone', 'email', 
                     'user__first_name', 'user__last_name')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'active')
        }),
        ('Company Information', {
            'fields': ('company_name', 'address', 'city', 'state', 'zip_code', 'phone', 'email', 'tax_id')
        }),
        ('Billing Information', {
            'fields': ('billing_address', 'billing_city', 'billing_state', 'billing_zip_code', 'credit_limit')
        }),
        ('Preferences', {
            'fields': ('preferred_language', 'notes')
        }),
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
        'is_manually_blocked',  # Added
        'w9_on_file',
        'background_check_status',
        'hourly_rate'
    )
    list_filter = (
        'active',
        'is_manually_blocked',  # Added
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
        'zip_code',
        'blocked_reason'  # Added
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
    actions = [
        'activate_interpreters', 
        'deactivate_interpreters', 
        'send_contract_invitation',
        'block_interpreters',
        'unblock_interpreters',
        'send_reminder_level_1',
        'send_reminder_level_2',
        'send_reminder_level_3',
        'suspend_for_violation'
    ]
    
    def activate_interpreters(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} interpreter(s) have been successfully activated.')
    activate_interpreters.short_description = "Activate selected interpreters"
    
    def deactivate_interpreters(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} interpreter(s) have been successfully deactivated.')
    deactivate_interpreters.short_description = "Deactivate selected interpreters"
    
    def send_contract_invitation(self, request, queryset):
        """
        Admin action to send contract invitations to selected interpreters.
        Creates ContractInvitation and sends email.
        """
        from app.models import ContractInvitation, ContractTrackingEvent
        from app.services.email_service import ContractEmailService
        from django.contrib import messages
        from datetime import timedelta
        from django.utils import timezone
        
        sent_count = 0
        skipped_count = 0
        error_count = 0
        
        for interpreter in queryset:
            # Check if active invitation exists (SENT, OPENED, REVIEWING)
            active_invitation = ContractInvitation.objects.filter(
                interpreter=interpreter,
                status__in=['SENT', 'OPENED', 'REVIEWING']
            ).exists()
            
            if active_invitation:
                skipped_count += 1
                continue
            
            try:
                # Create invitation
                invitation = ContractInvitation.objects.create(
                    interpreter=interpreter,
                    created_by=request.user,
                    expires_at=timezone.now() + timedelta(days=30)
                    # tokens and invitation_number auto-generated by model save()
                )
                
                # Create tracking event
                ContractTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='EMAIL_SENT',
                    performed_by=request.user,
                    metadata={'source': 'admin_bulk_action'}
                )
                
                # Send email
                email_sent = ContractEmailService.send_invitation_email(invitation, request)
                
                if email_sent:
                    invitation.email_sent_at = timezone.now()
                    invitation.save(update_fields=['email_sent_at'])
                    sent_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send contract invitation to {interpreter}: {e}")
        
        # Build message
        msg_parts = []
        if sent_count:
            msg_parts.append(f"Contract invitation sent to {sent_count} interpreter(s).")
        if skipped_count:
            msg_parts.append(f"Skipped {skipped_count} (already have active invitations).")
        if error_count:
            msg_parts.append(f"Failed to send to {error_count} interpreter(s).")
        
        msg = " ".join(msg_parts)
        
        if error_count:
            self.message_user(request, msg, level=messages.ERROR)
        elif skipped_count:
            self.message_user(request, msg, level=messages.WARNING)
        else:
            self.message_user(request, msg, level=messages.SUCCESS)
    send_contract_invitation.short_description = "Send 2026 Contract Invitation"

    def block_interpreters(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            is_manually_blocked=True,
            blocked_at=timezone.now(),
            blocked_by=request.user,
            blocked_reason="Manual block via Admin"
        )
        self.message_user(request, f'{updated} interpreter(s) have been manually blocked.')
    block_interpreters.short_description = "Block selected interpreters (Manual)"

    def unblock_interpreters(self, request, queryset):
        updated = queryset.update(
            is_manually_blocked=False,
            blocked_at=None,
            blocked_by=None,
            blocked_reason=None
        )
        self.message_user(request, f'{updated} interpreter(s) have been unblocked.')
    unblock_interpreters.short_description = "Unblock selected interpreters"

    def send_reminder_level_1(self, request, queryset):
        self._send_bulk_reminder(request, queryset, 1)
    send_reminder_level_1.short_description = "Send Level 1 Reminder (Day 3)"

    def send_reminder_level_2(self, request, queryset):
        self._send_bulk_reminder(request, queryset, 2)
    send_reminder_level_2.short_description = "Send Level 2 Reminder (Day 7)"

    def send_reminder_level_3(self, request, queryset):
        self._send_bulk_reminder(request, queryset, 3)
    send_reminder_level_3.short_description = "Send Level 3 Reminder (Block)"

    def suspend_for_violation(self, request, queryset):
        from app.services.email_service import ContractViolationService
        from django.contrib import messages
        from django.utils import timezone
        
        count = 0
        for interpreter in queryset:
            if ContractViolationService.send_suspension_email(interpreter, "Administrative Decision", triggered_by=request.user):
                interpreter.is_manually_blocked = True
                interpreter.blocked_reason = "Administrative Suspension"
                interpreter.blocked_by = request.user
                interpreter.blocked_at = timezone.now()
                interpreter.save()
                count += 1
        
        self.message_user(request, f'Suspension email sent to {count} interpreter(s) and accounts blocked.', level=messages.SUCCESS)
    suspend_for_violation.short_description = "Suspend Account (Violation)"

    def _send_bulk_reminder(self, request, queryset, level):
        from app.services.email_service import ContractReminderService
        from app.models import ContractInvitation
        from django.contrib import messages

        sent_count = 0
        for interpreter in queryset:
            # Try to find active invitation
            invitation = ContractInvitation.objects.filter(
                interpreter=interpreter,
                status__in=['SENT', 'OPENED', 'REVIEWING']
            ).last()
            
            # Send using service
            method = getattr(ContractReminderService, f"send_level_{level}")
            if method(interpreter, invitation, triggered_by=request.user):
                sent_count += 1
        
        self.message_user(request, f'Level {level} reminder sent to {sent_count} interpreter(s).', level=messages.SUCCESS)

