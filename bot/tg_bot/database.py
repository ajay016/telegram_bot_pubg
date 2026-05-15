from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db import transaction
from asgiref.sync import sync_to_async
from decimal import Decimal, ROUND_DOWN
from django.db.models import Sum
from datetime import timedelta
from core.models import *
from core.decorators import block_check












@sync_to_async
def get_or_create_telegram_user(user_data):
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=user_data.id,
        defaults={
            "first_name": user_data.first_name or "",
            "last_name": user_data.last_name or "",
            "username": user_data.username or "",
            "is_bot": user_data.is_bot,
        },
    )
    Wallet.objects.get_or_create(telegram_user=user)
    return user



@sync_to_async
def get_wallet_by_telegram_id(telegram_id):
    try:
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        return Wallet.objects.get(telegram_user=user)
    except (TelegramUser.DoesNotExist, Wallet.DoesNotExist):
        return None
    
    
    
@block_check
async def get_user_by_telegram_id(telegram_id: int) -> TelegramUser | None:
    try:
        return await TelegramUser.objects.aget(telegram_id=telegram_id)
    except TelegramUser.DoesNotExist:
        return None
    
    
    
@sync_to_async
def get_all_payment_methods():
    return list(PaymentMethod.objects.filter(is_active=True).values('id', 'name'))



@sync_to_async
def get_categories():
    return list(Category.objects.all().values("id", "name"))



@sync_to_async
def get_categories_pubg():
    # Filters categories to only show active ones that have 'pubg' in the slug
    return list(Category.objects.filter(is_active=True, slug__icontains="pubg").values("id", "name"))



@sync_to_async
def get_recharge_categories():
    return list(RechargeCategory.objects.all().values("id", "name"))



@sync_to_async
def get_products_by_category(category_id):
    return list(Product.objects.filter(category_id=category_id).values('id', 'name', 'price', 'stock_quantity'))



@sync_to_async
def get_product_detail(product_id):
    return Product.objects.filter(id=product_id).values(
        'name', 'description', 'price', 'stock_quantity', 'category'
    ).first()
    
    
    
@sync_to_async
def get_product_and_wallet(user: TelegramUser, product_id: int):
    # Fetch product and user's wallet in one go
    product = Product.objects.get(id=product_id)
    wallet  = Wallet.objects.get(telegram_user=user)
    return product, wallet



@sync_to_async
def get_current_announcement():
    # get latest visible announcement
    qs = Announcement.objects.filter(is_active=True).order_by("-created_at")
    for a in qs[:20]:  # small cap
        if a.is_visible_now():
            return a
    return None



@sync_to_async
def get_wallet_balance(user):
    try:
        return Wallet.objects.get(telegram_user=user)
    except Wallet.DoesNotExist:
        return None
    
    
    
@sync_to_async
def create_topup_transaction(user_id, method_id, note=None):
    user = TelegramUser.objects.get(id=user_id)
    method = PaymentMethod.objects.get(id=method_id)

    return Transaction.objects.create(
        user=user,
        payment_method=method,
        note=note,

        # ✅ NEW FIELDS
        transaction_type="topup",
        direction="credit",

        # keep pending until confirmed
        status="pending",
    )
    
    
    
@sync_to_async
def create_payment_transaction_binance(user_id, method_id, topup_transaction, note):
    user = TelegramUser.objects.get(id=user_id)
    wallet = Wallet.objects.get(telegram_user=user)
    method = PaymentMethod.objects.get(id=method_id)
    PaymentTransaction.objects.create(user=user, payment_method=method, wallet=wallet, topup_transaction=topup_transaction, note=note)
    
    
    
@sync_to_async
def create_payment_transaction(user_id, method_id, amount, topup_id):
    print('user_id in Payment transaction', user_id)
    user = TelegramUser.objects.get(id=user_id)
    wallet = Wallet.objects.get(telegram_user=user)
    return PaymentTransaction.objects.create(
        user_id=user_id,
        wallet=wallet,
        payment_method_id=method_id,
        amount=amount,
        topup_transaction_id=topup_id,
        status="pending"
    )
    
    
    
@sync_to_async
def get_transaction_by_id(transaction_id):
    try:
        return Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        return None
    
    
    
@sync_to_async
def confirm_transaction_and_update_wallet(transaction_id, amount):
    tx = Transaction.objects.get(id=transaction_id)
    tx.status = "confirmed"
    tx.amount = amount
    tx.save()
    
    wallet = Wallet.objects.get(telegram_user=tx.user)
    wallet.balance += amount
    wallet.save()



@sync_to_async
def mark_payment_completed(payment_id):
    PaymentTransaction.objects.filter(id=payment_id).update(status="completed")
    
    
    
@sync_to_async
def mark_topup_completed(topup_id):
    Transaction.objects.filter(id=topup_id).update(status="confirmed")
    
    
    
@sync_to_async
def credit_wallet(user_id, amount):
    wallet = Wallet.objects.get(telegram_user_id=user_id)
    wallet.balance += amount
    wallet.save()
    
    
    
@sync_to_async
def check_binance_for_note(note):
    # Simulate hitting Binance API and checking for memo/note
    # In reality: call actual Binance API with auth headers etc.
    if note.startswith("Xy"):  # Example condition
        return Decimal("10.00")
    return Decimal("0.00")



