"""
Core context processors – inject site-wide settings into all templates
"""

from django.conf import settings


def site_settings(request):
    """Make site settings available in all templates"""
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Urban Holidays'),
        'SITE_URL': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'VOUCHER_PRICE': getattr(settings, 'VOUCHER_PRICE', 149),
        'RAZORPAY_KEY_ID': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
