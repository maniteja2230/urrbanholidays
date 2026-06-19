"""
Urban Holidays - Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

admin.site.site_header = "Urban Holidays Administration"
admin.site.site_title = "Urban Holidays Admin"
admin.site.index_title = "Welcome to Urban Holidays Admin Panel"

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Core / Public pages
    path('', include('core.urls', namespace='core')),

    # Authentication
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # Vouchers
    path('vouchers/', include('vouchers.urls', namespace='vouchers')),

    # Travel Packages
    path('packages/', include('packages.urls', namespace='packages')),

    # Payments
    path('payments/', include('payments.urls', namespace='payments')),

    # User Dashboard
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),

    # Notifications
    path('notifications/', include('notifications.urls', namespace='notifications')),

    # Password Reset (Django built-in)
    path('accounts/password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
         ),
         name='password_reset'),
    path('accounts/password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('accounts/reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
