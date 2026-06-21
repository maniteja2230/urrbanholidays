from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    path('buy/', views.buy_voucher, name='buy'),
    path('pending/<str:voucher_number>/', views.payment_pending, name='payment_pending'),
    path('success/<str:voucher_number>/', views.voucher_success, name='success'),
    path('detail/<str:voucher_number>/', views.voucher_detail, name='detail'),
    path('redeem/<str:voucher_number>/', views.redeem_voucher, name='redeem'),
    path('download/<str:voucher_number>/', views.download_voucher_pdf, name='download'),
    path('reveal/<str:voucher_number>/', views.reveal_reward, name='reveal_reward'),
]
