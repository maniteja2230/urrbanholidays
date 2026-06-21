import uuid
import string
import random
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings


# ── Reward System ─────────────────────────────────────────────────
REWARD_CHOICES = [
    ('cashback',        '💰 Cashback'),
    ('wonderla',        '🎡 Wonderla Ticket'),
    ('gold',            '🥇 Gold Gift'),
    ('silver',          '🥈 Silver Gift'),
    ('trip',            '✈️ Trip (500 Days + Free Accommodation + Activities)'),
    ('boat_headset',    '🎧 Boat Headset'),
    ('digital_watch',   '⌚ Digital Watch'),
]

# Weighted probability (higher = more common)
REWARD_WEIGHTS = {
    'cashback':       40,   # Most common
    'boat_headset':   18,
    'digital_watch':  18,
    'wonderla':       10,
    'silver':          8,
    'gold':            4,
    'trip':            2,   # Rarest
}


def assign_random_reward():
    """Pick a random reward based on weighted probability"""
    rewards  = list(REWARD_WEIGHTS.keys())
    weights  = [REWARD_WEIGHTS[r] for r in rewards]
    return random.choices(rewards, weights=weights, k=1)[0]


def get_cashback_amount():
    """Random cashback between ₹150 and ₹250 (multiples of 50)"""
    return random.choice(range(150, 300, 50))  # 150, 200, 250


def generate_voucher_number():
    """Generate unique 12-character voucher number"""
    return 'UH' + ''.join(random.choices(string.digits, k=10))


def generate_coupon_code():
    """Generate unique 10-character coupon code"""
    chars = string.ascii_uppercase + string.digits
    return 'URBAN-' + ''.join(random.choices(chars, k=6))


class Voucher(models.Model):
    """Main voucher model"""
    STATUS_CHOICES = [
        ('pending_payment', 'Pending Payment Verification'),
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='vouchers'
    )
    voucher_number = models.CharField(
        max_length=20, unique=True,
        default=generate_voucher_number
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # QR Code
    qr_code = models.ImageField(upload_to='vouchers/qr_codes/', blank=True, null=True)

    # Dates
    purchase_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()

    # Payment reference
    payment_transaction = models.OneToOneField(
        'payments.PaymentTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='voucher'
    )

    # Paytm / Manual UPI payment
    utr_number = models.CharField(
        max_length=50, blank=True,
        help_text='UPI Transaction / UTR number submitted by customer'
    )
    payment_screenshot = models.ImageField(
        upload_to='vouchers/payment_proofs/',
        blank=True, null=True,
        help_text='Payment screenshot uploaded by customer'
    )
    payment_method = models.CharField(
        max_length=30, default='paytm_qr',
        help_text='paytm_qr / razorpay / manual'
    )

    # Lucky Draw Reward
    reward_type = models.CharField(
        max_length=30, choices=REWARD_CHOICES,
        blank=True, default='',
        help_text='Randomly assigned reward'
    )
    reward_detail = models.CharField(
        max_length=200, blank=True,
        help_text='Extra detail e.g. cashback amount'
    )
    reward_revealed = models.BooleanField(
        default=False,
        help_text='Has the user revealed/seen their reward?'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Voucher'
        verbose_name_plural = 'Vouchers'

    def __str__(self):
        return f"{self.voucher_number} – {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            from datetime import timedelta
            days = getattr(settings, 'VOUCHER_VALIDITY_DAYS', 365)
            self.expiry_date = timezone.now() + timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_date

    @property
    def days_remaining(self):
        if self.is_expired:
            return 0
        return (self.expiry_date - timezone.now()).days

    def generate_qr(self):
        """Generate QR code for this voucher"""
        import qrcode
        import io
        from django.core.files import File

        qr_data = f"Urban Holidays Voucher\nVoucher No: {self.voucher_number}\nAmount: ₹{self.amount}\nExpiry: {self.expiry_date.strftime('%d/%m/%Y')}\nStatus: {self.status}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#0A2463', back_color='white')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f'qr_{self.voucher_number}.png'
        self.qr_code.save(filename, File(buffer), save=True)
        buffer.close()


class Coupon(models.Model):
    """Unique coupon codes attached to vouchers"""
    voucher = models.OneToOneField(
        Voucher, on_delete=models.CASCADE,
        related_name='coupon'
    )
    coupon_code = models.CharField(
        max_length=20, unique=True,
        default=generate_coupon_code
    )
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'

    def __str__(self):
        return f"{self.coupon_code} ({'Used' if self.is_used else 'Active'})"

    def mark_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save()


class Redemption(models.Model):
    """Voucher redemption requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    voucher = models.ForeignKey(
        Voucher, on_delete=models.CASCADE,
        related_name='redemptions'
    )
    package = models.ForeignKey(
        'packages.TravelPackage',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='redemptions'
    )
    travel_date = models.DateField(null=True, blank=True)
    number_of_persons = models.PositiveSmallIntegerField(default=1)
    special_requests = models.TextField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_redemptions'
    )

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Redemption Request'
        verbose_name_plural = 'Redemption Requests'

    def __str__(self):
        return f"Redemption #{self.id} – {self.voucher.voucher_number}"

    def approve(self, admin_user, notes=''):
        self.status = 'approved'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        self.admin_notes = notes
        self.voucher.status = 'used'
        self.voucher.save()
        if hasattr(self.voucher, 'coupon'):
            self.voucher.coupon.mark_used()
        self.save()

        # Send notification
        from notifications.models import Notification
        Notification.objects.create(
            user=self.voucher.user,
            title='Redemption Approved! 🎉',
            message=f'Your redemption request for voucher {self.voucher.voucher_number} has been approved. Enjoy your trip!',
            notification_type='redemption',
        )

    def reject(self, admin_user, notes=''):
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = admin_user
        self.admin_notes = notes
        self.save()

        from notifications.models import Notification
        Notification.objects.create(
            user=self.voucher.user,
            title='Redemption Update',
            message=f'Your redemption request for voucher {self.voucher.voucher_number} was not approved. Reason: {notes or "Please contact support."}',
            notification_type='redemption',
        )
