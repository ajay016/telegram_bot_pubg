import json
import time
import httpx
import hmac
import hashlib
import websockets
import asyncio  # <-- Needed for sleep
from asgiref.sync import sync_to_async
from django.conf import settings
from core.models import *
from telegram import Bot
from django.utils import timezone
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta
from core.models import Wallet
from decimal import Decimal




bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
API_KEY = settings.BYBIT_API_KEY
API_SECRET = settings.BYBIT_API_SECRET

session = HTTP(
    testnet=True,
    api_key=settings.BYBIT_API_KEY,
    api_secret=settings.BYBIT_API_SECRET,
    recv_window=30000,
)

BASE_URL = "https://api.bybit.com"  # Mainnet (not testnet)




async def bybit_ws_listener():
    # uri = "wss://stream.bybit.com/v5/private"
    uri = "wss://stream-testnet.bybit.com/v5/private"

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

                # Authenticate
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

                # Receive loop
                while True:
                    try:
                        msg = await ws.recv()
                        print("📥 WS Message:", msg)
                        data = json.loads(msg)

                        print('data from ByBit websocket listener: ', data)
                        
                        if data.get("topic") == "wallet":
                            wallet_data = data.get("data", [])
                            print("📬 Wallet Data Received:")
                            print(json.dumps(wallet_data, indent=2))

                    except websockets.ConnectionClosedError as e:
                        print(f"⚠️ WS closed: {e}; reconnecting in 5s…")
                        break

        except Exception as e:
            print(f"❌ WS connection error: {e}; retry in 5s…")

        await asyncio.sleep(5)

    
    
    
def generate_signature(params, secret):
    param_str = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
    return hmac.new(secret.encode(), param_str.encode(), hashlib.sha256).hexdigest()


    


# Initialize session
# Convert datetime to milliseconds
def dt_to_ms(dt):
    return int(dt.timestamp() * 1000)

async def bybit_transaction_listener():
    print("🚀 Starting Bybit transaction listener...")

    session = HTTP(
        api_key=settings.BYBIT_API_KEY,
        api_secret=settings.BYBIT_API_SECRET,
        testnet=False,
    )

    while True:
        try:
            # Get transactions from yesterday onward
            now = datetime.now()
            start_time = now - timedelta(days=1)
            start_ms = dt_to_ms(start_time)

            print(f"📡 Fetching transactions since: {start_time.isoformat()}")

            result = session.get_transaction_log(
                accountType="FUND",
                category="linear",
                currency="USDT",
                startTime=start_ms,
                limit=50
            )

            print("📥 Transaction Log Response:")
            print(result)

            # You can process each transaction here
            for tx in result.get("result", {}).get("list", []):
                print("🔍 Transaction:")
                print(tx)

            # Poll every N seconds
            await asyncio.sleep(15)

        except Exception as e:
            print(f"❌ Error in transaction listener: {e}")
            await asyncio.sleep(10)
            


async def fetch_trc20_transactions(start_time_ms):
    try:
        print("📤 Fetching TRC20 deposit records")
        response = session.get_deposit_records(coin="USDT", startTime=start_time_ms)
        print("📥 TRC20 API Response:", response)

        if response["retCode"] == 0:
            tx_list = response["result"]["rows"]
            parsed = [
                {
                    "amount": tx.get("amount"),
                    "txID": tx.get("txID"),
                    "status": tx.get("status"),
                }
                for tx in tx_list
                if tx.get("status") == 3  # status 3 = success
            ]
            return parsed
        else:
            print(f"❌ TRC20 API error: {response['retMsg']}")
            return []
    except Exception as e:
        print(f"🚨 Exception during TRC20 fetch: {str(e)}")
        return []


async def fetch_transactions(start_time_ms):
    try:
        start_time_sec = start_time_ms // 1000  # Universal Transfer API expects seconds

        print(f"📤 Sending API request to fetch universal transfer records from {start_time_sec}")
        # response = session.get_internal_deposit_records(
        #     coin="USDT",
        #     startTime=start_time_ms
        # )
        
        response = session.get_internal_deposit_records(
            coin="USDT",
            startTime=start_time_ms
        )

        print(f"📥 Raw API Response: {response}")

        if response["retCode"] == 0:
            tx_list = response["result"]["rows"]
            parsed = [
                {
                    "amount": tx.get("amount"),
                    # "time": tx.get("timestamp"),
                    "type": "UNIVERSAL_TRANSFER",
                    # "from": tx.get("fromAccountType"),
                    # "to": tx.get("toAccountType"),
                }
                for tx in tx_list
                if tx.get("status") in [2, 3]
            ]
            return parsed
        else:
            print(f"❌ API error: {response['retMsg']}")
            return []

    except Exception as e:
        print(f"🚨 Exception during fetch: {str(e)}")
        return []
    
    

