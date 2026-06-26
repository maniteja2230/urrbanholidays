from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Voucher, Coupon, Redemption
from core.email_utils import (
    send_membership_activated_email,
    send_membership_rejected_email,
    send_redemption_approved_email,
    send_redemption_rejected_email,
)


class CouponInline(admin.StackedInline):
    model = Coupon
    extra = 0
    readonly_fields = ['coupon_code', 'is_used', 'used_at', 'created_at']


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = [
        'voucher_number', 'user', 'amount', 'colored_status',
        'utr_number', 'payment_method', 'purchase_date', 'qr_preview'
    ]
    list_filter  = ['status', 'payment_method', 'purchase_date']
    search_fields = ['voucher_number', 'user__username', 'user__email', 'utr_number']
    readonly_fields = [
        'voucher_number', 'qr_code', 'purchase_date',
        'created_at', 'screenshot_preview'
    ]
    inlines = [CouponInline]
    actions = ['approve_payment', 'reject_payment', 'generate_qr_codes', 'mark_expired', 'test_scratch_card']

    fieldsets = (
        ('Voucher Info', {
            'fields': ('voucher_number', 'user', 'amount', 'status', 'expiry_date')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'utr_number', 'payment_screenshot', 'screenshot_preview', 'payment_transaction')
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Timestamps', {
            'fields': ('purchase_date', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    # ── Display helpers ────────────────────────────────────────────────
    def colored_status(self, obj):
        colors = {
            'pending_payment': '#FF8C00',   # orange
            'active':          '#28a745',   # green
            'used':            '#6c757d',   # grey
            'expired':         '#dc3545',   # red
            'cancelled':       '#dc3545',
        }
        color = colors.get(obj.status, '#000')
        return format_html(
            '<b style="color:{}">{}</b>', color, obj.get_status_display()
        )
    colored_status.short_description = 'Status'

    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50">', obj.qr_code.url)
        return '–'
    qr_preview.short_description = 'QR'

    def screenshot_preview(self, obj):
        if obj.payment_screenshot:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px;max-height:200px;border:1px solid #ddd;padding:4px">'
                '</a>', obj.payment_screenshot.url, obj.payment_screenshot.url
            )
        return 'No screenshot uploaded'
    screenshot_preview.short_description = 'Payment Screenshot'

    # ── TEST SCRATCH CARD ────────────────────────────────────────────
    def test_scratch_card(self, request, queryset):
        """Admin test: assign random reward + reset reveal so you can test scratch card"""
        from .models import assign_random_reward, get_reward_detail
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        voucher = queryset.first()
        if not voucher:
            self.message_user(request, 'Select one voucher to test.', level='warning')
            return

        def is_lucky_winner(reward_type):
            """Returns True if this reward shows the LUCKY WINNER banner"""
            return reward_type in ['gold', 'silver']

        def get_reward_detail(reward_type):
            """Return the display text for a given reward type"""
            details = {
                'off_100':       '₹100 Off on Your Next Trip',
                'off_200':       '₹200 Off on Your Next Trip',
                'off_500':       '₹500 Off on Your Next Trip',
                'off_2000':      '₹2000 Off on Your Next Trip',
                'wonderla':      'Wonderla Theme Park Entry Ticket',
                'accommodation': 'Accommodation Free on Your Next Trip',
                'journey':       'Journey Tickets Free on Your Next Trip',
                'silver':        'You Got 10gm of Silver 🥈',
                'gold':          'You Won 1 Gram Gold 🥇',
            }
            return details.get(reward_type, 'Special Reward')

        # Assign random reward
        reward = assign_random_reward()
        voucher.reward_type   = reward
        voucher.reward_revealed = False   # reset so scratch shows
        voucher.status        = 'active'
        voucher.reward_detail = get_reward_detail(reward)

        voucher.save()
        self.message_user(
            request,
            f'🎮 Test scratch card set! Reward: {voucher.reward_detail}. '
            f'Visit /vouchers/detail/{voucher.voucher_number}/ to scratch!'
        )
        # Redirect directly to the scratch card page
        return HttpResponseRedirect(
            f'/vouchers/detail/{voucher.voucher_number}/'
        )
    test_scratch_card.short_description = '🎮 Test Scratch Card (assign random reward)'

    # ── Admin Actions ─────────────────────────────────────────────────
    def approve_payment(self, request, queryset):
        """Approve payments — activate voucher + assign random reward + generate QR"""
        from .models import assign_random_reward, get_reward_detail
        count = 0
        for voucher in queryset.filter(status='pending_payment'):
            reward = assign_random_reward()
            voucher.reward_type   = reward
            voucher.reward_detail = get_reward_detail(reward)

            voucher.status = 'active'
            voucher.save()

            # Generate QR code
            try:
                voucher.generate_qr()
            except Exception:
                pass

            # Create coupon if not exists
            if not hasattr(voucher, 'coupon'):
                Coupon.objects.create(voucher=voucher)

            # Notify user
            reward_label = dict(voucher._meta.get_field('reward_type').choices).get(reward, reward)
            try:
                from notifications.models import Notification
                Notification.objects.create(
                    user=voucher.user,
                    title='🎉 Payment Verified – Scratch Your Lucky Draw!',
                    message=(
                        f'Your payment of ₹{voucher.amount} has been verified! '
                        f'Voucher #{voucher.voucher_number} is now ACTIVE. '
                        f'Login to reveal your LUCKY DRAW reward! 🎊'
                    ),
                    notification_type='voucher',
                )
            except Exception:
                pass
            # Notify user via email
            try:
                send_membership_activated_email(voucher)
            except Exception:
                pass
            count += 1
        self.message_user(request, f'✅ {count} membership(s) approved with lucky draw rewards!')
    approve_payment.short_description = '✅ Approve & Activate (Paytm payment verified)'

    def reject_payment(self, request, queryset):
        """Reject invalid Paytm payments"""
        count = 0
        for voucher in queryset.filter(status='pending_payment'):
            voucher.status = 'cancelled'
            voucher.save()

            try:
                from notifications.models import Notification
                Notification.objects.create(
                    user=voucher.user,
                    title='❌ Payment Verification Failed',
                    message=(
                        f'We could not verify your payment (UTR: {voucher.utr_number}). '
                        f'Please contact support at support@urrbanholidays.in'
                    ),
                    notification_type='voucher',
                )
            except Exception:
                pass

            try:
                send_membership_rejected_email(voucher)
            except Exception:
                pass
            count += 1
        self.message_user(request, f'❌ {count} membership(s) rejected.')
    reject_payment.short_description = '❌ Reject (Payment not verified)'

    def generate_qr_codes(self, request, queryset):
        count = 0
        for voucher in queryset:
            try:
                voucher.generate_qr()
                count += 1
            except Exception:
                pass
        self.message_user(request, f'{count} QR code(s) generated.')
    generate_qr_codes.short_description = 'Generate QR codes'

    def mark_expired(self, request, queryset):
        count = queryset.filter(status='active').update(status='expired')
        self.message_user(request, f'{count} voucher(s) marked as expired.')
    mark_expired.short_description = 'Mark as expired'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ['coupon_code', 'voucher', 'is_used', 'used_at', 'created_at']
    list_filter   = ['is_used', 'created_at']
    search_fields = ['coupon_code', 'voucher__voucher_number']
    readonly_fields = ['coupon_code', 'voucher', 'created_at']


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display  = ['id', 'voucher', 'package', 'status', 'submitted_at', 'reviewed_by']
    list_filter   = ['status', 'submitted_at']
    search_fields = ['voucher__voucher_number', 'voucher__user__username']
    readonly_fields = ['voucher', 'submitted_at']
    actions = ['approve_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        count = 0
        for r in queryset.filter(status='pending'):
            r.approve(admin_user=request.user, notes='Approved by admin.')
            count += 1
        self.message_user(request, f'{count} redemption(s) approved.')
    approve_requests.short_description = 'Approve selected redemptions'

    def reject_requests(self, request, queryset):
        count = 0
        for r in queryset.filter(status='pending'):
            r.reject(admin_user=request.user, notes='Rejected by admin.')
            count += 1
        self.message_user(request, f'{count} redemption(s) rejected.')
    reject_requests.short_description = 'Reject selected redemptions'
