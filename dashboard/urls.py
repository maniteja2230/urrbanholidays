"""
Dashboard app URL patterns
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('vouchers/', views.my_vouchers, name='my_vouchers'),
    path('transactions/', views.transaction_history, name='transactions'),
    path('referrals/', views.referrals, name='referrals'),
]
