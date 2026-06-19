"""
Payments app admin configuration
"""

from django.contrib import admin
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['razorpay_order_id', 'user', 'amount', 'currency',
                    'status', 'payment_method', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['razorpay_order_id', 'razorpay_payment_id',
                     'user__username', 'user__email']
    readonly_fields = ['razorpay_order_id', 'razorpay_payment_id',
                       'razorpay_signature', 'user', 'amount', 'currency',
                       'notes', 'created_at', 'updated_at']
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
