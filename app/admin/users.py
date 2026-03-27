from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from app import models
from .utils import mark_as_active, mark_as_inactive, reset_password

class InterpreterLanguageInline(admin.TabularInline):
    model = models.InterpreterLanguage
    extra = 1
    classes = ['collapse']
    fields = ('language', 'proficiency', 'is_primary', 'certified', 'certification_details')


class ContractBankingInline(admin.TabularInline):
    model = models.InterpreterContractSignature
    fk_name = 'interpreter'
    extra = 0
    max_num = 0
    can_delete = False
    verbose_name = 'Contract Banking Info'
    verbose_name_plural = 'Contract Banking Info (encrypted)'
    classes = ['collapse']
    fields = (
        'status', 'signed_at', 'bank_name', 'account_holder_name',
        'account_type', 'account_number_reveal', 'routing_number_reveal', 'swift_code_reveal',
    )
    readonly_fields = (
        'status', 'signed_at', 'bank_name', 'account_holder_name',
        'account_type', 'account_number_reveal', 'routing_number_reveal', 'swift_code_reveal',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def _is_unlocked(self):
        request = getattr(self, '_current_request', None)
        return request and request.session.get('admin_reauth_verified')

    def _make_reveal(self, masked, clear, field_id):
        if self._is_unlocked():
            return mark_safe(
                f'<span id="masked-{field_id}">{masked}</span>'
                f'<span id="clear-{field_id}" style="display:none;">{clear}</span> '
                f'<a href="#" style="font-size:11px;" onclick="'
                f"var m=document.getElementById('masked-{field_id}'),"
                f"c=document.getElementById('clear-{field_id}'),"
                f"t=this;"
                f"if(c.style.display==='none'){{c.style.display='inline';m.style.display='none';t.textContent='Masquer';}}"
                f"else{{c.style.display='none';m.style.display='inline';t.textContent='Voir';}}"
                f"return false;"
                f'">Voir</a>'
            )
        else:
            request = getattr(self, '_current_request', None)
            path = request.path if request else ''
            reauth_url = f"/admin/mfa/reauth/?next={path}"
            return mark_safe(f'{masked} <a href="{reauth_url}" style="font-size:11px; color:#417690;">Unlock to view</a>')

    def get_formset(self, request, obj=None, **kwargs):
        self._current_request = request
        return super().get_formset(request, obj, **kwargs)

    def account_number_reveal(self, obj):
        val = obj.get_account_number()
        if not val:
            return '—'
        masked = '*' * (len(val) - 4) + val[-4:]
        return self._make_reveal(masked, val, f'inl-acct-{obj.pk}')
    account_number_reveal.short_description = 'Account #'

    def routing_number_reveal(self, obj):
        val = obj.get_routing_number()
        if not val:
            return '—'
        masked = val[:2] + '*' * (len(val) - 4) + val[-2:]
        return self._make_reveal(masked, val, f'inl-rout-{obj.pk}')
    routing_number_reveal.short_description = 'Routing #'

    def swift_code_reveal(self, obj):
        val = obj.get_swift_code()
        if not val:
            return '—'
        masked = val[:4] + '*' * (len(val) - 4)
        return self._make_reveal(masked, val, f'inl-swift-{obj.pk}')
    swift_code_reveal.short_description = 'SWIFT'

class InterpreterInline(admin.StackedInline):
    model = models.Interpreter
    can_delete = False
    verbose_name_plural = 'Interpreter Profile'
    fk_name = 'user'
    extra = 0
    fieldsets = (
        ('Profile Information', {'fields': ('profile_photo_preview', 'profile_image', 'bio')}),
        ('Contact Information', {'fields': ('address', ('city', 'state', 'zip_code'), 'radius_of_service')}),
    )
    readonly_fields = ('profile_photo_preview',)

    def profile_photo_preview(self, obj):
        if obj.profile_image:
            import re
            url = obj.profile_image
            # Extraction du chemin relatif si c'est une URL signée S3/B2
            if url.startswith('http'):
                # Regex pour capturer le chemin après le nom du bucket/domaine et avant les paramètres query
                match = re.search(r'https?://[^/]+/(?:media/)?([^?]+)', url)
                if match:
                    url = match.group(1)
            
            # Si on a un chemin relatif (ou extrait), on génère une URL non signée
            if not url.startswith('http'):
                from custom_storages import PublicMediaStorage
                try:
                    storage = PublicMediaStorage()
                    # On s'assure de ne pas doubler 'media/' si déjà présent dans custom_storages
                    path = url
                    if path.startswith('media/'):
                        path = path.replace('media/', '', 1)
                    url = storage.url(path)
                except Exception:
                    pass
            return mark_safe(f'<img src="{url}" width="150" style="border-radius: 10px; border: 1px solid #ccc;" />')
        return "No photo"
    profile_photo_preview.short_description = 'Photo Preview'

@admin.register(models.User)
class CustomUserAdmin(UserAdmin):
    # AJOUT DES NOUVELLES COLONNES DEMANDÉES
    list_display = ('username', 'email', 'role', 'is_active', 'last_login', 'date_joined', 'registration_complete', 'contract_acceptance_date', 'is_dashboard_enabled')
    list_filter = ('role', 'is_active', 'groups', 'registration_complete', 'is_dashboard_enabled')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    actions = [reset_password, mark_as_active, mark_as_inactive]
    inlines = [] # Will be populated in get_inlines

    def get_inlines(self, request, obj=None):
        inlines = super().get_inlines(request, obj)
        if obj and obj.role == models.User.Roles.INTERPRETER:
            return inlines + [InterpreterInline]
        return inlines
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

    def user_change_password(self, request, id, form_url=''):
        """Gate password change behind MFA reauth."""
        if not request.session.get('admin_reauth_verified'):
            reauth_url = reverse('admin_mfa:reauth')
            next_url = request.get_full_path()
            return redirect(f"{reauth_url}?next={next_url}")
        return super().user_change_password(request, id, form_url)

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
        'address',
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
        'address',
        'city',
        'state',
        'zip_code',
        'blocked_reason'  # Added
    )
    inlines = [InterpreterLanguageInline, ContractBankingInline]
    fieldsets = (
        ('Status', {'fields': (('user', 'active'),)}),
        ('Profile Information', {'fields': (('profile_photo_preview', 'profile_image'), 'bio')}),
        ('Personal Information', {'fields': ('date_of_birth', 'years_of_experience'),
                                  'classes': ('collapse',)}),
        ('Contact Information', {'fields': ('address', ('city', 'state', 'zip_code'), 'radius_of_service')}),
        ('Professional Information', {'fields': ('hourly_rate', 'certifications', 'specialties', 'availability')}),
        ('Assignment Preferences', {'fields': ('assignment_types', 'preferred_assignment_type', 'cities_willing_to_cover'),
                                    'classes': ('collapse',)}),
        ('Compliance', {'fields': (('background_check_date', 'background_check_status'), 'w9_on_file'),
                        'classes': ('collapse',)}),
        ('Banking Information (ACH)', {'fields': ('bank_name', 'account_holder_name', 'routing_number_display', 'account_number_display', 'account_type'),
                                         'classes': ('collapse',),
                                         'description': 'Banking data is encrypted. Click "Voir" to reveal, "Masquer" to hide.'}),
        ('Contract Invitation', {'fields': ('contract_invite_token', 'contract_invite_expires_at', 'signature_ip'),
                                 'classes': ('collapse',)}),
    )
    readonly_fields = ('profile_photo_preview',)

    def profile_photo_preview(self, obj):
        if obj.profile_image:
            import re
            url = obj.profile_image
            # Extraction du chemin relatif si c'est une URL signée S3/B2
            if url.startswith('http'):
                # Regex pour capturer le chemin après le nom du bucket/domaine et avant les paramètres query
                match = re.search(r'https?://[^/]+/(?:media/)?([^?]+)', url)
                if match:
                    url = match.group(1)
            
            # Si on a un chemin relatif (ou extrait), on génère une URL non signée
            if not url.startswith('http'):
                from custom_storages import PublicMediaStorage
                try:
                    storage = PublicMediaStorage()
                    # On s'assure de ne pas doubler 'media/' si déjà présent dans custom_storages
                    path = url
                    if path.startswith('media/'):
                        path = path.replace('media/', '', 1)
                    url = storage.url(path)
                except Exception:
                    pass
            return mark_safe(f'<img src="{url}" width="150" style="border-radius: 10px; border: 1px solid #ccc;" />')
        return "No photo"
    profile_photo_preview.short_description = 'Photo Preview'
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
    def _make_banking_reveal(self, masked, clear, field_id, request):
        """Show masked value. If reauth verified, allow toggle. Otherwise link to reauth."""
        is_unlocked = request and request.session.get('admin_reauth_verified')
        if is_unlocked:
            return mark_safe(
                f'<span id="masked-{field_id}">{masked}</span>'
                f'<span id="clear-{field_id}" style="display:none;">{clear}</span> '
                f'<a href="#" style="font-size:11px;" onclick="'
                f"var m=document.getElementById('masked-{field_id}'),"
                f"c=document.getElementById('clear-{field_id}'),"
                f"t=this;"
                f"if(c.style.display==='none'){{c.style.display='inline';m.style.display='none';t.textContent='Masquer';}}"
                f"else{{c.style.display='none';m.style.display='inline';t.textContent='Voir';}}"
                f"return false;"
                f'">Voir</a>'
            )
        else:
            reauth_url = f"/admin/mfa/reauth/?next={request.path}" if request else "#"
            return mark_safe(
                f'{masked} '
                f'<a href="{reauth_url}" style="font-size:11px; color:#417690;">Unlock to view</a>'
            )

    def _decrypt_field(self, raw_value):
        if not raw_value:
            return None
        try:
            from app.models.documents import InterpreterContractSignature
            return InterpreterContractSignature.decrypt_data(raw_value.encode() if isinstance(raw_value, str) else raw_value)
        except Exception:
            return None

    def routing_number_display(self, obj):
        clear = self._decrypt_field(obj.routing_number)
        if not clear:
            return '—'
        masked = clear[:2] + '*' * (len(clear) - 4) + clear[-2:]
        request = getattr(self, '_current_request', None)
        return self._make_banking_reveal(masked, clear, f'interp-rout-{obj.pk}', request)
    routing_number_display.short_description = 'Routing Number'

    def account_number_display(self, obj):
        clear = self._decrypt_field(obj.account_number)
        if not clear:
            return '—'
        masked = '*' * (len(clear) - 4) + clear[-4:]
        request = getattr(self, '_current_request', None)
        return self._make_banking_reveal(masked, clear, f'interp-acct-{obj.pk}', request)
    account_number_display.short_description = 'Account Number'

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        self._current_request = request
        return super().changeform_view(request, object_id, form_url, extra_context)

    def get_readonly_fields(self, request, obj=None):
        readonly = ('profile_photo_preview', 'routing_number_display', 'account_number_display')
        if obj:
            return readonly + ('user',)
        return readonly
    def save_model(self, request, obj, form, change):
        if not change:
            obj.active = True
        super().save_model(request, obj, form, change)
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            for field in ['hourly_rate']:
                if field in form.base_fields:
                    form.base_fields[field].disabled = True
        return form
    actions = [
        'activate_interpreters',
        'deactivate_interpreters',
        'send_contract_invitation',
        'send_onboarding_invitation',
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

    def send_onboarding_invitation(self, request, queryset):
        """Send onboarding invitations to selected interpreters (existing accounts)."""
        from app.models import OnboardingInvitation, OnboardingTrackingEvent
        from app.services.email_service import OnboardingEmailService
        from django.utils import timezone

        sent_count = 0
        skipped_count = 0
        error_count = 0

        for interpreter in queryset:
            # Check for active onboarding invitation
            active = OnboardingInvitation.objects.filter(
                interpreter=interpreter,
                current_phase__in=['INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED', 'ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED']
            ).exists()

            if active:
                skipped_count += 1
                continue

            try:
                invitation = OnboardingInvitation.objects.create(
                    email=interpreter.user.email,
                    first_name=interpreter.user.first_name,
                    last_name=interpreter.user.last_name,
                    phone=getattr(interpreter.user, 'phone', ''),
                    user=interpreter.user,
                    interpreter=interpreter,
                    created_by=request.user,
                    email_sent_at=timezone.now(),
                )

                OnboardingTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='EMAIL_SENT',
                    performed_by=request.user,
                    metadata={'source': 'admin_interpreter_action'}
                )

                if OnboardingEmailService.send_invitation_email(invitation, request):
                    sent_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                import logging
                logging.getLogger(__name__).error(f"Failed to send onboarding invitation to {interpreter}: {e}")

        msg_parts = []
        if sent_count:
            msg_parts.append(f"Onboarding invitation sent to {sent_count} interpreter(s).")
        if skipped_count:
            msg_parts.append(f"Skipped {skipped_count} (already have active invitations).")
        if error_count:
            msg_parts.append(f"Failed for {error_count} interpreter(s).")

        msg = " ".join(msg_parts)
        if error_count:
            self.message_user(request, msg, level=messages.ERROR)
        elif skipped_count:
            self.message_user(request, msg, level=messages.WARNING)
        else:
            self.message_user(request, msg, level=messages.SUCCESS)
    send_onboarding_invitation.short_description = "Send Onboarding Invitation"

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

