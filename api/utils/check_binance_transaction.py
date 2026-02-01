from datetime import timedelta
from django.utils import timezone
from .binance_client import binance_signed_request
from core.models import BinancePayNote, Transaction, Wallet
from decimal import Decimal

async def confirm_binance_payment(user, note):
    try:
        note_obj = await BinancePayNote.objects.aget(note=note, user=user, is_used=False)
    except BinancePayNote.DoesNotExist:
        return None  # Already used or invalid note

    created_at = int(note_obj.created_at.timestamp() * 1000)  # 30 days ago

    # Fetch transactions after note was created
    params = {
        "startTime": created_at,
        "limit": 50  # Optional
    }
    data = binance_signed_request("/sapi/v1/pay/transactions", params)
    print('data from binance***********************: ', data)
    
    # Check each transaction
    for tx in data.get("data", []):
        remark = tx.get("remark")
        amount = tx.get("amount")
        asset = tx.get("currency")
        status = tx.get("status")

        if (
            remark == note and
            asset == "USDT" and
            status.lower() == "success"
        ):
            amount_decimal = Decimal(amount)

            # Update Wallet
            wallet, _ = await Wallet.objects.aget_or_create(user=user)
            wallet.balance += amount_decimal
            await wallet.asave()

            # Create Transaction
            await Transaction.objects.acreate(
                user=user,
                payment_method_id=tx.get("bizType"),  # Use appropriate method id or pass it
                note=note,
                amount=amount_decimal,
                status="confirmed"
            )

            # Mark note used
            note_obj.is_used = True
            await note_obj.asave()

            return amount_decimal  # Return amount to show in Telegram

    return None
