# signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import TelegramUser, Wallet, VoucherCode

@receiver(post_save, sender=TelegramUser)
def create_wallet_for_telegram_user(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(telegram_user=instance)


@receiver(post_save, sender=VoucherCode)
@receiver(post_delete, sender=VoucherCode)
def update_product_stock(sender, instance, **kwargs):
    instance.product.update_stock_from_vouchers()