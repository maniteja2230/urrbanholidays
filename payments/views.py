"""
Payments app views – Razorpay payment callback and webhook
"""

import json
import hmac
import hashlib
import logging

from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PaymentTransaction
from .utils import verify_razorpay_payment, create_razorpay_order
from vouchers.models import Voucher, Coupon

logger = logging.getLogger(__name__)


@login_required
@require_POST
def initiate_payment(request):
    """
    Create a Razorpay order (used when the buy page needs to create
    an order dynamically via AJAX — kept as a fallback endpoint).
    """
    try:
        amount = settings.VOUCHER_PRICE
        order = create_razorpay_order(
            amount=amount,
            currency='INR',
            notes={'user_id': str(request.user.id), 'type': 'voucher_purchase'}
        )
        PaymentTransaction.objects.create(
            user=request.user,
            razorpay_order_id=order['id'],
            amount=amount,
            currency='INR',
            status='created',
            notes={'type': 'voucher_purchase'},
        )
        return JsonResponse({
            'order_id':    order['id'],
            'amount':      int(amount) * 100,   # paise
            'currency':    'INR',
            'key':         settings.RAZORPAY_KEY_ID,
            'name':        settings.SITE_NAME,
            'description': f'Urban Holidays Mega Ticket Voucher - ₹{amount}',
            'prefill': {
                'name':    request.user.get_full_name(),
                'email':   request.user.email,
                'contact': getattr(getattr(request.user, 'profile', None), 'phone', '') or '',
            },
        })
    except Exception as e:
        logger.error(f"Payment initiation error: {e}")
        return JsonResponse({'error': 'Payment initiation failed'}, status=500)


@csrf_exempt
@require_POST
def payment_callback(request):
    """
    Called by the front-end after Razorpay checkout succeeds.
    Verifies the payment signature, marks the transaction as paid,
    and creates the voucher + coupon.
    """
    try:
        # Accept both JSON body and form POST
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        razorpay_order_id   = data.get('razorpay_order_id', '').strip()
        razorpay_payment_id = data.get('razorpay_payment_id', '').strip()
        razorpay_signature  = data.get('razorpay_signature', '').strip()

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return JsonResponse(
                {'status': 'error', 'message': 'Missing payment data'},
                status=400
            )

        # Verify Razorpay HMAC signature
        is_valid = verify_razorpay_payment(
            razorpay_order_id, razorpay_payment_id, razorpay_signature
        )

        with transaction.atomic():
            try:
                txn = PaymentTransaction.objects.select_for_update().get(
                    razorpay_order_id=razorpay_order_id
                )
            except PaymentTransaction.DoesNotExist:
                return JsonResponse(
                    {'status': 'error', 'message': 'Transaction not found'},
                    status=404
                )

            # Guard against double-processing
            if txn.status == 'paid':
                # Already processed – return the existing voucher
                try:
                    voucher = Voucher.objects.get(payment_transaction=txn)
                    return JsonResponse({
                        'status': 'success',
                        'voucher_number': voucher.voucher_number,
                        'redirect_url': f'/vouchers/success/{voucher.voucher_number}/',
                    })
                except Voucher.DoesNotExist:
                    pass

            txn.razorpay_payment_id = razorpay_payment_id
            txn.razorpay_signature  = razorpay_signature

            if is_valid:
                txn.status = 'paid'
                txn.save()

                # ── Create Voucher ─────────────────────────────────────
                voucher = Voucher.objects.create(
                    user=txn.user,
                    amount=txn.amount,
                    payment_transaction=txn,
                )

                # Generate QR Code
                voucher.generate_qr()

                # Create Coupon (unique code)
                Coupon.objects.create(voucher=voucher)

                # ── Create Notification ────────────────────────────────
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=txn.user,
                        title='Voucher Purchased Successfully! 🎉',
                        message=(
                            f'Your Urban Holidays voucher #{voucher.voucher_number} '
                            f'worth ₹{voucher.amount} is ready. '
                            f'Valid till {voucher.expiry_date.strftime("%d/%m/%Y")}.'
                        ),
                        notification_type='voucher',
                    )
                except Exception as notif_err:
                    logger.warning(f"Notification creation failed: {notif_err}")

                return JsonResponse({
                    'status': 'success',
                    'voucher_number': voucher.voucher_number,
                    'redirect_url': f'/vouchers/success/{voucher.voucher_number}/',
                })

            else:
                txn.status = 'failed'
                txn.error_description = 'Signature verification failed'
                txn.save()
                return JsonResponse(
                    {'status': 'error', 'message': 'Payment verification failed – invalid signature'},
                    status=400
                )

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Payment callback error: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def razorpay_webhook(request):
    """
    Razorpay server-to-server webhook for reliable payment confirmation.
    Verify X-Razorpay-Signature before processing.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload   = request.body
        signature = request.headers.get('X-Razorpay-Signature', '')
        secret    = settings.RAZORPAY_KEY_SECRET.encode('utf-8')

        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, signature):
            logger.warning("Razorpay webhook: invalid signature")
            return HttpResponse(status=400)

        event      = json.loads(payload)
        event_type = event.get('event')

        if event_type == 'payment.captured':
            payment  = event['payload']['payment']['entity']
            order_id = payment.get('order_id', '')
            try:
                txn = PaymentTransaction.objects.get(razorpay_order_id=order_id)
                if txn.status != 'paid':
                    txn.status = 'paid'
                    txn.razorpay_payment_id = payment.get('id', '')
                    txn.payment_method      = payment.get('method', '')
                    txn.save()
            except PaymentTransaction.DoesNotExist:
                logger.warning(f"Webhook: transaction not found for order {order_id}")

        return HttpResponse(status=200)

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return HttpResponse(status=500)
