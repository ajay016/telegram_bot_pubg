import os
import django
from datetime import datetime
import asyncio
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
import random
from django.db import transaction
from asgiref.sync import sync_to_async
import websockets
import json
from telegram import Bot
import aiohttp
from telegram import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler, ApplicationBuilder
from core.models import *  # Replace 'store' with your app name
from api.bybit_websocket.bybit_ws import bybit_ws_listener


# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "telegram_bot_project.settings")  # Replace with your project
django.setup()

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN


SELECT_QUANTITY = 1


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


@sync_to_async
def get_all_payment_methods():
    return list(PaymentMethod.objects.all().values('id', 'name'))


# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Register the Telegram user and ensure a Wallet is created
    await get_or_create_telegram_user(update.effective_user)
    
    keyboard = [
        [
            InlineKeyboardButton("🛍️ Browse Products", callback_data="browse_products"),
            InlineKeyboardButton("👛 My Wallet", callback_data="my_wallet")
        ],
        [
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
        ],
        # This one takes full width (alone in its row)
        [
            InlineKeyboardButton("🎮 Game ID Recharge (Auto)", callback_data="game_id_recharge_auto")
        ],
        [
            InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"),
            InlineKeyboardButton("🧩 API", callback_data="api")
        ]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome! What would you like to do?", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "browse_products":
        categories = await get_categories()
        keyboard = [
            [InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")]
            for cat in categories
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("Select a category:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("cat_"):
        category_id = int(data.split("_")[1])
        products = await get_products_by_category(category_id)
        if not products:
            await query.edit_message_text("No products found in this category.")
            return
        keyboard = [
            [InlineKeyboardButton(f"{prod['name']} | ${prod['price']} | {prod['stock_quantity']}", callback_data=f"prod_{prod['id']}")]
            for prod in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="browse_products")])
        await query.edit_message_text("Here are some exciting products that we offer for you!!", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("prod_"):
        product_id = int(data.split("_")[1])
        product = await get_product_detail(product_id)
        if not product:
            await query.edit_message_text("Product not found.")
            return

        text = (
            f"🛍️ <b>{product['name']}</b>\n\n"
            f"📝 Description: {product['description']}\n"
            f"💰 Price: ${product['price']}\n"
            f"📦 Stock: {product['stock_quantity']} available"
        )

        keyboard = [
            [InlineKeyboardButton("🛒 Buy", callback_data=f"buy_{product_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"cat_{product['category']}")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("buy_"):
        # Extract product_id
        product_id = int(data.split("_")[1])
        # Store it so the next handler can use it
        context.user_data["pending_product_id"] = product_id

        # Ask quantity
        await query.edit_message_text(
            f"ℹ️ How many units of product #{product_id} would you like to buy?\n\n"
            "Please enter a whole number (e.g. 2)."
        )
        return SELECT_QUANTITY

    elif data == "main_menu":
        await start(update, context)
        
    elif data.startswith("pm_"):
        method_id = int(data.split("_")[1])
        method = await get_payment_method_info(method_id)

        if not method:
            await query.edit_message_text("Invalid payment method selected.")
            return

        is_binance = "binance" in method["api_base_url"].lower() if method.get("api_base_url") else False

        if is_binance:
            user = await get_or_create_telegram_user(update.effective_user)
            # Generate and store a unique Binance note
            while True:
                note = get_random_string(12)
                print('note before: ', note)
                if not await note_exists(note):
                    print('getting notes', note)
                    break

            # Save the note for this 
            print('note after while loop: ', note)
            await BinancePayNote.objects.acreate(note=note, user=user)

            # Create transaction (if needed)
            transaction = await create_topup_transaction(user.id, method_id, note)

            text = (
                f"🪪 <b>UID:</b> <code>123456789</code> (Tap to copy)\n\n"
                f"💸 Please send your desired amount to this UID and include the note below:\n\n"
                f"📝 <b>Note:</b> <code>{note}</code>\n\n"
                f"⚠️ <b>Please send only</b> <code>USDT</code>. After paying, click the ✅ <b>I have paid</b> button.\n\n"
                f"🔴 <i>Note: This will be valid for only 30 minutes</i>"
            )

            keyboard = [[InlineKeyboardButton("✅ I have paid", callback_data=f"confirm_{transaction.id}")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
        elif "bybit" in method["api_base_url"].lower():
            # Store method in user session or memory
            context.user_data["selected_method"] = method
            
            text = (
                f"💵 Please enter the amount (in USD) you want to deposit\n"
                f"📌 Example: 40.00\n\n"
                f"📝 If you want to cancel the operation send \\cancel"
            )
            await query.edit_message_text(text)
            
            # 🚀 Tell the ConversationHandler to wait for amount input next
            return AMOUNT_INPUT

        else:
            # Non-binance — do not use note here
            text = f"💳 <b>{method['name']}</b>\n\n{method['description']}"
            if method.get("address"):
                text += f"\n📍 Send to: <code>{method['address']}</code>"

            keyboard = [[InlineKeyboardButton("🔙 Back to Wallet", callback_data="my_wallet")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
    
    elif data.startswith("confirm_"):
        transaction_id = int(data.split("_")[1])
        print('transaction confirm_id: ', transaction_id)
        chat_id = update.effective_chat.id

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{settings.BOT_API_BASE_URL}/api/confirm-topup/", json={"transaction_id": transaction_id}) as resp:
                data = await resp.json()

        if resp.status == 200 and data.get("success"):
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ <b>Payment received successfully!</b>\n\n"
                    f"💰 <b>${data['amount']}</b> has been added to your wallet.\n"
                    f"💼 <b>New Balance:</b> <code>${data['balance']}</code>"
                ),
                parse_mode="HTML"
            )
            # Optionally, redirect to wallet menu:
            await show_wallet_info(chat_id, context, telegram_id=data["telegram_id"])

        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=data.get("detail", "❌ Payment confirmation failed.")
            )

        

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    telegram_user = update.effective_user
    telegram_id = telegram_user.id

    if "Browse Products" in text:
        await show_categories(update, context)

    elif "My Wallet" in text:
        # Fetch wallet and user data
        wallet = await get_wallet_by_telegram_id(telegram_id)
        if not wallet:
            await update.message.reply_text("❌ Wallet not found.")
            return

        full_name = f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip()

        if full_name:
            display_name = full_name
        elif telegram_user.username:
            display_name = f"@{telegram_user.username}"
        else:
            display_name = str(telegram_user.id)
    
        current_date = datetime.now().strftime("%B %d, %Y")
        balance = wallet.balance

        # Get all payment methods
        payment_methods = await get_all_payment_methods()  # This should return a list of dicts or objects with id and name

        text = (
            f"👛 <b>Wallet Information</b>:\n\n"
            f"Hello, <b>{display_name}</b>! Your wallet balance as of <i>{current_date}</i>:\n\n"
            f"🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>\n"
            f"💰 <b>Current Balance:</b> <code>${balance:.2f}</code>\n\n"
            f"✨ Would you like to top up your wallet? Use one of the following methods:"
        )

        # keyboard = [
        #     [InlineKeyboardButton(f"💳 {method['name']}", callback_data=f"pm_{method['id']}")]
        #     for method in payment_methods
        # ]
        
        # Create buttons two per row
        keyboard = []
        row = []
        for i, method in enumerate(payment_methods, start=1):
            row.append(InlineKeyboardButton(f"💳 {method['name']}", callback_data=f"pm_{method['id']}"))
            if i % 2 == 0:
                keyboard.append(row)
                row = []

        # Append last row if it has one button
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif "My Orders" in text:
        await update.message.reply_text("Your orders will show here.")

    elif "Leaderboard" in text:
        await update.message.reply_text("Here's the leaderboard.")

    elif "Game ID Recharge (Auto)" in text:
        await update.message.reply_text("Please send your Game ID to proceed.")

    elif "Contact Support" in text:
        await update.message.reply_text("Contact us at support@example.com.")

    elif "API" in text:
        await update.message.reply_text("API access is coming soon!")
        
        
async def handle_amount_input(update, context):
    print('handle input amount entered')
    try:
        amount = float(update.message.text.strip())
        print('entered amount: ', amount)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number (e.g., 15.0)")
        return

    user = await get_or_create_telegram_user(update.effective_user)
    method = context.user_data.get("selected_method")

    if not method:
        await update.message.reply_text("⚠️ No payment method selected.")
        return

    # Create topup and payment transaction
    transaction = await create_topup_transaction(user.id, method["id"], note=None)
    payment = await create_payment_transaction(user.id, method["id"], amount, transaction.id)

    

    msg = (
        f"✅ Kindly deposit exactly <b>{amount:.2f} USDT (BYBIT)</b> to the address below:\n\n"
        f" 💼 <code>{method['address']}</code>\n\n"
        f" ⏰ This invoice will expire in 20 minutes.\n\n"
        f" ⏬ Kindly complete the deposit of exact amount within this time frame.\n\n"
        f" 🕑 This message will be deleted after 20 minutes. 🗑️"
    )
    sent = await update.message.reply_text(msg, parse_mode="HTML")

    # Schedule message deletion
    asyncio.create_task(
        delete_message_after_delay(
            context.bot, 
            update.effective_chat.id, 
            sent.message_id
        )
    )
    return ConversationHandler.END

async def delete_message_after_delay(bot, chat_id, message_id, delay=20*60):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Failed to delete message: {e}")
    

# Function to handle the quantity input for purchasing a product
async def handle_quantity_input(update, context):
    text = update.message.text.strip()
    try:
        qty = int(text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        return await update.message.reply_text("❌ Please enter a positive whole number.")

    user_data     = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    product_id    = context.user_data.get("pending_product_id")
    if not product_id:
        return await update.message.reply_text("⚠️ No product selected. Please start again with Buy.")

    # fetch product + wallet
    product, wallet = await get_product_and_wallet(telegram_user, product_id)
    total = product.price * Decimal(qty)

    if wallet.balance < total:
        return await update.message.reply_text(
            f"❌ You need ${total:.2f} but your balance is only ${wallet.balance:.2f}."
        )

    # Everything looks good — perform DB updates atomically
    @sync_to_async
    def do_purchase_and_vouchers():
        with transaction.atomic():
            # Deduct balance
            wallet.balance -= total
            wallet.save()

            print('wallet amount has just changed')
            # Deduct stock quantity
            product.stock_quantity -= qty
            product.save()

            # Create order
            order = Order.objects.create(
                user=telegram_user,
                total_price=total
            )

            # Get available voucher codes (if any)
            available_vouchers = list(
                VoucherCode.objects.filter(product=product, is_used=False)[:qty]
            )

            for i in range(qty):
                voucher = available_vouchers[i] if i < len(available_vouchers) else None
                if voucher:
                    voucher.is_used = True
                    voucher.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=1,  # single quantity per item
                    unit_price=product.price,
                    voucher_code=voucher
                )

            return order, wallet.balance

    order, new_balance = await do_purchase_and_vouchers()

    # Respond to user
    await update.message.reply_text(
        f"✅ Thank you for your purchase!\n\n"
        f"• Product: {product.name}\n"
        f"• Quantity: {qty}\n"
        f"• Total: ${total:.2f}\n\n"
        f"🛍️ Your order #{order.id} is now in process.\n\n"
        f"💰 Your new balance is ${wallet.balance:.2f}.",
        parse_mode="HTML"
    )

    # Clean up and go back to main menu
    context.user_data.pop("pending_product_id", None)
    return ConversationHandler.END
   
        
@sync_to_async
def get_categories():
    return list(Category.objects.all().values("id", "name"))

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = await get_categories()

    keyboard = [
        [InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")]
        for cat in categories
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Here are some Categories where you can find exciting products!!", reply_markup=reply_markup)
    

@sync_to_async
def get_products_by_category(category_id):
    return list(Product.objects.filter(category_id=category_id).values('id', 'name', 'price', 'stock_quantity'))

@sync_to_async
def get_product_detail(product_id):
    return Product.objects.filter(id=product_id).values(
        'name', 'description', 'price', 'stock_quantity', 'category'
    ).first()
    

@sync_to_async
def get_wallet_balance(user):
    try:
        return Wallet.objects.get(telegram_user=user)
    except Wallet.DoesNotExist:
        return None
    

@sync_to_async
def get_payment_methods():
    return list(PaymentMethod.objects.filter(is_active=True).values('id', 'name'))

async def show_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    wallet = await sync_to_async(lambda: Wallet.objects.get(telegram_user=telegram_user))()

    text = f"👛 Your Wallet Balance: ${wallet.balance}"

    methods = await get_payment_methods()
    keyboard = [
        [InlineKeyboardButton(method['name'], callback_data=f"pm_{method['id']}")]
        for method in methods
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    

@sync_to_async
def get_payment_method_info(method_id):
    try:
        method = PaymentMethod.objects.get(id=method_id)
        return {
            "id": method.id,
            "name": method.name,
            "description": method.description,
            "address": method.address,
            "api_base_url": method.api_base_url,
        }
    except PaymentMethod.DoesNotExist:
        return None
    

@sync_to_async
def create_topup_transaction(user_id, method_id, note):
    user = TelegramUser.objects.get(id=user_id)
    method = PaymentMethod.objects.get(id=method_id)
    return TopUpTransaction.objects.create(user=user, payment_method=method, note=note)


@sync_to_async
def get_transaction_by_id(transaction_id):
    try:
        return TopUpTransaction.objects.get(id=transaction_id)
    except TopUpTransaction.DoesNotExist:
        return None


@sync_to_async
def confirm_transaction_and_update_wallet(transaction_id, amount):
    tx = TopUpTransaction.objects.get(id=transaction_id)
    tx.status = "confirmed"
    tx.amount_received = amount
    tx.save()
    
    wallet = Wallet.objects.get(telegram_user=tx.user)
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


async def show_wallet_info(chat_id, context, telegram_id):
    user = await get_user_by_telegram_id(telegram_id)
    wallet = await get_wallet_balance(user)

    text = (
        f"👤 <b>Your Wallet</b>\n\n"
        f"💼 <b>Balance:</b> <code>${wallet.balance}</code>\n"
        f"📅 Last Updated: {wallet.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    keyboard = [
        [InlineKeyboardButton("🔄 Top Up", callback_data="topup_wallet")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    

# After confirming Purchase
@sync_to_async
def get_product_and_wallet(user: TelegramUser, product_id: int):
    # Fetch product and user's wallet in one go
    product = Product.objects.get(id=product_id)
    wallet  = Wallet.objects.get(telegram_user=user)
    return product, wallet

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
    

async def get_user_by_telegram_id(telegram_id: int) -> TelegramUser | None:
    try:
        return await TelegramUser.objects.aget(telegram_id=telegram_id)
    except TelegramUser.DoesNotExist:
        return None
    
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END


# Completing Bybit pay API
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
def mark_payment_completed(payment_id):
    PaymentTransaction.objects.filter(id=payment_id).update(status="completed")

@sync_to_async
def mark_topup_completed(topup_id):
    TopUpTransaction.objects.filter(id=topup_id).update(status="confirmed")

@sync_to_async
def credit_wallet(user_id, amount):
    wallet = Wallet.objects.get(telegram_user_id=user_id)
    wallet.balance += amount
    wallet.save()
# Completing Bybit pay API ends

        

# Register bot commands
async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Restart the bot")
    ])



# AMOUNT_INPUT = 1  # Define a state

SELECTING_PAYMENT_METHOD, AMOUNT_INPUT = range(2)

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CallbackQueryHandler(button_handler),  # Accept entry via button
    ],
    states={
        AMOUNT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount_input),
        ],
        
        SELECT_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity_input)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
    ],
)


class Command(BaseCommand):
    help = "Run the Telegram bot"

    def handle(self, *args, **options):
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        
        app.add_handler(conv_handler)
        
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        app.post_init = lambda app: set_commands(app)
        
        print("🤖 Bot is running...")
        app.run_polling()



class Command(BaseCommand):
    help = "Run the Telegram bot and WebSocket listener"

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        async def post_init(app):
            # Set commands
            await set_commands(app)
            # Start the WebSocket listener in background
            asyncio.create_task(bybit_ws_listener())
            print("🌐 WebSocket listener started")

        application.post_init = post_init

        print("🤖 Bot is running...")
        application.run_polling()


