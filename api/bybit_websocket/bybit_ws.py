import json
import time
import hmac
import hashlib
import websockets
import asyncio  # <-- Needed for sleep
from asgiref.sync import sync_to_async
from django.conf import settings
from core.models import *
from telegram import Bot
from django.utils import timezone

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

# async def bybit_ws_listener():
#     uri = "wss://stream.bybit.com/v5/private"

#     # Create Bybit signature for auth
#     timestamp = str(int(time.time() * 1000))
#     recv_window = "5000"
#     param_str = timestamp + settings.BYBIT_API_KEY + recv_window
#     sign = hmac.new(
#         settings.BYBIT_API_SECRET.encode(),
#         param_str.encode(),
#         hashlib.sha256
#     ).hexdigest()

#     async with websockets.connect(uri) as ws:
#         # Send auth message
#         await ws.send(json.dumps({
#             "op": "auth",
#             "args": [settings.BYBIT_API_KEY, timestamp, sign, recv_window]
#         }))

#         # Subscribe to wallet topic
#         await ws.send(json.dumps({
#             "op": "subscribe",
#             "args": ["wallet"]
#         }))

#         while True:
#             msg = await ws.recv()
#             print("📥 Received message from WebSocket:", msg)
#             data = json.loads(msg)
#             print("📥 Received message from WebSocket and parsed into json:", data)

#             if data.get("topic") == "wallet":
#                 for deposit in data.get("data", {}).get("transferRecords", []):
#                     await handle_bybit_deposit(deposit)

# @sync_to_async
# def handle_bybit_deposit(deposit):
#     amount = float(deposit.get("amount", 0))
#     reference = deposit.get("tag")  # Or use "memo" or similar

#     try:
#         transaction = PaymentTransaction.objects.get(
#             amount=amount,
#             status="pending",
#             note=reference  # Optional: match on reference if you're using notes
#         )
#         transaction.status = "completed"
#         transaction.save()

#         wallet = transaction.wallet
#         wallet.balance += transaction.amount
#         wallet.save()

#         bot.send_message(
#             chat_id=transaction.user.telegram_id,
#             text=(
#                 f"✅ <b>Deposit Confirmed</b>\n\n"
#                 f"💰 <b>${transaction.amount:.2f}</b> has been added to your wallet.\n"
#                 f"💼 New balance: <code>${wallet.balance:.2f}</code>"
#             ),
#             parse_mode="HTML"
#         )

#     except PaymentTransaction.DoesNotExist:
#         print(f"❌ No pending transaction found for amount: {amount} and reference: {reference}")






async def bybit_ws_listener():
    uri = "wss://stream.bybit.com/v5/private"

    while True:
        try:
            print("🔌 Connecting to Bybit WebSocket...")
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                print("✅ Connected to WebSocket.")

                # Build expires and signature
                expires = int((time.time() + 5) * 1000)
                payload = f"GET/realtime{expires}"
                sign = hmac.new(
                    settings.BYBIT_API_SECRET.encode("utf-8"),
                    payload.encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()

                # Authenticate (3 args)
                await ws.send(json.dumps({
                    "op": "auth",
                    "args": [settings.BYBIT_API_KEY, expires, sign]
                }))
                print("🔐 Sent auth request.")

                # Subscribe to wallet updates
                await ws.send(json.dumps({
                    "op": "subscribe",
                    "args": ["wallet"]
                }))
                print("📡 Subscribed to wallet topic.")

                # Simulate test deposit (optional)
                await asyncio.sleep(5)
                fake_deposit = {"amount": "50.0", "tag": "test_reference"}
                print("🧪 Simulating deposit…")
                await handle_bybit_deposit(fake_deposit)

                # Receive loop
                while True:
                    try:
                        msg = await ws.recv()
                        print("📥 WS Message:", msg)
                        data = json.loads(msg)

                        if data.get("topic") == "wallet":
                            wallet_data = data["data"]
                            # adapt to actual structure…
                            await handle_bybit_deposit(wallet_data)

                    except websockets.ConnectionClosedError as e:
                        print(f"⚠️ WS closed: {e}; reconnecting in 5s…")
                        break

        except Exception as e:
            print(f"❌ WS connection error: {e}; retry in 5s…")

        await asyncio.sleep(5)
        

@sync_to_async
def handle_bybit_deposit(deposit):
    """
    Called whenever there is a new deposit event from the WS.
    deposit: dict with keys 'amount' (str), 'tag' (str, your note/memo)
    """
    amount = float(deposit.get("amount", 0))
    memo = deposit.get("tag")  # your unique note
    now = timezone.now()

    # 1) Find the pending TopUpTransaction that generated this memo,
    #    and ensure it's not expired:
    try:
        topup = TopUpTransaction.objects.get(
            note=memo,
            status="pending",
            created_at__gte=now - timedelta(minutes=30)
        )
    except TopUpTransaction.DoesNotExist:
        print(f"No matching TopUpTransaction for memo={memo}")
        return

    # 2) Find the associated PaymentTransaction:
    try:
        payment = PaymentTransaction.objects.get(
            topup_transaction=topup,
            amount=amount,
            status="pending"
        )
    except PaymentTransaction.DoesNotExist:
        print(f"No pending PaymentTransaction for topup={topup.id} amount={amount}")
        return

    # 3) All good—mark them confirmed:
    topup.status = "confirmed"
    topup.amount_received = amount
    topup.save()

    payment.status = "completed"
    payment.save()

    # 4) Credit the user’s wallet:
    wallet = payment.wallet
    wallet.balance = wallet.balance + amount
    wallet.save()

    # 5) Notify the user on Telegram:
    user = payment.user
    bot.send_message(
        chat_id=user.telegram_id,
        text=(
            f"✅ <b>Deposit Confirmed</b>\n\n"
            f"💰 <b>${amount:.2f}</b> has been added to your wallet.\n"
            f"💼 New balance: <code>${wallet.balance:.2f}</code>"
        ),
        parse_mode="HTML"
    )
    print(f"✅ Processed deposit for user {user.telegram_id}: +${amount}")