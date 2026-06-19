"""
Payments app models – Razorpay transaction tracking
"""

from django.db import models
from django.contrib.auth.models import User


class PaymentTransaction(models.Model):
    """Track all Razorpay payment transactions"""
    STATUS_CHOICES = [
        ('created', 'Order Created'),
        ('attempted', 'Payment Attempted'),
        ('paid', 'Payment Successful'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=300, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    payment_method = models.CharField(max_length=50, blank=True)
    bank = models.CharField(max_length=100, blank=True)
    wallet = models.CharField(max_length=100, blank=True)

    notes = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_description = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'

    def __str__(self):
        return f"{self.razorpay_order_id} – {self.status} – ₹{self.amount}"

    @property
    def is_paid(self):
        return self.status == 'paid'
