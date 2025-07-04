from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError



class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)  # User ID from Telegram
    username = models.CharField(max_length=150, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    is_blocked = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.telegram_id}"


class Category(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['created_at']

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
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.category.name} → {self.name}"
    

class RechargeCategory(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Recharge Categories'
        ordering = ['created_at']

    def __str__(self):
        return self.name

# class RechargeSubCategory(models.Model):
#     category    = models.ForeignKey(
#         Category,
#         related_name='subcategories',
#         on_delete=models.CASCADE
#     )
#     name        = models.CharField(max_length=200)
#     slug        = models.SlugField(unique=True)
#     description = models.TextField(blank=True)
#     is_active   = models.BooleanField(default=True)

#     class Meta:
#         unique_together = ('category', 'name')
#         ordering = ['name']

#     def __str__(self):
#         return f"{self.category.name} → {self.name}"


class Product(models.Model):
    name           = models.CharField(max_length=200)
    slug           = models.SlugField(unique=True)
    description    = models.TextField(blank=True)
    recharge_description = models.TextField(blank=True)
    price          = models.DecimalField(max_digits=10, decimal_places=3)
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
    
    recharge_category    = models.ForeignKey(
        RechargeCategory,
        null=True,
        blank=True,
        related_name='products',
        on_delete=models.SET_NULL
    )
    
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.name

    def clean(self):
        # Ensure product belongs to either category or subcategory or recharge category
        if not self.category and not self.subcategory and not self.recharge_category:
            raise ValidationError('Product must have a category or subcategory or a recharge category.')

        if self.category and self.subcategory:
            raise ValidationError('Product cannot have both category and subcategory.')

        # Conditional requirement for recharge_description
        if self.recharge_category:
            if self.recharge_description:
                raise ValidationError('Recharge products must not have a recharge description.')
        else:
            if not self.recharge_description:
                raise ValidationError('Non-recharge products must have a recharge description.')
            
    
    def update_stock_from_vouchers(self):
        count = self.vouchers.filter(is_used=False).count()
        self.stock_quantity = count
        self.in_stock = count > 0
        self.save(update_fields=['stock_quantity', 'in_stock'])
    


class Wallet(models.Model):
    telegram_user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
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
    total_price = models.DecimalField(max_digits=12, decimal_places=3)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at  = models.DateTimeField(auto_now_add=True)
    pubg_id    = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} — {self.status}"
    
    
class VoucherCode(models.Model):
    code       = models.CharField(max_length=50, unique=True)
    product    = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='vouchers')
    is_used    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({'used' if self.is_used else 'available'})"
    

class UploadVoucherCode(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    file = models.FileField(upload_to='voucher_uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Optional: validate the file before saving
        if not self.file.name.endswith(('.txt',)):
            raise ValidationError("Only .txt files are allowed.")

    def process_file(self):
        # Read the file and create voucher codes
        self.file.seek(0)
        lines = self.file.read().decode('utf-8').splitlines()

        valid_lines = []
        for line in lines:
            code = line.strip()
            if code and code.isalnum():
                valid_lines.append(code)
            else:
                raise ValidationError(f"Invalid code format: '{line}'")

        # Save voucher codes
        for code in valid_lines:
            VoucherCode.objects.get_or_create(code=code, product=self.product)
            
        self.product.update_stock_from_vouchers()  # Update stock after processing
    

class OrderItem(models.Model):
    order        = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product      = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity     = models.PositiveIntegerField()
    unit_price   = models.DecimalField(max_digits=10, decimal_places=3)
    pubg_id    = models.CharField(max_length=20, blank=True, null=True)
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
    uid = models.CharField(max_length=100, blank=True, null=True)
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
    amount_received = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed')], default='pending')
    tx_id = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=60)
    
    
class PaymentTransaction(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.CASCADE)
    topup_transaction = models.ForeignKey(TopUpTransaction, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    note = models.CharField(max_length=255, null=True, blank=True)
    tx_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    transaction_id = models.CharField(max_length=30, blank=True, null=True)
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
    


class AdminChatID(models.Model):
    chat_id = models.CharField(max_length=50)
    username = models.CharField(max_length=150, blank=True, null=True)
    name = models.CharField(max_length=150, blank=True, null=True)

    def save(self, *args, **kwargs):
        AdminChatID.objects.all().delete()  # Ensures only one entry exists
        super().save(*args, **kwargs)

    def __str__(self):
        display_name = self.name or self.username or self.chat_id
        return f"{display_name} ({self.chat_id})"