@sync_to_async
def get_or_create_binance_pay_note():
    # Reuse first available unused and unexpired note
    note_obj = BinancePayNote.objects.filter(is_used=False).order_by("created_at").first()
    if note_obj and (note_obj.created_at + timedelta(minutes=30)) > timezone.now():
        return note_obj.note

    # Generate new unique note
    note = get_random_string(12)
    while BinancePayNote.objects.filter(note=note).exists():
        note = get_random_string(12)

    new_note = BinancePayNote.objects.create(note=note)
    return new_note.note



@sync_to_async
def note_exists(note):
    return BinancePayNote.objects.filter(note=note).exists()



@sync_to_async
def complete_recharge_order_with_vouchers(user, product, wallet, qty, total):
    with transaction.atomic():
        available_vouchers = list(
            VoucherCode.objects.filter(product=product, is_used=False)[:qty]
        )
        if len(available_vouchers) < qty:
            return None, None, None, "no_voucher", None

        wallet.balance -= total
        wallet.save()
        
        product.stock_quantity -= qty
        product.save(update_fields=["stock_quantity"])

        order = Order.objects.create(
            user=user,
            total_price=total,
            status="Completed",
        )
        
        transaction_obj = Transaction.objects.create(
            user=user,
            order=order,
            payment_method=None,
            note=None,
            amount=total,
            transaction_type="purchase",
            direction="debit",
            status="confirmed",
        )

        used_voucher_codes = []

        for i in range(qty):
            voucher = available_vouchers[i]
            voucher.is_used = True
            voucher.save()

            used_voucher_codes.append(voucher.code)

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1,
                unit_price=product.price,
                voucher_code=voucher
            )

        return order, wallet.balance, used_voucher_codes, None, transaction_obj
    
    
    
@sync_to_async
def complete_recharge_without_description(user, product, wallet, qty, total, pubg_id):
    with transaction.atomic():
        wallet.balance -= total
        wallet.save()

        product.stock_quantity -= qty
        product.save()

        order = Order.objects.create(
            user=user,
            total_price=total,
            pubg_id=pubg_id,
            status="Pending"
        )
        
        Transaction.objects.create(
            user=user,
            order=order,
            payment_method=None,
            note=None,
            amount=total,
            transaction_type="purchase",
            direction="debit",
            status="confirmed",
        )

        available_vouchers = list(
            VoucherCode.objects.filter(product=product, is_used=False)[:qty]
        )

        used_voucher_codes = []

        for i in range(qty):
            voucher = available_vouchers[i] if i < len(available_vouchers) else None
            if voucher:
                voucher.is_used = True
                voucher.save()
                used_voucher_codes.append(voucher.code)

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=1,
                unit_price=product.price,
                pubg_id=pubg_id,
                voucher_code=voucher
            )

        return order, wallet.balance, used_voucher_codes
    
    
    
@sync_to_async
def create_order_and_item(user, product, quantity, total_price):
    # Atomic creation of Order + OrderItem
    order = Order.objects.create(
        user=user,
        total_price=total_price
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        unit_price=product.price
    )
    return order



@sync_to_async
def get_payment_methods():
    return list(PaymentMethod.objects.filter(is_active=True).values('id', 'name'))


@sync_to_async
def get_payment_method_info(method_id):
    try:
        method = PaymentMethod.objects.get(id=method_id)
        return {
            "id": method.id,
            'uid': method.uid,
            "name": method.name,
            "description": method.description,
            "address": method.address,
            "api_base_url": method.api_base_url,
        }
    except PaymentMethod.DoesNotExist:
        return None
    
    
    
@sync_to_async
def get_top_buyers(limit=5):
    top_users = Transaction.objects.filter(
        transaction_type='purchase',
        status='confirmed',
        direction='debit'
    ).values(
        'user__telegram_id'
    ).annotate(
        total_spent=Sum('amount')
    ).order_by('-total_spent')[:limit]

    return list(top_users)



# ===================== BEP20 functions =====================
@sync_to_async
def check_bep20_amount_active(amount):
    """Clean up expired locks, then check if amount is taken."""
    cutoff = timezone.now() - timedelta(minutes=22)
    BEP20ActiveAmount.objects.filter(created_at__lt=cutoff).delete()
    return BEP20ActiveAmount.objects.filter(amount=amount).exists()


@sync_to_async
def lock_bep20_amount(user, amount, transaction_obj):
    """Lock an amount for an active BEP20 session."""
    obj, created = BEP20ActiveAmount.objects.get_or_create(
        amount=amount,
        defaults={"user": user, "transaction": transaction_obj},
    )
    return obj, created


@sync_to_async
def release_bep20_amount(amount):
    """Release a locked BEP20 amount."""
    BEP20ActiveAmount.objects.filter(amount=amount).delete()


@sync_to_async
def set_transaction_amount(transaction_id, amount):
    """Store confirmed amount on a pending transaction."""
    Transaction.objects.filter(id=transaction_id).update(amount=amount)


@sync_to_async
def cancel_bep20_transaction(transaction_id):
    """Mark transaction failed and release its locked amount."""
    tx = Transaction.objects.filter(id=transaction_id).first()
    if tx:
        BEP20ActiveAmount.objects.filter(amount=tx.amount).delete()
        tx.status = "failed"
        tx.save(update_fields=["status"])