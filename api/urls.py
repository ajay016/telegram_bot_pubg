from django.contrib import admin
from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from . import views


urlpatterns = [
    # Categories
    path('categories/', views.CategoryList.as_view(),   name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetail.as_view(), name='category-detail'),

    # SubCategories
    path('subcategories/', views.SubCategoryList.as_view(),   name='subcategory-list'),
    path('subcategories/<int:pk>/', views.SubCategoryDetail.as_view(), name='subcategory-detail'),

    # Products
    path('products/', views.ProductList.as_view(),   name='product-list'),
    path('products/<int:pk>/', views.ProductDetail.as_view(), name='product-detail'),

    # Wallets
    path('wallets/', views.WalletList.as_view(), name='wallet-list'),
    path('wallets/<int:pk>/', views.WalletDetail.as_view(), name='wallet-detail'),

    # Orders
    path('orders/', views.OrderList.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetail.as_view(), name='order-detail'),
    
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='payment-methods-list'),
    path('payment-methods/<int:id>/', views.PaymentMethodDetailView.as_view(), name='payment-method-detail'),
    
    path("confirm-topup/", views.ConfirmTopUpView.as_view(), name="confirm-topup"),
]
