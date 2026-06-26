"""
Centralized email utility for Urban Holidays.
Handles all transactional emails.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

FROM = settings.DEFAULT_FROM_EMAIL


def _send(subject, message, to_email):
    """Base send helper — fails silently and logs errors."""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=FROM,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f"Email sent to {to_email}: {subject}")
    except Exception as e:
        logger.error(f"Email failed to {to_email}: {e}")


# ── Registration ──────────────────────────────────────────────────
def send_welcome_email(user):
    name = user.get_full_name() or user.username
    _send(
        subject="🎉 Welcome to Urban Holidays!",
        message=f"""Hi {name}!

Welcome to Urban Holidays 🌍

Your account has been created successfully.

🔗 Login: https://urrbanholidays.in/accounts/login/

🏆 Get your Membership Plan for just ₹149 and:
  • Get a Lucky Draw scratch card reward
  • Win Wonderla tickets, Gold, Trip, Headset, Watch & more!
  • Redeem for FREE travel experiences

See you on board! ✈️
Team Urban Holidays
📧 support@urrbanholidays.in
🌐 https://urrbanholidays.in
""",
        to_email=user.email,
    )


# ── Payment Received ──────────────────────────────────────────────
def send_payment_received_email(voucher):
    user = voucher.user
    name = user.get_full_name() or user.username
    _send(
        subject="⏳ Payment Received – Verification in Progress",
        message=f"""Hi {name}!

We have received your payment of ₹{voucher.amount}.

📋 Details:
  • Membership ID : {voucher.voucher_number}
  • UTR / Txn ID  : {voucher.utr_number}
  • Amount        : ₹{voucher.amount}
  • Status        : Pending Verification ⏳

We will verify your payment and activate your membership within 30 minutes.
You will receive another email once it's activated!

Need help? Email us: support@urrbanholidays.in
Team Urban Holidays ✈️
""",
        to_email=user.email,
    )


# ── Membership Activated ──────────────────────────────────────────
def send_membership_activated_email(voucher):
    user = voucher.user
    name = user.get_full_name() or user.username
    _send(
        subject="🎉 Membership Activated! Scratch Your Lucky Draw!",
        message=f"""Hi {name}!

Great news! Your payment has been verified and your membership is now ACTIVE! 🎊

📋 Membership Details:
  • Membership ID : {voucher.voucher_number}
  • Amount Paid   : ₹{voucher.amount}
  • Valid Till    : {voucher.expiry_date.strftime('%d %B %Y')}
  • Status        : ✅ Active

🎊 LUCKY DRAW: Log in now to scratch your reward card!
👉 https://urrbanholidays.in/vouchers/detail/{voucher.voucher_number}/

You could win:
💰 Cashback ₹150-250 | 🎡 Wonderla Ticket | 🥇 Gold | ✈️ Free Trip | 🎧 Headset | ⌚ Watch

Team Urban Holidays ✈️
📧 support@urrbanholidays.in
""",
        to_email=user.email,
    )


# ── Membership Rejected ───────────────────────────────────────────
def send_membership_rejected_email(voucher):
    user = voucher.user
    name = user.get_full_name() or user.username
    _send(
        subject="❌ Payment Verification Failed – Urban Holidays",
        message=f"""Hi {name},

We could not verify your payment for membership {voucher.voucher_number}.

UTR Submitted: {voucher.utr_number}

If you have already paid, please contact us immediately:
📧 support@urrbanholidays.in
📞 WhatsApp: +91 9019852352

We will resolve this within 24 hours.

Team Urban Holidays ✈️
""",
        to_email=user.email,
    )


# ── Redemption Approved ───────────────────────────────────────────
def send_redemption_approved_email(redemption):
    user = redemption.voucher.user
    name = user.get_full_name() or user.username
    _send(
        subject="✅ Trip Confirmed! Your Redemption is Approved!",
        message=f"""Hi {name}!

Your redemption request has been APPROVED! 🎊

📋 Details:
  • Membership  : {redemption.voucher.voucher_number}
  • Travel Date : {redemption.travel_date or 'TBD'}
  • Persons     : {redemption.number_of_persons}

Our team will contact you within 24 hours with trip details.

Enjoy your trip! ✈️
Team Urban Holidays
📧 support@urrbanholidays.in
""",
        to_email=user.email,
    )


# ── Redemption Rejected ───────────────────────────────────────────
def send_redemption_rejected_email(redemption):
    user = redemption.voucher.user
    name = user.get_full_name() or user.username
    _send(
        subject="Update on Your Redemption Request – Urban Holidays",
        message=f"""Hi {name},

We're sorry, your redemption request could not be approved at this time.

Reason: {redemption.admin_notes or 'Please contact support for details.'}

Please contact us:
📧 support@urrbanholidays.in
📞 WhatsApp: +91 9019852352

Team Urban Holidays ✈️
""",
        to_email=user.email,
    )