async def wait_for_matching_transaction(amount, user_id, bot, chat_id, message_id, start_time_ms, timeout=20*60, interval=10, initial_delay=10, method_name=""):
    print(f"🕒 Initial delay of {initial_delay}s before first transaction check...")
    await asyncio.sleep(initial_delay)

    # start_time_ms = int((time.time() - initial_delay) * 1000)
    start_time_ms = int((time.time()) * 1000 - 1000 * 60 * 60 * 24)
    print(f"⏱️ Using startTime = {start_time_ms} ({datetime.utcfromtimestamp(start_time_ms / 1000)})")

    start = time.time()
    elapsed = 0

    while elapsed < timeout:
        print(f"\n🔁 Checking for transactions at {datetime.utcnow().isoformat()} (elapsed: {int(elapsed)}s)")
        
        # transactions = await fetch_transactions(start_time_ms)
        
        if "bybit" in method_name.lower():
            transactions = await fetch_transactions(start_time_ms)
        elif "trc20" in method_name.lower():
            transactions = await fetch_trc20_transactions(start_time_ms)
        else:
            print("❗ Unknown method name. Skipping check.")
            return False

        if not transactions:
            print("📭 No transactions found in this cycle.")
        else:
            print(f"📦 Received {len(transactions)} transactions:")
            for tx in transactions:
                print(f"    - {tx}")

        for tx in transactions:
            if float(tx["amount"]) == amount:
                print(f"✅ Matching transaction found! Amount: {tx['amount']}")

                wallet = await sync_to_async(Wallet.objects.get)(telegram_user=user_id)
                balance_before = wallet.balance
                wallet.balance += Decimal(str(amount))
                await sync_to_async(wallet.save)()

                # tx_id = tx.get("txID", "N/A")
                # Get the latest pending payment for this user
                payment = await sync_to_async(
                    lambda: PaymentTransaction.objects.filter(user=user_id, status='pending').latest('created_at')
                )()
                topup = await sync_to_async(lambda: payment.topup_transaction)()
                # tx_id = tx.get("txID", f"{tx['amount']}_{int(time.time())}")  # fallback ID
                
                timestamp = int(time.time())
                formatted_amount = str(amount).replace('.', '')  # remove decimal point for clean ID
                generated_tx_id = f"{payment.id}{formatted_amount}{timestamp}"
                
                tx_id = tx.get("txID", generated_tx_id)

                # Check if already processed
                already_processed = await sync_to_async(PaymentTransaction.objects.filter(tx_id=tx_id).exists)()
                if already_processed:
                    print(f"⚠️ Transaction {tx_id} already processed.")
                    continue

                # Update payment and topup
                payment.tx_id = tx_id
                payment.status = "completed"
                await sync_to_async(payment.save)()

                topup.amount_received = Decimal(str(amount))
                topup.status = "confirmed"
                await sync_to_async(topup.save)()

                msg = (
                    "💸 <b>New Transaction</b> 💸\n\n"
                    f"✅ <b>Transaction ID:</b> #{tx_id}\n"
                    f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                    f"🔄 <b>Type:</b> Add Balance\n"
                    f"💰 <b>Amount:</b> ${amount:.2f}\n"
                    f"📊 <b>Balance Before:</b> ${balance_before:.2f}\n"
                    f"📈 <b>Balance After:</b> ${wallet.balance:.2f}\n"
                    f"📌 <b>Status:</b> Success\n"
                    f"📝 <b>Description:</b> Payment from BYBIT Pay"
                )

                await bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode="HTML"
                )
                return True

        print(f"⏳ Waiting {interval}s before next check...")
        await asyncio.sleep(interval)
        elapsed = time.time() - start

    print("❌ Timeout reached. No matching transaction found.")
    await bot.send_message(chat_id=chat_id, text="⌛ Timeout. No matching deposit found.")
    return False


def update_wallet_balance(user_id, amount):  # adjust if different
    wallet = Wallet.objects.get(user_id=user_id)
    wallet.balance += amount
    wallet.save()
