"""
Vouchers app views – Get Voucher, Buy (Razorpay), Detail, Redeem, Download PDF
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.db import transaction

from .models import Voucher, Coupon, Redemption
from .forms import RedemptionForm
from .utils import generate_voucher_pdf
from payments.models import PaymentTransaction
from payments.utils import create_razorpay_order

logger = logging.getLogger(__name__)


@login_required
def buy_voucher(request):
    """
    'Get Voucher' page – shows voucher details, creates a Razorpay order
    server-side and passes order_id + key to the template so the
    Razorpay checkout can fire directly without any extra API call.
    """
    amount = settings.VOUCHER_PRICE          # e.g. 149 (rupees)
    razorpay_order_id = ''
    error = None

    try:
        profile = getattr(request.user, 'profile', None)
        order = create_razorpay_order(
            amount=amount,
            currency='INR',
            notes={
                'user_id': str(request.user.id),
                'username': request.user.username,
                'type': 'voucher_purchase',
            }
        )
        razorpay_order_id = order.get('id', '')

        # Persist a pending transaction so payment_callback can locate it
        PaymentTransaction.objects.get_or_create(
            razorpay_order_id=razorpay_order_id,
            defaults={
                'user': request.user,
                'amount': amount,
                'currency': 'INR',
                'status': 'created',
                'notes': {'type': 'voucher_purchase'},
            }
        )
    except Exception as e:
        logger.error(f"Razorpay order creation error: {e}")
        error = "Unable to create payment order. Please try again."

    profile = getattr(request.user, 'profile', None)

    context = {
        'amount': amount,
        'amount_paise': int(amount) * 100,           # Razorpay SDK expects paise
        'razorpay_order_id': razorpay_order_id,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'user_name': request.user.get_full_name() or request.user.username,
        'user_email': request.user.email,
        'user_phone': getattr(profile, 'phone', '') or '',
        'error': error,
    }
    return render(request, 'vouchers/buy.html', context)


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
    context = {
        'voucher': voucher,
        'coupon': coupon,
        'redemptions': redemptions,
    }
    return render(request, 'vouchers/detail.html', context)


@login_required
def redeem_voucher(request, voucher_number):
    """Submit redemption request"""
    voucher = get_object_or_404(Voucher, voucher_number=voucher_number, user=request.user)

    if voucher.status != 'active':
        messages.error(request, f'This voucher is {voucher.status} and cannot be redeemed.')
        return redirect('vouchers:detail', voucher_number=voucher_number)

    if voucher.is_expired:
        voucher.status = 'expired'
        voucher.save()
        messages.error(request, 'This voucher has expired.')
        return redirect('vouchers:detail', voucher_number=voucher_number)

    if voucher.redemptions.filter(status='pending').exists():
        messages.warning(request, 'You already have a pending redemption request for this voucher.')
        return redirect('vouchers:detail', voucher_number=voucher_number)

    if request.method == 'POST':
        form = RedemptionForm(request.POST)
        if form.is_valid():
            redemption = form.save(commit=False)
            redemption.voucher = voucher
            redemption.save()

            from notifications.models import Notification
            from django.contrib.auth.models import User as AuthUser
            for admin in AuthUser.objects.filter(is_staff=True):
                Notification.objects.create(
                    user=admin,
                    title='New Redemption Request',
                    message=(
                        f'User {request.user.username} submitted a redemption '
                        f'request for voucher {voucher.voucher_number}.'
                    ),
                    notification_type='system',
                )

            messages.success(
                request,
                'Redemption request submitted! Our team will review it within 24–48 hours.'
            )
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
