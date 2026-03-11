from django.contrib import admin
from django.utils.html import mark_safe
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from app.models import OnboardingInvitation, OnboardingTrackingEvent
import json


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

    actions = ['void_invitations', 'resend_invitations']

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
                inv.current_phase = 'VOIDED'
                inv.voided_by = request.user
                inv.voided_at = timezone.now()
                inv.void_reason = "Voided by admin bulk action"
                inv.save()
                OnboardingTrackingEvent.objects.create(
                    invitation=inv,
                    event_type='VOIDED',
                    performed_by=request.user,
                    metadata={'reason': 'Admin bulk action'}
                )
                count += 1
        self.message_user(request, f"{count} invitation(s) voided.", level=messages.SUCCESS)

    @admin.action(description="Resend invitations (new version)")
    def resend_invitations(self, request, queryset):
        from app.services.email_service import OnboardingEmailService

        count = 0
        for old_inv in queryset:
            if old_inv.current_phase not in ('VOIDED', 'EXPIRED'):
                old_inv.current_phase = 'VOIDED'
                old_inv.voided_by = request.user
                old_inv.voided_at = timezone.now()
                old_inv.void_reason = "Voided for resending"
                old_inv.save()

            new_inv = OnboardingInvitation.objects.create(
                email=old_inv.email,
                first_name=old_inv.first_name,
                last_name=old_inv.last_name,
                phone=old_inv.phone,
                created_by=request.user,
                version=old_inv.version + 1,
            )

            OnboardingTrackingEvent.objects.create(
                invitation=new_inv,
                event_type='RESENT',
                performed_by=request.user,
                metadata={'original_invitation_id': str(old_inv.id)}
            )

            OnboardingEmailService.send_invitation_email(new_inv, request)
            count += 1

        self.message_user(request, f"{count} invitation(s) resent.", level=messages.SUCCESS)

    # Custom admin URL for sending new invitations
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

            # Check for existing active invitation
            active = OnboardingInvitation.objects.filter(
                email=email,
                current_phase__in=['INVITED', 'EMAIL_OPENED', 'WELCOME_VIEWED', 'ACCOUNT_CREATED', 'PROFILE_COMPLETED', 'CONTRACT_STARTED']
            ).exists()

            if active:
                messages.warning(request, f'An active onboarding invitation already exists for {email}.')
                return redirect('admin:app_onboardinginvitation_changelist')

            try:
                from app.services.email_service import OnboardingEmailService
                from app.models import User

                invitation = OnboardingInvitation.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    created_by=request.user,
                    email_sent_at=timezone.now(),
                )

                # Check if user already exists with this email
                existing_user = User.objects.filter(email=email).first()
                if existing_user:
                    invitation.user = existing_user
                    interpreter = getattr(existing_user, 'interpreter', None)
                    if interpreter:
                        invitation.interpreter = interpreter
                    invitation.save()

                OnboardingTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='EMAIL_SENT',
                    performed_by=request.user,
                    metadata={'source': 'admin_send_form'}
                )

                email_sent = OnboardingEmailService.send_invitation_email(invitation, request)

                if email_sent:
                    messages.success(request, f'Onboarding invitation sent to {first_name} {last_name} ({email}).')
                else:
                    messages.warning(request, f'Invitation created but email failed to send to {email}.')

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
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
