"""
Core app views – Home, About, Contact, FAQ, Terms & Conditions
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .models import FAQ, ContactMessage, Testimonial, SiteBanner
from packages.models import TravelPackage


def home(request):
    """Homepage with hero, packages, testimonials"""
    context = {
        'banners': SiteBanner.objects.filter(is_active=True)[:5],
        'featured_packages': TravelPackage.objects.filter(
            is_active=True, is_featured=True
        ).order_by('-created_at')[:6],
        'testimonials': Testimonial.objects.filter(is_active=True)[:6],
        'voucher_price': settings.VOUCHER_PRICE,
    }
    return render(request, 'core/home.html', context)


def about(request):
    """About Us page"""
    return render(request, 'core/about.html')


def contact(request):
    """Contact Us page with form"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not all([name, email, subject, message_text]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'core/contact.html', {
                'name': name, 'email': email,
                'phone': phone, 'subject': subject,
                'message': message_text
            })

        # Save to database
        ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message_text,
        )

        # Send notification email to admin
        try:
            send_mail(
                subject=f"New Contact: {subject}",
                message=f"From: {name} ({email})\nPhone: {phone}\n\n{message_text}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else settings.EMAIL_HOST_USER],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request, 'Thank you! Your message has been sent. We will get back to you soon.')
        return redirect('core:contact')

    return render(request, 'core/contact.html')


def faq(request):
    """FAQ page"""
    faqs = FAQ.objects.filter(is_active=True)
    return render(request, 'core/faq.html', {'faqs': faqs})


def terms(request):
    """Terms & Conditions page"""
    return render(request, 'core/terms.html')


def privacy(request):
    """Privacy Policy page"""
    return render(request, 'core/privacy.html')


def context_processors(request):
    """Global context (used in base.html)"""
    return {
        'site_name': settings.SITE_NAME,
        'voucher_price': settings.VOUCHER_PRICE,
    }
