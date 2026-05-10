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
    
    # Transaction details
    path('customers/<int:pk>/transactions/', views.user_transactions_view, name='user_transactions'),
    path('customers/<int:pk>/transactions/data/', views.user_transactions_data, name='user_transactions_data'),
    path('transactions/<int:tx_id>/details/', views.transaction_details_view, name='transaction_details'),
    
    #Admin Orders
    path('admin-orders/', views.admin_pending_orders_view, name='admin_pending_orders'),
    path('admin-orders/data/', views.admin_pending_orders_data, name='admin_pending_orders_data'),
    path('admin-orders/<int:order_id>/details/', views.order_details_api, name='order_details_api'),
    path('admin-orders/<int:order_id>/approve/', views.approve_order_api, name='approve_order_api'),
    path('admin-orders/<int:order_id>/reject/', views.reject_order_api, name='reject_order_api'),
    path('admin-orders/<int:order_id>/delete/', views.delete_order_api, name='delete_order_api'),
]
