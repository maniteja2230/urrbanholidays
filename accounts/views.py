"""
Accounts app views – Registration, Login, Logout, Profile
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction

from .forms import UserRegistrationForm, UserLoginForm, ProfileUpdateForm
from .models import Profile, Referral


def register(request):
    """User registration with referral support"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    # Pre-fill referral code from URL
    ref_code = request.GET.get('ref', '')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()

                # Profile is created via signal, update phone
                profile = user.profile
                profile.phone = form.cleaned_data['phone']

                # Handle referral
                referral_code = form.cleaned_data.get('referral_code')
                if referral_code:
                    try:
                        referrer_profile = Profile.objects.get(referral_code=referral_code)
                        profile.referred_by = referrer_profile

                        # Create referral record
                        referral = Referral.objects.create(
                            referrer=referrer_profile,
                            referee=profile,
                            bonus_amount=settings.REFERRAL_BONUS,
                        )
                        # Credit bonus immediately
                        referral.credit_bonus()

                        # Notify referrer
                        from notifications.models import Notification
                        Notification.objects.create(
                            user=referrer_profile.user,
                            title='Referral Bonus Credited!',
                            message=f'₹{settings.REFERRAL_BONUS} has been credited to your wallet for referring {user.get_full_name() or user.username}.',
                            notification_type='referral',
                        )
                    except Profile.DoesNotExist:
                        pass

                profile.save()

            login(request, user)
            messages.success(
                request,
                f'Welcome to Urban Holidays, {user.first_name}! Your account has been created successfully.'
            )
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm(initial={'referral_code': ref_code})

    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Allow login with email too
            if '@' in username:
                try:
                    user_obj = User.objects.get(email=username)
                    username = user_obj.username
                except User.DoesNotExist:
                    pass

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                next_url = request.GET.get('next', 'dashboard:index')
                return redirect(next_url)
        messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = UserLoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def user_logout(request):
    """Logout user"""
    logout(request)
    messages.info(request, 'You have been logged out. Visit again!')
    return redirect('core:home')


@login_required
def profile(request):
    """User profile view and update"""
    user_profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=user_profile
        )
        if form.is_valid():
            # Update User fields
            request.user.first_name = form.cleaned_data.get('first_name', request.user.first_name)
            request.user.last_name = form.cleaned_data.get('last_name', request.user.last_name)
            request.user.email = form.cleaned_data.get('email', request.user.email)
            request.user.save()

            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = ProfileUpdateForm(instance=user_profile, initial=initial_data)

    context = {
        'form': form,
        'profile': user_profile,
    }
    return render(request, 'accounts/profile.html', context)
