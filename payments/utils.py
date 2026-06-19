"""
Payments utility functions – Razorpay integration helpers
"""

import hmac
import hashlib
import razorpay
from django.conf import settings


def get_razorpay_client():
    """Return an authenticated Razorpay client instance."""
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def create_razorpay_order(amount: int, currency: str = 'INR', notes: dict = None) -> dict:
    """
    Create a Razorpay order.
    `amount` is in rupees — converted to paise internally.
    Returns the full order dict from Razorpay.
    """
    client = get_razorpay_client()
    order = client.order.create({
        'amount':          int(amount) * 100,   # paise
        'currency':        currency,
        'payment_capture': 1,                   # auto-capture
        'notes':           notes or {},
    })
    return order


def verify_razorpay_payment(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify the Razorpay payment signature to prevent tampering.

    Razorpay signature = HMAC-SHA256(
        key   = razorpay_key_secret,
        message = "<order_id>|<payment_id>"
    )

    Returns True if valid, False otherwise.
    """
    try:
        message = f"{order_id}|{payment_id}".encode('utf-8')
        secret  = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
        expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def fetch_payment_details(payment_id: str) -> dict:
    """Fetch a single payment's details from Razorpay."""
    client = get_razorpay_client()
    return client.payment.fetch(payment_id)


def refund_payment(payment_id: str, amount: int = None) -> dict:
    """
    Initiate a refund.
    `amount` is in rupees; converted to paise if provided.
    If amount is None, the full payment is refunded.
    """
    client = get_razorpay_client()
    data = {'speed': 'normal'}
    if amount:
        data['amount'] = int(amount) * 100
    return client.payment.refund(payment_id, data)
