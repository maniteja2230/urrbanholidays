"""
Accounts app models – User Profile, Referral Program
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


def generate_referral_code():
    """Generate unique 8-character referral code"""
    return str(uuid.uuid4()).replace('-', '').upper()[:8]


class Profile(models.Model):
    """Extended user profile with referral and wallet"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('', 'Prefer not to say'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # Referral system
    referral_code = models.CharField(
        max_length=20, unique=True,
        default=generate_referral_code,
        editable=False
    )
    referred_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='referrals'
    )

    # Wallet
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Status
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} Profile"

    def get_referral_link(self):
        from django.conf import settings
        return f"{settings.SITE_URL}/accounts/register/?ref={self.referral_code}"

    @property
    def total_referrals(self):
        return self.referrals.count()

    @property
    def total_vouchers(self):
        return self.user.vouchers.count()


class Referral(models.Model):
    """Track referrals and bonuses"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('credited', 'Credited'),
        ('expired', 'Expired'),
    ]

    referrer = models.ForeignKey(
        Profile, on_delete=models.CASCADE,
        related_name='sent_referrals'
    )
    referee = models.ForeignKey(
        Profile, on_delete=models.CASCADE,
        related_name='received_referrals'
    )
    bonus_amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    credited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Referral'
        verbose_name_plural = 'Referrals'
        unique_together = ('referrer', 'referee')

    def __str__(self):
        return f"{self.referrer.user.username} → {self.referee.user.username}"

    def credit_bonus(self):
        """Credit referral bonus to referrer wallet"""
        if self.status == 'pending':
            self.referrer.wallet_balance += self.bonus_amount
            self.referrer.save(update_fields=['wallet_balance'])
            self.status = 'credited'
            self.credited_at = timezone.now()
            self.save(update_fields=['status', 'credited_at'])


class WalletTransaction(models.Model):
    """Track wallet credits and debits"""
    TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    SOURCE_CHOICES = [
        ('referral', 'Referral Bonus'),
        ('voucher', 'Voucher Purchase'),
        ('refund', 'Refund'),
        ('admin', 'Admin Credit'),
        ('redemption', 'Redemption'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='wallet_transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'

    def __str__(self):
        return f"{self.profile.user.username} - {self.transaction_type} ₹{self.amount}"
