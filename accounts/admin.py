"""
Accounts app admin – User and Profile management
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Referral, WalletTransaction


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['phone', 'city', 'state', 'referral_code', 'referred_by',
              'wallet_balance', 'is_verified', 'email_verified']
    readonly_fields = ['referral_code']


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name',
                    'is_staff', 'date_joined', 'get_phone', 'get_wallet']

    def get_phone(self, obj):
        try:
            return obj.profile.phone
        except Profile.DoesNotExist:
            return '-'
    get_phone.short_description = 'Phone'

    def get_wallet(self, obj):
        try:
            return f'₹{obj.profile.wallet_balance}'
        except Profile.DoesNotExist:
            return '₹0'
    get_wallet.short_description = 'Wallet'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'state', 'wallet_balance',
                    'is_verified', 'total_referrals', 'created_at']
    list_filter = ['is_verified', 'email_verified', 'state']
    search_fields = ['user__username', 'user__email', 'phone', 'city']
    readonly_fields = ['referral_code', 'created_at', 'updated_at']

    def total_referrals(self, obj):
        return obj.total_referrals
    total_referrals.short_description = 'Referrals'


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referee', 'bonus_amount', 'status', 'created_at', 'credited_at']
    list_filter = ['status', 'created_at']
    search_fields = ['referrer__user__username', 'referee__user__username']
    readonly_fields = ['referrer', 'referee', 'created_at']

    actions = ['credit_referral_bonus']

    def credit_referral_bonus(self, request, queryset):
        count = 0
        for referral in queryset.filter(status='pending'):
            referral.credit_bonus()
            count += 1
        self.message_user(request, f'{count} referral bonus(es) credited successfully.')
    credit_referral_bonus.short_description = 'Credit referral bonus'


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['profile', 'transaction_type', 'source', 'amount',
                    'balance_after', 'description', 'created_at']
    list_filter = ['transaction_type', 'source', 'created_at']
    search_fields = ['profile__user__username', 'description']
    readonly_fields = ['profile', 'transaction_type', 'source', 'amount',
                       'balance_after', 'description', 'created_at']

    def has_add_permission(self, request):
        return False
