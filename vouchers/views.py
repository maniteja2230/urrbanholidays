import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import Voucher, Coupon, Redemption
from .forms import RedemptionForm
from .utils import generate_voucher_pdf
from core.email_utils import (
    send_payment_received_email,
    send_membership_activated_email,
    send_membership_rejected_email,
    send_redemption_approved_email,
    send_redemption_rejected_email,
)

logger = logging.getLogger(__name__)


@login_required
def buy_voucher(request):
    """
    Paytm QR payment page.
    Shows QR code + form to enter UTR/Transaction ID after paying.
    """
    amount = settings.VOUCHER_PRICE  # 149

    if request.method == 'POST':
        utr = request.POST.get('utr_number', '').strip()
        screenshot = request.FILES.get('payment_screenshot')

        if not utr:
            messages.error(request, 'Please enter your UPI Transaction ID / UTR number.')
            return render(request, 'vouchers/buy.html', {'amount': amount})

        # Check if UTR already used (prevent duplicates)
        if Voucher.objects.filter(utr_number=utr).exists():
            messages.error(request, 'This Transaction ID has already been submitted. Please contact support.')
            return render(request, 'vouchers/buy.html', {'amount': amount})

        # Create voucher in pending_payment status
        voucher = Voucher.objects.create(
            user=request.user,
            amount=amount,
            status='pending_payment',
            utr_number=utr,
            payment_method='paytm_qr',
            expiry_date=timezone.now() + timedelta(days=settings.VOUCHER_VALIDITY_DAYS),
        )

        # Save screenshot if uploaded
        if screenshot:
            voucher.payment_screenshot = screenshot
            voucher.save()

        # Notify admins
        try:
            from notifications.models import Notification
            from django.contrib.auth.models import User as AuthUser
            for admin in AuthUser.objects.filter(is_staff=True):
                Notification.objects.create(
                    user=admin,
                    title='💰 New Payment Verification Required',
                    message=(
                        f'User {request.user.username} paid ₹{amount} via Paytm. '
                        f'UTR: {utr}. Voucher: {voucher.voucher_number}. '
                        f'Please verify and activate in admin panel.'
                    ),
                    notification_type='voucher',
                )
        except Exception as e:
            logger.warning(f"Admin notification failed: {e}")

        # Send payment received email
        try:
            send_payment_received_email(voucher)
        except Exception as e:
            logger.warning(f"Payment email failed: {e}")

        return redirect('vouchers:payment_pending', voucher_number=voucher.voucher_number)

    return render(request, 'vouchers/buy.html', {'amount': amount})


@login_required
def payment_pending(request, voucher_number):
    """Show pending verification page after UTR submission"""
    voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)
    return render(request, 'vouchers/payment_pending.html', {'voucher': voucher})


@login_required
def voucher_success(request, voucher_number):
    """Voucher purchase success page"""
    voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)
    coupon = getattr(voucher, 'coupon', None)
    return render(request, 'vouchers/success.html', {
        'voucher': voucher,
        'coupon': coupon,
    })


@login_required
def voucher_detail(request, voucher_number):
    """Voucher detail page"""
    voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)
    coupon = getattr(voucher, 'coupon', None)
    redemptions = voucher.redemptions.all()
    return render(request, 'vouchers/detail.html', {
        'voucher': voucher,
        'coupon': coupon,
        'redemptions': redemptions,
    })


@login_required
def reveal_reward(request, voucher_number):
    """Mark reward as revealed when user taps scratch card"""
    if request.method == 'POST':
        voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)
        if not voucher.reward_revealed and voucher.reward_type:
            voucher.reward_revealed = True
            voucher.save()
    return redirect('vouchers:detail', voucher_number=voucher_number)


@login_required
def redeem_voucher(request, voucher_number):
    """Submit redemption request"""
    voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)

    if voucher.status != 'active':
        messages.error(request, f'This voucher is {voucher.get_status_display()} and cannot be redeemed.')
        return redirect('vouchers:detail', voucher_number=voucher_number)

    if voucher.is_expired:
        voucher.status = 'expired'
        voucher.save()
        messages.error(request, 'This voucher has expired.')
        return redirect('vouchers:detail', voucher_number=voucher_number)

    if voucher.redemptions.filter(status='pending').exists():
        messages.warning(request, 'You already have a pending redemption request.')
        return redirect('vouchers:detail', voucher_number=voucher_number)

    if request.method == 'POST':
        form = RedemptionForm(request.POST)
        if form.is_valid():
            redemption = form.save(commit=False)
            redemption.voucher = voucher
            redemption.save()
            messages.success(request, 'Redemption request submitted! Our team will review it within 24–48 hours.')
            return redirect('vouchers:detail', voucher_number=voucher_number)
    else:
        form = RedemptionForm()

    return render(request, 'vouchers/redeem.html', {'form': form, 'voucher': voucher})


@login_required
def download_voucher_pdf(request, voucher_number):
    """Download voucher as PDF"""
    voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)
    coupon = getattr(voucher, 'coupon', None)
    pdf_buffer = generate_voucher_pdf(voucher, coupon)
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="UrbanHolidays_Voucher_{voucher.voucher_number}.pdf"'
    )
    return response
