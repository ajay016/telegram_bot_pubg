from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline



@admin.register(TelegramUser)
class TelegramUserAdmin(ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'first_name', 'last_name', 'created_at')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    ordering = ('-created_at',)

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
    list_display = ('id', 'user', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__telegram_id', 'user__username')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    autocomplete_fields = ('user',)
    

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'voucher_code')
    list_filter = ('product',)
    search_fields = ('order__id', 'product__name')
    autocomplete_fields = ('order', 'product', 'voucher_code')


@admin.register(VoucherCode)
class VoucherCodeAdmin(ModelAdmin):
    list_display = ('code', 'product', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('code',)
    autocomplete_fields = ('product',)


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ('id', 'telegram_user', 'balance')
    search_fields = ('telegram_user__username', 'telegram_user__user_id')
    ordering = ('-id',)
    

@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    list_display = ('name', 'is_active', 'address', 'api_base_url')
    list_filter = ('is_active',)
    search_fields = ('name', 'address', 'note')
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'note', 'is_active')
        }),
        ('Connection Details', {
            'fields': ('address', 'api_base_url'),
            'classes': ('collapse',),  # collapsible section
        }),
    )
    
    

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = ('id', 'wallet', 'payment_method', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('reference', 'wallet__id', 'payment_method__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(TopUpTransaction)
class TopUpTransactionAdmin(ModelAdmin):
    list_display = ('id', 'user', 'payment_method', 'note', 'amount_received', 'status', 'created_at')
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


@admin.register(UploadVoucherCode)
class UploadVoucherCodeAdmin(admin.ModelAdmin):
    list_display = ('product', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            obj.process_file()
        except Exception as e:
            self.message_user(request, f"Error: {str(e)}", level='error')
        else:
            self.message_user(request, "Voucher codes uploaded successfully.")