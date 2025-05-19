from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from django.utils.crypto import get_random_string



# class Product(models.Model):
#     name = models.CharField(max_length=200)
#     parent = models.ForeignKey(
#         'self', null=True, blank=True,
#         related_name='children', on_delete=models.CASCADE
#     )
#     # The amount of items or units this product represents (e.g., 26 UC per pack)
#     unit_quantity = models.PositiveIntegerField(
#         default=1,
#         help_text="Number of underlying units per purchase unit"
#     )
#     # Price per this product (for the specified unit_quantity)
#     price = models.DecimalField(
#         max_digits=10, decimal_places=2,
#         help_text="Price for the defined unit_quantity"
#     )
#     # Available stock in terms of purchase units
#     stock = models.PositiveIntegerField(
#         default=0,
#         help_text="Quantity of purchase units available for sale"
#     )

#     def is_leaf(self):
#         """
#         A product is a leaf if it has no children and has a price defined.
#         """
#         return not self.children.exists() and self.price is not


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)  # User ID from Telegram
    username = models.CharField(max_length=150, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    is_bot = models.BooleanField(default=False)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.telegram_id} ({self.username})"


class Category(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    category    = models.ForeignKey(
        Category,
        related_name='subcategories',
        on_delete=models.CASCADE
    )
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} → {self.name}"

class Product(models.Model):
    name           = models.CharField(max_length=200)
    slug           = models.SlugField(unique=True)
    description    = models.TextField(blank=True)
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    in_stock       = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)

    # Relationship: either category or subcategory must be set (but not both)
    category    = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        related_name='products',
        on_delete=models.SET_NULL
    )
    subcategory = models.ForeignKey(
        SubCategory,
        null=True,
        blank=True,
        related_name='products',
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        # Ensure product belongs to either category or subcategory
        if not self.category and not self.subcategory:
            raise ValidationError('Product must have a category or subcategory.')
        if self.category and self.subcategory:
            raise ValidationError('Product cannot have both category and subcategory.')
    


class Wallet(models.Model):
    telegram_user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()  # Manually update timestamp
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Wallet of {self.telegram_user}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending',   'Pending'),
        ('Completed', 'Completed'),
        ('Rejected',  'Rejected'),
    ]
    user        = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} — {self.status}"
    
    
class VoucherCode(models.Model):
    code       = models.CharField(max_length=50, unique=True)
    product    = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='vouchers')
    is_used    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({'used' if self.is_used else 'available'})"
    

class OrderItem(models.Model):
    order        = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product      = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity     = models.PositiveIntegerField()
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)
    voucher_code = models.ForeignKey(
        VoucherCode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="If this order uses a voucher"
    )

    def __str__(self):
        return f"{self.quantity}x{self.product.name} (Order #{self.order.id})"
    
    
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    note = models.TextField(blank=True)  # E.g. “Use memo xyz when sending.”
    address = models.CharField(max_length=255, blank=True)
    api_base_url = models.URLField(blank=True, null=True) 
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class TopUpTransaction(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    note = models.CharField(max_length=64, unique=True, blank=True, null=True)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=30)
    
    
class PaymentTransaction(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.CASCADE)
    topup_transaction = models.ForeignKey(TopUpTransaction, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    note = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('expired', 'Expired')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.created_at + timedelta(minutes=30) < timezone.now()
    

class BinancePayNote(models.Model):
    note = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey('TelegramUser', on_delete=models.CASCADE)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.note
    
