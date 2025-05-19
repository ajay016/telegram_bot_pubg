from rest_framework import serializers
from core.models import *

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description',
            'price', 'in_stock', 'stock_quantity',
            'category', 'subcategory'
        ]

class SubCategorySerializer(serializers.ModelSerializer):
    # include its products, read‑only
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = SubCategory
        fields = [
            'id', 'name', 'slug', 'description',
            'is_active', 'category', 'products'
        ]

class CategorySerializer(serializers.ModelSerializer):
    # include both subcategories and products directly under this category
    subcategories = SubCategorySerializer(many=True, read_only=True)
    products      = ProductSerializer(many=True,    read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description',
            'is_active', 'subcategories', 'products'
        ]

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['user', 'balance']

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    class Meta:
        model = Order
        fields = ['id', 'user', 'total_price', 'created_at', 'items']
        

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'description', 'note', 'address', 'api_base_url']