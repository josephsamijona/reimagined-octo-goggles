from django.contrib import admin
from django.utils.html import mark_safe
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from app.models import ContractInvitation, ContractTrackingEvent
from django.utils.translation import gettext_lazy as _
import datetime

class ContractTrackingEventInline(admin.TabularInline):
    model = ContractTrackingEvent
    extra = 0
    readonly_fields = ('event_type', 'timestamp', 'performed_by', 'metadata_display')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def metadata_display(self, obj):
        import json
        return mark_safe(f"<pre>{json.dumps(obj.metadata, indent=2)}</pre>")
    metadata_display.short_description = "Metadata"


@admin.register(ContractInvitation)
class ContractInvitationAdmin(admin.ModelAdmin):
    list_display = (
        'invitation_number',
        'interpreter_name',
        'status_badge',
        'version',
        'email_sent_at',
        'signed_at',
        'created_by'
    )
    list_filter = ('status', 'version', 'created_at')
    search_fields = (
        'invitation_number', 
        'interpreter__user__email', 
        'interpreter__user__first_name', 
        'interpreter__user__last_name'
    )
    readonly_fields = (
        'invitation_number', 
        'token', 
        'accept_token', 
        'review_token', 
        'created_at',
        'email_sent_at',
        'email_opened_at',
        'link_clicked_at',
        'signed_at',
        'voided_at',
        'tracking_timeline',
        'download_pdf_link_display'
    )
    inlines = [ContractTrackingEventInline]
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('invitation_number', 'interpreter', 'status', 'version', 'created_by')
        }),
        ('Tokens', {
            'fields': ('token', 'accept_token', 'review_token'),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': ('tracking_timeline',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'email_sent_at', 'email_opened_at', 
                'link_clicked_at', 'signed_at', 'voided_at'
            ),
            'classes': ('collapse',)
        }),
        ('PDF & Storage', {
            'fields': ('pdf_s3_key', 'download_pdf_link_display'),
            'classes': ('collapse',)
        }),
        ('Void Info', {
            'fields': ('voided_by', 'void_reason'),
            'classes': ('collapse',),
            'description': 'Information if invalid/voided'
        })
    )
    
    actions = ['void_invitations', 'resend_invitations']
    
    def interpreter_name(self, obj):
        return obj.interpreter.user.get_full_name()
    interpreter_name.short_description = 'Interpreter'
    interpreter_name.admin_order_field = 'interpreter__user__last_name'
    
    def status_badge(self, obj):
        colors = {
            'SENT': 'blue',
            'OPENED': 'cyan',
            'REVIEWING': 'purple',
            'SIGNED': 'green',
            'VOIDED': 'red',
            'EXPIRED': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return mark_safe(f'<span style="background:{color};color:white;padding:4px 8px;border-radius:4px;font-weight:bold;">{obj.status}</span>')
    status_badge.short_description = 'Status'
    
    def download_pdf_link_display(self, obj):
        if obj.pdf_s3_key:
            from django.urls import reverse
            url = reverse('dbdint:contract_pdf_download', kwargs={'invitation_id': obj.id})
            return mark_safe(f'<a href="{url}" class="button" target="_blank">Download PDF</a>')
        return "Not generated yet"
    download_pdf_link_display.short_description = "PDF Download"
    
    def tracking_timeline(self, obj):
        """Display visual timeline of tracking events"""
        events = obj.tracking_events.all().order_by('-timestamp')
        if not events:
            return "No events recorded."
            
        html = '<div style="max-height:300px;overflow-y:auto;padding:10px;border:1px solid #ccc;background:#fff;">'
        for event in events:
            icon = "•"
            color = "#666"
            if "SENT" in event.event_type: icon="✉️"; color="blue"
            elif "OPENED" in event.event_type: icon="👁️"; color="cyan"
            elif "CLICKED" in event.event_type: icon="🖱️"; color="purple"
            elif "SIGNED" in event.event_type: icon="✍️"; color="green"
            elif "VOIDED" in event.event_type: icon="🚫"; color="red"
            
            html += f'<div style="margin-bottom:10px;padding:8px;border-left:3px solid {color};background:#f9f9f9;">'
            html += f'<div style="font-weight:bold;color:{color}">{icon} {event.get_event_type_display()}</div>'
            html += f'<div style="font-size:0.9em;color:#555">{event.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</div>'
            if event.performed_by:
                html += f'<div style="font-size:0.8em;color:#777">by {event.performed_by.get_full_name()}</div>'
            html += '</div>'
        html += '</div>'
        return mark_safe(html)
    tracking_timeline.short_description = 'Event Timeline'
    
    @admin.action(description="Void selected invitations")
    def void_invitations(self, request, queryset):
        # Bulk void action uses generic reason. For custom reasons, void individually.
        updated_count = 0
        for invitation in queryset:
            if invitation.status not in ['VOIDED', 'EXPIRED']:
                invitation.status = 'VOIDED'
                invitation.voided_by = request.user
                invitation.voided_at = timezone.now()
                invitation.void_reason = "Voided by admin bulk action"
                invitation.save()
                
                ContractTrackingEvent.objects.create(
                    invitation=invitation,
                    event_type='VOIDED',
                    performed_by=request.user,
                    metadata={'reason': "Admin bulk action"}
                )
                updated_count += 1
        
        self.message_user(request, f"{updated_count} invitations successfully voided.")
    
    @admin.action(description="Resend invitations (Create new version)")
    def resend_invitations(self, request, queryset):
        sent_count = 0
        for old_invitation in queryset:
            # 1. Void the old one
            if old_invitation.status not in ['VOIDED', 'EXPIRED']:
                old_invitation.status = 'VOIDED'
                old_invitation.voided_by = request.user
                old_invitation.voided_at = timezone.now()
                old_invitation.void_reason = "Voided for resending"
                old_invitation.save()
                
            # 2. Create new version
            new_invitation = ContractInvitation.objects.create(
                interpreter=old_invitation.interpreter,
                created_by=request.user,
                version=old_invitation.version + 1,
                status='SENT',
                # Tokens auto-generated on save
            )
            
            # 3. Create tracking event linked to new invitation
            ContractTrackingEvent.objects.create(
                invitation=new_invitation,
                event_type='RESENT',
                performed_by=request.user,
                metadata={'original_invitation_id': str(old_invitation.id)}
            )
            
            # 4. Trigger email logic
            from app.services.email_service import ContractEmailService
            ContractEmailService.send_invitation_email(new_invitation, request)
            
            sent_count += 1
            
        self.message_user(request, f"{sent_count} invitations regenerated and sent.")
    

