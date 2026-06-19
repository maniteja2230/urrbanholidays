"""
Vouchers app admin configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Voucher, Coupon, Redemption


class CouponInline(admin.StackedInline):
    model = Coupon
    extra = 0
    readonly_fields = ['coupon_code', 'is_used', 'used_at', 'created_at']


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ['voucher_number', 'user', 'amount', 'status',
                    'purchase_date', 'expiry_date', 'qr_preview']
    list_filter = ['status', 'purchase_date', 'expiry_date']
    search_fields = ['voucher_number', 'user__username', 'user__email']
    readonly_fields = ['voucher_number', 'qr_code', 'purchase_date', 'created_at']
    inlines = [CouponInline]

    actions = ['generate_qr_codes', 'mark_expired']

    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50">', obj.qr_code.url)
        return '-'
    qr_preview.short_description = 'QR Code'

    def generate_qr_codes(self, request, queryset):
        count = 0
        for voucher in queryset:
            if not voucher.qr_code:
                voucher.generate_qr()
                count += 1
        self.message_user(request, f'{count} QR code(s) generated.')
    generate_qr_codes.short_description = 'Generate QR codes'

    def mark_expired(self, request, queryset):
        count = queryset.filter(status='active').update(status='expired')
        self.message_user(request, f'{count} voucher(s) marked as expired.')
    mark_expired.short_description = 'Mark as expired'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['coupon_code', 'voucher', 'is_used', 'used_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['coupon_code', 'voucher__voucher_number']
    readonly_fields = ['coupon_code', 'voucher', 'created_at']


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'voucher', 'package', 'status', 'submitted_at',
                    'reviewed_by', 'reviewed_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['voucher__voucher_number', 'voucher__user__username']
    readonly_fields = ['voucher', 'submitted_at']

    actions = ['approve_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        count = 0
        for redemption in queryset.filter(status='pending'):
            redemption.approve(admin_user=request.user, notes='Approved by admin.')
            count += 1
        self.message_user(request, f'{count} redemption(s) approved.')
    approve_requests.short_description = 'Approve selected redemptions'

    def reject_requests(self, request, queryset):
        count = 0
        for redemption in queryset.filter(status='pending'):
            redemption.reject(admin_user=request.user, notes='Rejected by admin.')
            count += 1
        self.message_user(request, f'{count} redemption(s) rejected.')
    reject_requests.short_description = 'Reject selected redemptions'
