from django.contrib import admin
from django.utils import timezone
from app import models
from .performance import AdminPerformanceMixin

@admin.register(models.Notification)
class NotificationAdmin(AdminPerformanceMixin, admin.ModelAdmin):
    admin_select_related = ('recipient',)
    admin_defer_changelist = ('content',)
    list_display = ('recipient', 'type', 'title', 'read', 'created_at')
    list_filter = ('type', 'read', 'created_at')
    search_fields = ('recipient__email', 'title', 'content')
    autocomplete_fields = ('recipient',)
    readonly_fields = ('created_at',)

@admin.register(models.ContactMessage)
class ContactMessageAdmin(AdminPerformanceMixin, admin.ModelAdmin):
    admin_select_related = ('processed_by',)
    admin_defer_changelist = ('message', 'notes')
    list_display = ('subject', 'name', 'email', 'created_at', 'processed')
    list_filter = ('processed', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    autocomplete_fields = ('processed_by',)
    readonly_fields = ('created_at',)
    def mark_as_processed(self, request, queryset):
        queryset.update(
            processed=True,
            processed_by=request.user,
            processed_at=timezone.now()
        )
    mark_as_processed.short_description = "Mark as processed"
    actions = [mark_as_processed]
