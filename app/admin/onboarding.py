import logging
import json
from django.contrib import admin
from django.utils.html import mark_safe
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from app.models import OnboardingInvitation, OnboardingTrackingEvent
import app.services.onboarding_service as onboarding_svc

logger = logging.getLogger(__name__)

class OnboardingTrackingEventInline(admin.TabularInline):
    model = OnboardingTrackingEvent
    extra = 0
    readonly_fields = ('event_type', 'timestamp', 'performed_by', 'metadata_display')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def metadata_display(self, obj):
        return mark_safe(f"<pre>{json.dumps(obj.metadata, indent=2)}</pre>")
    metadata_display.short_description = "Metadata"


@admin.register(OnboardingInvitation)
class OnboardingInvitationAdmin(admin.ModelAdmin):
    list_display = (
        'invitation_number',
        'full_name_display',
        'email',
        'phase_badge',
        'version',
        'created_at',
        'created_by_display',
    )
    list_filter = ('current_phase', 'created_at')
    search_fields = ('invitation_number', 'email', 'first_name', 'last_name')
    readonly_fields = (
        'invitation_number',
        'token',
        'created_by',
        'version',
        'created_at',
        'email_sent_at',
        'email_opened_at',
        'welcome_viewed_at',
        'account_created_at',
        'profile_completed_at',
        'contract_started_at',
        'completed_at',
        'voided_at',
        'expires_at',
        'tracking_timeline',
    )
    inlines = [OnboardingTrackingEventInline]

    fieldsets = (
        ('Invitation Details', {
            'fields': ('invitation_number', 'first_name', 'last_name', 'email', 'phone', 'current_phase')
        }),
        ('System Info', {
            'fields': ('created_by', 'version'),
            'classes': ('collapse',)
        }),
        ('Linked Records', {
            'fields': ('user', 'interpreter', 'contract_invitation'),
            'classes': ('collapse',)
        }),
        ('Token', {
            'fields': ('token',),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('tracking_timeline',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'email_sent_at', 'email_opened_at',
                'welcome_viewed_at', 'account_created_at', 'profile_completed_at',
                'contract_started_at', 'completed_at', 'voided_at', 'expires_at'
            ),
            'classes': ('collapse',)
        }),
        ('Void Info', {
            'fields': ('voided_by', 'void_reason'),
            'classes': ('collapse',),
        }),
    )

    actions = [
        'void_invitations', 
        'resend_invitations',
        'resend_issue_email',
        'resend_stuck_welcome_email',
        'resend_stuck_account_email',
        'resend_stuck_contract_email',
        'resend_stuck_opened_email',
    ]

    def save_model(self, request, obj, form, change):
        """Auto-send invitation email on creation via the admin form."""
        if change:
            super().save_model(request, obj, form, change)
            return

        # New invitation: delegate entirely to the service (creates + links + emails)
        try:
            invitation = onboarding_svc.create_invitation(
                first_name=obj.first_name,
                last_name=obj.last_name,
                email=obj.email,
                phone=obj.phone or '',
                created_by=request.user,
                request=request,
            )
            # Copy auto-generated fields back so Django admin shows the saved object
            obj.pk = invitation.pk
            obj.token = invitation.token
            obj.invitation_number = invitation.invitation_number
            obj.email_sent_at = invitation.email_sent_at
            obj.created_by = invitation.created_by
            messages.success(request, f"Invitation email successfully sent to {obj.email}.")
        except Exception as e:
            logger.error("Automatic email failed in save_model: %s", e, exc_info=True)
            # Still save the object so the invitation isn't lost
            super().save_model(request, obj, form, change)
            messages.error(request, f"Automatic email error: {e}")

    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = 'Name'
    full_name_display.admin_order_field = 'last_name'

    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return '-'
    created_by_display.short_description = 'Sent By'

    def phase_badge(self, obj):
        colors = {
            'INVITED': '#2196F3',
            'EMAIL_OPENED': '#00BCD4',
            'WELCOME_VIEWED': '#9C27B0',
            'ACCOUNT_CREATED': '#FF9800',
            'PROFILE_COMPLETED': '#8BC34A',
            'CONTRACT_STARTED': '#FFC107',
            'COMPLETED': '#4CAF50',
            'VOIDED': '#F44336',
            'EXPIRED': '#9E9E9E',
        }
        color = colors.get(obj.current_phase, '#9E9E9E')
        label = obj.get_current_phase_display()
        return mark_safe(
            f'<span style="background:{color};color:white;padding:4px 8px;border-radius:4px;'
            f'font-weight:bold;font-size:11px;">{label}</span>'
        )
    phase_badge.short_description = 'Phase'

    def tracking_timeline(self, obj):
        events = obj.tracking_events.all().order_by('-timestamp')
        if not events:
            return "No events recorded."

        icons = {
            'EMAIL_SENT': '✉️',
            'EMAIL_OPENED': '👁️',
            'LINK_CLICKED': '🖱️',
            'WELCOME_COMPLETED': '👋',
            'ACCOUNT_CREATED': '👤',
            'PROFILE_SAVED': '📋',
            'CONTRACT_STARTED': '📝',
            'CONTRACT_SIGNED': '✍️',
            'ONBOARDING_COMPLETED': '🎉',
            'VOIDED': '🚫',
            'RESENT': '🔄',
        }

        html = '<div style="max-height:300px;overflow-y:auto;padding:10px;border:1px solid #ccc;background:#fff;">'
        for event in events:
            icon = icons.get(event.event_type, '•')
            html += f'<div style="margin-bottom:10px;padding:8px;border-left:3px solid #2196F3;background:#f9f9f9;">'
            html += f'<div style="font-weight:bold;">{icon} {event.get_event_type_display()}</div>'
            html += f'<div style="font-size:0.9em;color:#555">{event.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</div>'
            if event.performed_by:
                html += f'<div style="font-size:0.8em;color:#777">by {event.performed_by.get_full_name()}</div>'
            html += '</div>'
        html += '</div>'
        return mark_safe(html)
    tracking_timeline.short_description = 'Event Timeline'

    @admin.action(description="Void selected invitations")
    def void_invitations(self, request, queryset):
        count = 0
        for inv in queryset:
            if inv.current_phase not in ('VOIDED', 'EXPIRED', 'COMPLETED'):
                try:
                    onboarding_svc.void_invitation(inv, voided_by=request.user, reason='Voided by admin bulk action')
                    count += 1
                except ValueError:
                    pass
        self.message_user(request, f"{count} invitation(s) voided.", level=messages.SUCCESS)

    @admin.action(description="Resend invitations (Standard)")
    def resend_invitations(self, request, queryset):
        count = self._resend_with_template(request, queryset, None)
        self.message_user(request, f"{count} invitation(s) resent.", level=messages.SUCCESS)

    def _resend_with_template(self, request, queryset, template_type):
        """Void old invitation and create a new one — delegates to onboarding_service."""
        count = 0
        for old_inv in queryset:
            if old_inv.current_phase not in ('VOIDED', 'EXPIRED'):
                onboarding_svc.resend_invitation(
                    old_inv,
                    created_by=request.user,
                    template_type=template_type,
                    request=request,
                )
                count += 1
        return count

    @admin.action(description="Resend: Help/Issue")
    def resend_issue_email(self, request, queryset):
        count = self._resend_with_template(request, queryset, 'RESEND_ISSUE')
        self.message_user(request, f"{count} issue help email(s) sent.", level=messages.SUCCESS)

    @admin.action(description="Resend: Stuck in Welcome")
    def resend_stuck_welcome_email(self, request, queryset):
        count = self._resend_with_template(request, queryset, 'STUCK_WELCOME')
        self.message_user(request, f"{count} welcome nudge email(s) sent.", level=messages.SUCCESS)

    @admin.action(description="Resend: Stuck in Account")
    def resend_stuck_account_email(self, request, queryset):
        count = self._resend_with_template(request, queryset, 'STUCK_ACCOUNT')
        self.message_user(request, f"{count} account nudge email(s) sent.", level=messages.SUCCESS)

    @admin.action(description="Resend: Stuck in Contract")
    def resend_stuck_contract_email(self, request, queryset):
        count = self._resend_with_template(request, queryset, 'STUCK_CONTRACT')
        self.message_user(request, f"{count} contract nudge email(s) sent.", level=messages.SUCCESS)

    @admin.action(description="Resend: Stuck Email Opened")
    def resend_stuck_opened_email(self, request, queryset):
        count = self._resend_with_template(request, queryset, 'STUCK_OPENED')
        self.message_user(request, f"{count} orientation nudge email(s) sent.", level=messages.SUCCESS)

    def get_urls(self):
        custom_urls = [
            path('send-invitation/',
                 self.admin_site.admin_view(self.send_invitation_view),
                 name='send_onboarding_invitation'),
        ]
        return custom_urls + super().get_urls()

    def send_invitation_view(self, request):
        if request.method == 'POST':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()

            if not first_name or not last_name or not email:
                messages.error(request, 'First name, last name, and email are required.')
                return render(request, 'admin/onboarding/send_invitation.html', {
                    'title': 'Send Onboarding Invitation',
                    'opts': self.model._meta,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                })

            active = OnboardingInvitation.objects.filter(
                email=email,
                current_phase__in=['INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED', 'ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED']
            ).exists()

            if active:
                messages.warning(request, f'An active onboarding invitation already exists for {email}.')
                return redirect('admin:app_onboardinginvitation_changelist')

            try:
                invitation = onboarding_svc.create_invitation(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    created_by=request.user,
                    request=request,
                )

                if invitation.email_sent_at:
                    messages.success(request, f'Onboarding invitation sent to {first_name} {last_name} ({email}).')
                else:
                    messages.warning(request, f'Invitation created but email failed to send to {email}.')

            except Exception as e:
                logger.error(f"Failed to send onboarding invitation: {e}", exc_info=True)
                messages.error(request, f'Error: {e}')

            return redirect('admin:app_onboardinginvitation_changelist')

        return render(request, 'admin/onboarding/send_invitation.html', {
            'title': 'Send Onboarding Invitation',
            'opts': self.model._meta,
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_send_button'] = True
        extra_context['send_url'] = reverse('admin:send_onboarding_invitation')
        return super().changelist_view(request, extra_context=extra_context)