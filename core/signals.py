# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TelegramUser, Wallet

@receiver(post_save, sender=TelegramUser)
def create_wallet_for_telegram_user(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(telegram_user=instance)
