import json
import hmac
import hashlib
import logging
import razorpay
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import Voucher, Coupon, Redemption, assign_random_reward, get_reward_detail
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

# ── Razorpay client ─────────────────────────────────────────────────
rz_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)



@login_required
def buy_voucher(request):
    """
    Razorpay checkout page.
    Shows the Razorpay payment button.
    """
    amount = settings.VOUCHER_PRICE  # 149
    return render(request, 'vouchers/buy.html', {
        'amount': amount,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })


@login_required
def create_order(request):
    """POST: Create Razorpay order and return order_id"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    amount_inr = settings.VOUCHER_PRICE          # 149
    amount_paise = amount_inr * 100              # 14900 paise

    if amount_paise < 100:
        return JsonResponse({'error': 'Amount too low'}, status=400)

    try:
        order = rz_client.order.create({
            'amount':   amount_paise,
            'currency': 'INR',
            'receipt':  f'uh_{request.user.id}_{timezone.now().strftime("%Y%m%d%H%M%S")}',
            'payment_capture': 1,
        })
        return JsonResponse({
            'order_id': order['id'],
            'amount':   order['amount'],
            'currency': order['currency'],
            'key_id':   settings.RAZORPAY_KEY_ID,
        })
    except razorpay.errors.BadRequestError as e:
        logger.error(f'Razorpay BadRequest: {e}')
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f'Razorpay order creation failed: {e}')
        return JsonResponse({'error': 'Payment gateway error. Please try again.'}, status=500)


@csrf_exempt
@login_required
def verify_payment(request):
    """POST: Verify Razorpay payment signature and activate membership"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    payment_id = data.get('razorpay_payment_id', '')
    order_id   = data.get('razorpay_order_id', '')
    signature  = data.get('razorpay_signature', '')

    if not all([payment_id, order_id, signature]):
        return JsonResponse({'error': 'Missing payment details'}, status=400)

    # ── Verify HMAC-SHA256 signature ──────────────────────────────
    msg        = f'{order_id}|{payment_id}'.encode()
    secret     = settings.RAZORPAY_KEY_SECRET.encode()
    gen_sig    = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(gen_sig, signature):
        logger.warning(f'Razorpay signature mismatch for order {order_id}')
        return JsonResponse({'error': 'Payment verification failed. Please contact support.'}, status=400)

    # ── Signature valid — activate membership ─────────────────────
    amount = settings.VOUCHER_PRICE

    # Prevent duplicate activations for same order
    if Voucher.objects.filter(razorpay_order_id=order_id).exists():
        voucher = Voucher.objects.get(razorpay_order_id=order_id)
        return JsonResponse({'success': True, 'voucher_number': voucher.voucher_number})

    # Assign random scratch card reward
    reward      = assign_random_reward()
    reward_text = get_reward_detail(reward)

    voucher = Voucher.objects.create(
        user               = request.user,
        amount             = amount,
        status             = 'active',
        payment_method     = 'razorpay',
        razorpay_order_id  = order_id,
        razorpay_payment_id= payment_id,
        utr_number         = payment_id,   # store payment_id as reference
        expiry_date        = timezone.now() + timedelta(days=settings.VOUCHER_VALIDITY_DAYS),
        reward_type        = reward,
        reward_detail      = reward_text,
        reward_revealed    = False,
    )

    # Generate QR code
    try:
        from .utils import generate_qr_code
        generate_qr_code(voucher)
    except Exception as e:
        logger.warning(f'QR generation failed: {e}')

    # ── Credit Rs.20 joining bonus to wallet ──────────────────────
    try:
        from accounts.models import Profile
        profile = Profile.objects.get(user=request.user)
        joining_bonus = getattr(settings, 'JOINING_BONUS', 20)
        profile.wallet_balance += joining_bonus
        profile.save(update_fields=['wallet_balance'])
        # Notify user of joining bonus
        from notifications.models import Notification
        Notification.objects.create(
            user=request.user,
            title='🎉 Welcome Bonus Credited!',
            message=f'Rs.{joining_bonus} joining bonus has been added to your wallet. Welcome to Urban Holidays!',
            notification_type='wallet',
        )
    except Exception as e:
        logger.warning(f'Joining bonus credit failed: {e}')

    # Notify admins
    try:
        from notifications.models import Notification
        from django.contrib.auth.models import User as AuthUser
        for admin in AuthUser.objects.filter(is_staff=True):
            Notification.objects.create(
                user=admin,
                title='💰 New Razorpay Payment Received',
                message=(
                    f'User {request.user.username} paid ₹{amount} via Razorpay. '
                    f'Payment ID: {payment_id}. Membership: {voucher.voucher_number}. '
                    f'Auto-activated!'
                ),
                notification_type='voucher',
            )
    except Exception as e:
        logger.warning(f'Admin notification failed: {e}')

    # Send activation email
    try:
        send_membership_activated_email(voucher)
    except Exception as e:
        logger.warning(f'Activation email failed: {e}')

    logger.info(f'Membership {voucher.voucher_number} activated via Razorpay for {request.user.username}')
    return JsonResponse({'success': True, 'voucher_number': voucher.voucher_number})



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
