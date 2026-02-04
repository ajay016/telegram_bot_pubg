from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline
from django.contrib import messages



@admin.register(TelegramUser)
class TelegramUserAdmin(ModelAdmin):
    list_display = (
        'id', 'telegram_id', 'username', 'first_name', 'last_name',
        'status_display', 'created_at'
    )
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    ordering = ('-created_at',)

    @admin.display(description='Status', ordering='created_at')
    def status_display(self, obj):
        return "🔴 Blocked" if obj.is_blocked else "🟢 Active"

class SubCategoryInline(TabularInline):
    model = SubCategory
    extra = 0
    fields = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryInline]

@admin.register(SubCategory)
class SubCategoryAdmin(ModelAdmin):
    list_display = ('name', 'category', 'is_active')
    list_filter  = ('category', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    
@admin.register(RechargeCategory)
class RechargeCategoryAdmin(ModelAdmin):
    list_display = ('name', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = (
        'name', 'get_category', 'get_subcategory', 'price', 'in_stock', 'stock_quantity'
    )
    list_filter  = ('in_stock', 'category', 'subcategory')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def get_category(self, obj):
        return obj.category.name if obj.category else '-'
    get_category.short_description = 'Category'

    def get_subcategory(self, obj):
        return obj.subcategory.name if obj.subcategory else '-'
    get_subcategory.short_description = 'Subcategory'
    

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price',)
    autocomplete_fields = ('product', 'voucher_code')

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'user', 'pubg_id', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__telegram_id', 'user__username', 'items__voucher_code__code')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    autocomplete_fields = ('user',)
    

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'pubg_id', 'voucher_code')
    list_filter = ('product',)
    search_fields = ('order__id', 'product__name', 'voucher_code__code')
    autocomplete_fields = ('order', 'product', 'voucher_code')


@admin.register(VoucherCode)
class VoucherCodeAdmin(ModelAdmin):
    list_display = ('code', 'product', 'usage_status', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('code',)
    autocomplete_fields = ('product',)

    def usage_status(self, obj):
        return "🔴 Used" if obj.is_used else "🟢 Available"
    usage_status.short_description = "Status"


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_user', 'balance', 'created_at', 'updated_at')
    search_fields = (
        'telegram_user__username',
        'telegram_user__telegram_id',
        'telegram_user__first_name',
        'telegram_user__last_name',
    )
    ordering = ('-id',)
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('telegram_user',)
    

@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    list_display = ('name', 'uid', 'is_active', 'address', 'api_base_url')
    list_filter = ('is_active',)
    search_fields = ('name', 'address', 'note')
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'uid', 'description', 'note', 'is_active')
        }),
        ('Connection Details', {
            'fields': ('address', 'api_base_url'),
            'classes': ('collapse',),  # collapsible section
        }),
    )
    
    

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'wallet',
        'payment_method',
        'topup_transaction',
        'amount',
        'status',
        'transaction_id',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'user__telegram_id',
        'user__username',
        'wallet__telegram_user__telegram_id',
        'payment_method__name',
        'topup_transaction__note',
        'transaction_id',
        'tx_id',
    )
    list_filter = ('status', 'payment_method')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'transaction_id')
    list_select_related = ('user', 'wallet', 'payment_method', 'topup_transaction')


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('id', 'user', 'payment_method', 'note', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('note', 'user__username', 'payment_method__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(BinancePayNote)
class BinancePayNoteAdmin(ModelAdmin):
    list_display = ('id', 'note', 'user', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('note', 'user__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Suppliers.
    """
    list_display = ('name', 'contact_name', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_name', 'email', 'phone')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    # Organize fields into sections for better readability
    fieldsets = (
        ('Company Info', {
            'fields': ('name', 'is_active')
        }),
        ('Contact Details', {
            'fields': ('contact_name', 'phone', 'email')
        }),
        ('Additional Info', {
            'fields': ('note', 'created_at', 'updated_at'),
            'classes': ('collapse',)  # Hide this section by default
        }),
    )


@admin.register(UploadVoucherCode)
class UploadVoucherCodeAdmin(admin.ModelAdmin):
    """
    Admin interface for uploading vouchers, linked with Suppliers.
    """
    list_display = ('product', 'supplier', 'file', 'uploaded_at')
    list_filter = ('uploaded_at', 'supplier', 'product')
    search_fields = ('product__name', 'supplier__name', 'file')
    date_hierarchy = 'uploaded_at'
    
    # Use autocomplete if you have many suppliers/products
    # (Requires search_fields to be set on SupplierAdmin and ProductAdmin)
    autocomplete_fields = ['supplier', 'product'] 

    def save_model(self, request, obj, form, change):
        """
        Override save to ensure the file processing logic runs
        when a new file is uploaded via Admin.
        """
        super().save_model(request, obj, form, change)
        # Trigger the file processing logic defined in your model
        try:
            obj.process_file()
        except Exception as e:
            # You might want to handle user messaging here using Django messages
            self.message_user(request, f"Error processing file: {e}", level=messages.ERROR)
            
            
@admin.register(AdminChatID)
class AdminChatIDAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "username", "name")
    search_fields = ("chat_id", "username", "name")
    fieldsets = (
        (None, {
            "fields": ("chat_id", "username", "name")
        }),
    )
    
    
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "has_image", "has_attachment", "show_from", "show_until", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "message")
    ordering = ("-created_at",)
    
    fields = (
        "title",
        "message",
        "image",
        "attachment",
        "is_active",
        ("show_from", "show_until"),
    )
    
    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True

    def has_attachment(self, obj):
        return bool(obj.attachment)
    has_attachment.boolean = True

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)