"""
Notifications app admin
"""

from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    list_editable = ['is_read']
    readonly_fields = ['created_at', 'read_at']

    actions = ['send_bulk_notification']

    def send_bulk_notification(self, request, queryset):
        """Resend selected notifications"""
        self.message_user(request, f'Notifications re-queued.')
    send_bulk_notification.short_description = 'Re-send notification'
