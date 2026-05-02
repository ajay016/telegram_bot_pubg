from django.contrib import admin
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('view-dashboard', views.dashboard, name='dashboard'),
    
    # Vouchers
    path('vouchers/upload/', views.upload_voucher_view, name='upload_vouchers'), # You already have this
    path('vouchers/uploads/', views.list_voucher_uploads_view, name='list_voucher_uploads'),
    path('vouchers/uploads/<int:pk>/', views.voucher_upload_detail_view, name='view_voucher_upload_detail'),
    path('vouchers/uploads/<int:pk>/delete/', views.delete_voucher_upload_view, name='delete_voucher_upload'),
    path('vouchers/codes/delete/', views.delete_voucher_codes_view, name='delete_voucher_codes'),
    
    # Customers
    path('customers/balances/', views.customer_balances_view, name='customer_balances'),
    path('customers/balances/data/', views.customer_balances_data, name='customer_balances_data'),
    path('customers/<int:pk>/summary/', views.customer_summary_view, name='customer_summary'),
    path('customers/<int:pk>/edit/', views.edit_customer_view, name='edit_customer'),
    path('customers/<int:pk>/delete/', views.delete_customer_view, name='delete_customer'),
]
