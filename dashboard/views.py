"""
Dashboard app views – User Dashboard
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone

from vouchers.models import Voucher, Redemption
from payments.models import PaymentTransaction
from accounts.models import Referral
from notifications.models import Notification


@login_required
def dashboard_index(request):
    """Main dashboard overview"""
    user = request.user
    profile = user.profile

    vouchers = Voucher.objects.filter(user=user)
    active_vouchers = vouchers.filter(status='active')
    used_vouchers = vouchers.filter(status='used')
    expired_vouchers = vouchers.filter(status='expired')
    pending_redemptions = Redemption.objects.filter(
        voucher__user=user, status='pending'
    ).count()

    recent_transactions = PaymentTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    unread_notifications = Notification.objects.filter(
        user=user, is_read=False
    ).count()

    recent_notifications = Notification.objects.filter(user=user)[:5]

    # Referral stats
    total_referrals = Referral.objects.filter(referrer=profile).count()
    credited_referrals = Referral.objects.filter(referrer=profile, status='credited').count()
    referral_earnings = Referral.objects.filter(
        referrer=profile, status='credited'
    ).aggregate(total=Sum('bonus_amount'))['total'] or 0

    context = {
        'profile': profile,
        'total_vouchers': vouchers.count(),
        'active_vouchers': active_vouchers.count(),
        'used_vouchers': used_vouchers.count(),
        'expired_vouchers': expired_vouchers.count(),
        'pending_redemptions': pending_redemptions,
        'wallet_balance': profile.wallet_balance,
        'recent_transactions': recent_transactions,
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        'total_referrals': total_referrals,
        'credited_referrals': credited_referrals,
        'referral_earnings': referral_earnings,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def my_vouchers(request):
    """User's voucher wallet"""
    vouchers = Voucher.objects.filter(user=request.user).select_related('coupon')

    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        vouchers = vouchers.filter(status=status_filter)

    context = {
        'vouchers': vouchers,
        'status_filter': status_filter,
        'active_count': Voucher.objects.filter(user=request.user, status='active').count(),
        'used_count': Voucher.objects.filter(user=request.user, status='used').count(),
        'expired_count': Voucher.objects.filter(user=request.user, status='expired').count(),
    }
    return render(request, 'dashboard/my_vouchers.html', context)


@login_required
def transaction_history(request):
    """Payment and wallet transaction history"""
    transactions = PaymentTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')

    total_spent = PaymentTransaction.objects.filter(
        user=request.user, status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'transactions': transactions,
        'total_spent': total_spent,
    }
    return render(request, 'dashboard/transactions.html', context)


@login_required
def referrals(request):
    """Referral program page"""
    profile = request.user.profile
    referral_list = Referral.objects.filter(
        referrer=profile
    ).select_related('referee__user').order_by('-created_at')

    context = {
        'profile': profile,
        'referrals': referral_list,
        'total_earned': referral_list.filter(
            status='credited'
        ).aggregate(total=Sum('bonus_amount'))['total'] or 0,
    }
    return render(request, 'dashboard/referrals.html', context)
