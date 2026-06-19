"""
Notifications app model
"""

from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    """In-app notifications for users"""
    TYPE_CHOICES = [
        ('voucher', 'Voucher'),
        ('payment', 'Payment'),
        ('referral', 'Referral'),
        ('redemption', 'Redemption'),
        ('system', 'System'),
        ('promotion', 'Promotion'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @property
    def icon(self):
        icons = {
            'voucher': '🎟️',
            'payment': '💳',
            'referral': '🎁',
            'redemption': '✅',
            'system': '🔔',
            'promotion': '🎉',
        }
        return icons.get(self.notification_type, '🔔')
