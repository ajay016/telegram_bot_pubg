import code
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
import random
import string



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
    

class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


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

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_uploads'
    )

    file = models.FileField(upload_to='voucher_uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.file.name.endswith(('.txt',)):
            raise ValidationError("Only .txt files are allowed.")

    def process_file(self):
        self.file.seek(0)
        lines = self.file.read().decode('utf-8').splitlines()

        valid_lines = []
        for line in lines:
            code = line.strip()
            if not code:
                continue  # ignore empty lines
            valid_lines.append(code)

        for code in set(valid_lines):
            VoucherCode.objects.get_or_create(code=code, product=self.product)

        self.product.update_stock_from_vouchers()
    

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



class Transaction(models.Model):
    TYPE_CHOICES = [
        ('topup', 'Topup'),
        ('purchase', 'Purchase'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('other', 'Other'),
    ]
    DIRECTION_CHOICES = [
        ('credit', 'Credit'),  # adds to wallet
        ('debit', 'Debit'),    # deducts from wallet
    ]

    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)

    # Optional: used for topups (bank/crypto/stars/etc)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.CASCADE, null=True, blank=True
    )

    # Optional: used for purchase/refund to connect to an Order
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    transaction_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='topup'
    )
    direction = models.CharField(
        max_length=10, choices=DIRECTION_CHOICES, default='credit'
    )

    # Keep amount always positive; direction tells +/- meaning
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    # Keep your existing "note" behavior (you use it for matching deposits)
    note = models.CharField(max_length=64, unique=True, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('failed', 'Failed')],
        default='pending'
    )

    tx_id = models.CharField(max_length=64, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def _make_tx_id(self):
        # prefix based on transaction type
        prefix_map = {
            "topup": "TP",
            "purchase": "PU",
            "refund": "RF",
            "adjustment": "AD",
            "other": "OT",
        }
        prefix = prefix_map.get(getattr(self, "transaction_type", None), "TX")

        dt = self.created_at or timezone.now()
        ts = dt.strftime("%Y%m%d%H%M%S")

        # Prefer PK if available (most unique & stable). If not saved yet, use random.
        if self.pk:
            core = f"{prefix}-{ts}-{self.pk}"
        else:
            rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            core = f"{prefix}-{ts}-{rand}"

        return core


    def save(self, *args, **kwargs):
        # ✅ generate only during create (or when tx_id is empty)
        creating = self._state.adding  # True before first save

        super().save(*args, **kwargs)  # first save so we have pk + created_at

        if creating and not self.tx_id:
            tx_id = self._make_tx_id()

            # ultra-safe uniqueness fallback
            if Transaction.objects.filter(tx_id=tx_id).exists():
                rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                tx_id = f"{tx_id}-{rand}"

            Transaction.objects.filter(pk=self.pk).update(tx_id=tx_id)
            self.tx_id = tx_id

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=60)

    def __str__(self):
        return f"{self.user} | {self.transaction_type} | {self.direction} | {self.amount} | {self.status}"
    
    
class PaymentTransaction(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.CASCADE)
    topup_transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
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
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.transaction_id:
            self.transaction_id = f"{self.id}{timezone.now().strftime('%Y%m%d%H%M%S')}"
            super().save(update_fields=['transaction_id'])

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
    
    

class Announcement(models.Model):
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField()  # what admin writes
    is_active = models.BooleanField(default=True)

    show_from = models.DateTimeField(null=True, blank=True)
    show_until = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_announcements",
    )
    
    image = models.ImageField(upload_to="announcements/images/", null=True, blank=True)
    attachment = models.FileField(upload_to="announcements/files/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_visible_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.show_from and now < self.show_from:
            return False
        if self.show_until and now > self.show_until:
            return False
        return True