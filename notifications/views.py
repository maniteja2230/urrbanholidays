"""
Notifications app views
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    """List all notifications for the user"""
    notifications = Notification.objects.filter(user=request.user)
    # Mark all as read
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'dashboard/notifications.html', {
        'notifications': notifications
    })


@login_required
@require_POST
def mark_read(request, notification_id):
    """Mark a single notification as read (AJAX)"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_read()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read (AJAX)"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok', 'count': 0})


@login_required
def unread_count(request):
    """Return unread notification count (for navbar badge)"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})
