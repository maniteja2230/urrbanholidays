"""
Vouchers app URL patterns
"""

from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    path('buy/', views.buy_voucher, name='buy'),
    path('success/<str:voucher_number>/', views.voucher_success, name='success'),
    path('detail/<str:voucher_number>/', views.voucher_detail, name='detail'),
    path('redeem/<str:voucher_number>/', views.redeem_voucher, name='redeem'),
    path('download/<str:voucher_number>/', views.download_voucher_pdf, name='download'),
]
