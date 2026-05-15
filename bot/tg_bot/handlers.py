import os
import io
import django
from django.utils import timezone
from datetime import datetime
import asyncio
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
import random
from django.db import transaction
from asgiref.sync import sync_to_async
from decimal import Decimal, ROUND_DOWN
import websockets
import json
from django.conf import settings
from telegram import Bot, InputFile
import aiohttp
from telegram import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler, ApplicationBuilder
from core.models import *  
from api.bybit_websocket.bybit_ws import bybit_ws_listener, bybit_transaction_listener, wait_for_matching_transaction, update_wallet_balance
from core.decorators import block_check
from core.utils.generate_order import generate_order_summary_pdf
from telegram import InputFile
from .states import(
    SELECT_QUANTITY,
    TYPING_RECHARGE_PUBG_ID,
    SELECT_RECHARGE_QUANTITY,
    SELECTING_PAYMENT_METHOD,
    AMOUNT_INPUT,
    CONFIRM_PURCHASE,
    CONFIRM_RECHARGE_PURCHASE,
    SELECT_MANUAL_QUANTITY,
    CONFIRM_MANUAL_PURCHASE,
    BEP20_AMOUNT_INPUT,
    BEP20_AMOUNT_CONFIRM,
    TYPING_MANUAL_PUBG_ID,
)
from .utils import(
    fmt_money,
    get_admin_chat_id,
    delete_message_after_delay,
    normalize_amount,
    notify_admin_order_completed,
    notify_admin_order_pending,
    release_bep20_after_delay,
)
from .database import(
    get_or_create_telegram_user,
    get_current_announcement,
    get_top_buyers,
    get_categories,
    get_categories_manual_order,
    get_products_by_category_manual_order,
    get_wallet_by_telegram_id,
    get_all_payment_methods,
    get_products_by_category,
    get_product_detail,
    get_product_and_wallet,
    get_payment_method_info,
    note_exists,
    create_topup_transaction,
    create_payment_transaction,
    complete_recharge_order_with_vouchers,
    complete_recharge_without_description,
    get_recharge_categories,
    get_user_by_telegram_id,
    get_wallet_balance,
    get_payment_methods,
    check_bep20_amount_active,
    lock_bep20_amount,
    release_bep20_amount,
    set_transaction_amount,
    cancel_bep20_transaction,
)










# @block_check
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await get_or_create_telegram_user(update.effective_user)

#     keyboard = [
#         [
#             InlineKeyboardButton("🛒 Browse Products", callback_data="browse_products"),
#             InlineKeyboardButton("💳 My Wallet", callback_data="my_wallet")
#         ],
#         [
#             InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
#             InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
#         ],
#         [
#             InlineKeyboardButton("🎮 Game ID Recharge (Auto)", callback_data="game_id_recharge_auto")
#         ],
#         [
#             InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"),
#             InlineKeyboardButton("🧩 API", callback_data="api")
#         ]
#     ]

#     # ✅ Inline keyboard markup (correct for InlineKeyboardButton)
#     reply_markup = InlineKeyboardMarkup(keyboard)

#     # 2) Send welcome text as a second bubble with the menu keyboard
#     await update.message.reply_text(
#         "🏬 Welcome to MSNGamer Bot!\n\n"
#         "🌴 Explore our products, check your orders, and get the best deals right here. How can I assist you today?\n\n"
#         "🔘 Choose an option below to get started:",
#         reply_markup=reply_markup
#     )



@block_check
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_or_create_telegram_user(update.effective_user)

    keyboard = [
        [
            InlineKeyboardButton("🛒 Browse Products", callback_data="browse_products"),
            InlineKeyboardButton("💳 My Wallet", callback_data="my_wallet")
        ],
        [
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
        ],
        [
            InlineKeyboardButton("🎮 Game ID Recharge (Auto)", callback_data="game_id_recharge_auto"),
            InlineKeyboardButton("📝 Manual Order", callback_data="manual_order")
        ],
        [
            InlineKeyboardButton("📞 Contact Support", callback_data="contact_support"),
            InlineKeyboardButton("🧩 API", callback_data="api")
        ]
    ]

    # ✅ Inline keyboard markup
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🏬 Welcome to MSNGamer Bot!\n\n"
        "🌴 Explore our products, check your orders, and get the best deals right here. How can I assist you today?\n\n"
        "🔘 Choose an option below to get started:"
    )

    # ✅ Check if this was triggered by a button click or a normal command
    if update.callback_query:
        # Edit the existing message for a smooth "back" transition
        await update.callback_query.edit_message_text(
            text=welcome_text,
            reply_markup=reply_markup
        )
    else:
        # Send a new message if the user typed /start
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup
        )
    
    
    
@block_check
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    print("data raw: ", data)

    if data == "browse_products":
        print('data: ', data)
        categories = await get_categories()
        keyboard = [
            [InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")]
            for cat in categories
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("Select a category:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "my_wallet":
        telegram_user = await get_or_create_telegram_user(update.effective_user)
        wallet = await get_wallet_by_telegram_id(telegram_user.telegram_id)
        if not wallet:
            await query.edit_message_text("❌ Wallet not found.")
            return ConversationHandler.END

        # Payment methods
        payment_methods = await get_all_payment_methods()

        text = (
            f"👛 <b>Wallet Information</b>\n\n"
            f"🆔 <b>Telegram ID:</b> <code>{telegram_user.telegram_id}</code>\n"
            f"💰 <b>Current Balance:</b> <code>${fmt_money(wallet.balance)}</code>\n\n"
            f"✨ Select a top up method:"
        )

        # Buttons 2 per row
        keyboard = []
        row = []
        for i, method in enumerate(payment_methods, start=1):
            row.append(InlineKeyboardButton(f"{method['name']}", callback_data=f"pm_{method['id']}"))
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return ConversationHandler.END
        
    elif data == "game_id_recharge_auto":
        recharge_categories = await sync_to_async(list)(RechargeCategory.objects.filter(is_active=True))
        if not recharge_categories:
            return await query.edit_message_text("No recharge categories found.")

        keyboard = [
            [InlineKeyboardButton(cat.name, callback_data=f"recharge_cat_{cat.id}")]
            for cat in recharge_categories
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("🎮 Select a recharge category:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    # ==========================================
    # 🆕 MANUAL ORDER FLOW (Add inside button_handler)
    # ==========================================
    elif data == "manual_order":
        categories = await get_categories_manual_order()
        keyboard = [
            [InlineKeyboardButton(cat["name"], callback_data=f"m_cat_{cat['id']}")]
            for cat in categories
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("📂 <b>Select a category for your manual order:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data.startswith("m_cat_"):
        category_id = int(data.split("_")[2])
        products = await get_products_by_category_manual_order(category_id)
        if not products:
            await query.edit_message_text("No products found in this category.")
            return
        
        keyboard = [
            [InlineKeyboardButton(f"{prod['name']} | ${fmt_money(prod['price'])} | Stock: {prod['stock_quantity']}", callback_data=f"m_prod_{prod['id']}")]
            for prod in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="manual_order")])
        await query.edit_message_text("🛍️ <b>Select a product to place a manual order:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data.startswith("m_prod_"):
        product_id = int(data.split("_")[2])
        product = await get_product_detail(product_id)
        if not product:
            await query.edit_message_text("Product not found.")
            return

        price = Decimal(product['price']).normalize()
        
        text = (
            f"🏷️ <b>{product['name']}</b>\n\n"
            f"📝 <b>Description:</b> {product['description']}\n"
            f"💰 <b>Price:</b> ${price}\n"
            f"📦 <b>Stock:</b> {product['stock_quantity']} available\n\n"
            f"⚠️ <i>Note: This is a manual order. Delivery requires admin processing.</i>"
        )

        keyboard = [
            [InlineKeyboardButton("🛒 Place Manual Order", callback_data=f"m_buy_{product_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"m_cat_{product['category']}")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data.startswith("m_buy_"):
        product_id = int(data.split("_")[2])
        context.user_data["pending_manual_product_id"] = product_id
        
        user_data = update.effective_user
        telegram_user = await get_or_create_telegram_user(user_data)
        product, wallet = await get_product_and_wallet(telegram_user, product_id)

        # Fetch category slug safely
        @sync_to_async
        def get_cat_slug(p):
            return p.category.slug
        
        cat_slug = await get_cat_slug(product)

        # NEW FLOW: Check if category slug contains 'pubg'
        if "pubg" in cat_slug.lower():
            await query.edit_message_text(
                f"📝 You are placing a <b>Manual Order</b> for <b>{product.name}</b>\n\n"
                f"🎮 <b>Please enter your PUBG Game ID:</b>\n\n"
                f"🚫 <i>Send /cancel to abort.</i>",
                parse_mode="HTML"
            )
            return TYPING_MANUAL_PUBG_ID
        else:
            await query.edit_message_text(
                f"📝 You are placing a <b>Manual Order</b> for <b>{product.name}</b>\n\n"
                f"🔢 Enter a quantity between <b>1</b> and <b>{product.stock_quantity}</b>\n\n"
                f"🚫 <i>Send /cancel to abort.</i>",
                parse_mode="HTML"
            )
            return SELECT_MANUAL_QUANTITY

    elif data.startswith("cat_"):
        print('data category: ', data)
        category_id = int(data.split("_")[1])
        products = await get_products_by_category(category_id)
        if not products:
            await query.edit_message_text("No products found in this category.")
            return
        
        def format_price(value):
            return str(Decimal(value).normalize())
        
        keyboard = [
            [InlineKeyboardButton(f"{prod['name']} | ${fmt_money(prod['price'])} | {prod['stock_quantity']}", callback_data=f"prod_{prod['id']}")]
            for prod in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="browse_products")])
        await query.edit_message_text("Here are some exciting products that we offer for you!!", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data.startswith("recharge_cat_"):
        print('Browse game pro---------------------')
        cat_id = int(data.split("_")[-1])
        products = await sync_to_async(list)(
            Product.objects.filter(recharge_category_id=cat_id, in_stock=True)
        )
        if not products:
            return await query.edit_message_text("No products found in this category.")

        keyboard = [
            [InlineKeyboardButton(f"{p.name} | ${p.price} | {p.stock_quantity}", callback_data=f"recharge_product_{p.id}")]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="game_id_recharge_auto")])
        await query.edit_message_text("💎 Select a product to recharge:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("prod_"):
        print('data category product: ', data)
        product_id = int(data.split("_")[1])
        product = await get_product_detail(product_id)
        if not product:
            await query.edit_message_text("Product not found.")
            return

        price = Decimal(product['price']).normalize()
        
        text = (
            f"🛍️ <b>{product['name']}</b>\n\n"
            f"📝 Description: {product['description']}\n"
            f"💰 Price: ${price}\n"
            f"📦 Stock: {product['stock_quantity']} available"
        )

        keyboard = [
            [InlineKeyboardButton("🛒 Buy", callback_data=f"buy_{product_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"cat_{product['category']}")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        
    elif data.startswith("recharge_product_"):
        print('data recharger category product: ', data)
        product_id = int(data.split("_")[-1])
        context.user_data["pending_recharge_product_id"] = product_id
        context.user_data["expecting_pubg_id"] = True

        await query.edit_message_text(
            "🎯 Enter your Player PUBG ID.\n\n"
            "⚠️ If you want to cancel, type /cancel."
        )
        return TYPING_RECHARGE_PUBG_ID

    elif data.startswith("buy_"):
        print('data buy product: ', data)
        # Extract product_id
        product_id = int(data.split("_")[1])
        # Store it so the next handler can use it
        context.user_data["pending_product_id"] = product_id
        
        user_data = update.effective_user
        telegram_user = await get_or_create_telegram_user(user_data)
        product, wallet = await get_product_and_wallet(telegram_user, product_id)

        # Ask quantity
        await query.edit_message_text(
            f"ℹ️ You are purchasing <b>{product.name}</b> 🎮\n\n"
            f"📝 Enter a quantity between <b>1</b> and <b>{product.stock_quantity}</b>\n\n"
            f"If you want to cancel the process, send /cancel",
            parse_mode="HTML"
        )
        
        print('SELECT_QUANTITY: ', SELECT_QUANTITY)
        return SELECT_QUANTITY
    
    elif data == "leaderboard":
        top_buyers = await get_top_buyers()
        if not top_buyers:
            text_response = "🏆 <b>Leaderboard</b>\n\nNo purchases have been made yet."
        else:
            text_response = "🏆 <b>Top 5 Buyers Leaderboard</b>\n\n"
            medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
            for idx, buyer in enumerate(top_buyers):
                # Extract first 4 digits of Telegram ID and add asterisks for privacy
                telegram_id_str = str(buyer['user__telegram_id'])
                name = f"{telegram_id_str[:4]}****"
                spent = buyer['total_spent']
                # The numbering is right here: {idx + 1}.
                text_response += f"{idx + 1}. {medals[idx]} <b>{name}</b> - <code>${spent:.2f}</code>\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        await query.edit_message_text(text_response, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return ConversationHandler.END

    elif data == "my_orders":
        tg_user = await get_or_create_telegram_user(update.effective_user)
        pdf_buffer = await sync_to_async(generate_order_summary_pdf)(tg_user)
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]

        if not pdf_buffer:
            await query.edit_message_text("📭 You have no orders currently.\n\nStart shopping now! 🛍️", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("📄 Preparing your order summary...", reply_markup=InlineKeyboardMarkup(keyboard))
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=pdf_buffer,
                filename=f"order_summary_{tg_user.telegram_id}.pdf",
                caption="📄 Here is your order summary!"
            )
        return ConversationHandler.END

    elif data == "main_menu":
        # ✅ prevent old pending purchase from being completed later
        context.user_data.pop("pending_product_id", None)
        context.user_data.pop("pending_qty", None)
        context.user_data.pop("pending_total", None)

        await start(update, context)
        return ConversationHandler.END
        
    elif data.startswith("pm_"):
        method_id = int(data.split("_")[1])
        method = await get_payment_method_info(method_id)

        if not method:
            await query.edit_message_text("Invalid payment method selected.")
            return

        is_binance = "binance" in method["api_base_url"].lower() if method.get("api_base_url") else False

        if is_binance:
            is_bep20 = "bep" in method["name"].lower()

            if is_bep20:
                # ✅ NEW BEP20 FLOW — ask user for deposit amount first
                context.user_data["bep20_method"] = method
                await query.edit_message_text(
                    f"💵 <b>BEP20 (BSC) Deposit</b>\n\n"
                    f"📍 <b>Wallet Address:</b> <code>{method['address']}</code>\n\n"
                    f"Enter the amount in USD you want to deposit.\n"
                    f"📌 Example: <code>25.00</code>\n\n"
                    f"📝 To cancel at any time, send /cancel",
                    parse_mode="HTML",
                )
                return BEP20_AMOUNT_INPUT

            else:
                # ✅ EXISTING BINANCE PAY FLOW (unchanged)
                user = await get_or_create_telegram_user(update.effective_user)
                while True:
                    note = get_random_string(12)
                    if not await note_exists(note):
                        break

                await BinancePayNote.objects.acreate(note=note, user=user)
                transaction = await create_topup_transaction(user.id, method_id, note)
                uid_display = method["uid"] if method.get("api_base_url") else "N/A"
                name = method["name"] if method.get("api_base_url") else "N/A"

                text = (
                    f"💸 Kindly deposit your desired amount on {name}\n\n"
                    f"🪪 <b>UID:</b> <code>{uid_display}</code> (Tap to copy)\n\n"
                    f"💸 Please send your desired amount to this UID and include the note below:\n\n"
                    f"📝 <b>Note:</b> <code>{note}</code>\n\n"
                    f"⚠️ <b>Please send only</b> <code>USDT</code>. After paying, click the ✅ <b>I have paid</b> button.\n\n"
                    f"🔴 <i>Note: This will be valid for only 30 minutes</i>"
                )
                keyboard = [[InlineKeyboardButton("✅ I have paid", callback_data=f"confirm_{transaction.id}")]]
                print('binance text==================================: ', f"confirm_{transaction.id}")
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            
        elif "bybit" in method["api_base_url"].lower():
            # Store method in user session or memory
            context.user_data["selected_method"] = method
            
            text = (
                f"💵 Please enter the amount (in USD) you want to deposit\n"
                f"📌 Example: 40.00\n\n"
                f"📝 If you want to cancel the operation send /cancel"
            )
            message = await query.edit_message_text(text)

            
            # ⏳ Schedule deletion after 20 minutes (1200 seconds)
            asyncio.create_task(
                delete_message_after_delay(context.bot, query.message.chat_id, message.message_id, delay=1200)
            )
            
            # 🚀 Tell the ConversationHandler to wait for amount input next
            return AMOUNT_INPUT

        else:
            # Non-binance — do not use note here
            text = f"💳 <b>{method['name']}</b>\n\n{method['description']}"
            if method.get("address"):
                text += f"\n📍 Send to: <code>{method['address']}</code>"

            keyboard = [[InlineKeyboardButton("🔙 Back to Wallet", callback_data="my_wallet")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
    elif data.startswith("confirm_bep20_"):
        await confirm_bep20_callback(update, context)
        return ConversationHandler.END

    elif data.startswith("bep20_cancel_"):
        await bep20_cancel_callback(update, context)
        return ConversationHandler.END

    elif data.startswith("confirm_") and not data.startswith("confirm_bep20_"):
        print('transaction before confirm_id: ', data)
        transaction_id = int(data.split("_")[1])
        print('transaction confirm_id: ', transaction_id)
        chat_id = update.effective_chat.id

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{settings.BOT_API_BASE_URL}/api/confirm-topup/", json={"transaction_id": transaction_id}) as resp:
                data = await resp.json()

        if resp.status == 200 and data.get("success"):
            amount = normalize_amount(data['amount'])
            balance = normalize_amount(data['balance'])
    
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ <b>Payment received successfully!</b>\n\n"
                    f"💰 <b>${float(amount):.2f}</b> has been added to your wallet.\n"
                    f"💼 <b>New Balance:</b> <code>${balance}</code>"
                ),
                parse_mode="HTML"
            )
            # Optionally, redirect to wallet menu:
            await show_wallet_info(chat_id, context, telegram_id=data["telegram_id"])

        else:
            print('binance data: ', data)
            await context.bot.send_message(
                chat_id=chat_id,
                text=data.get("detail", "❌ Payment confirmation failed.")
            )
            
    return ConversationHandler.END



@block_check
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    telegram_user = update.effective_user
    telegram_id = telegram_user.id
    
    if text.lower() == "cancel":
        await update.message.reply_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    # Check if we're expecting a PUBG ID
    if context.user_data.get("pending_recharge_product_id") is not None and context.user_data.get("expecting_pubg_id"):
        print('expecting pubg id: ', text)
        context.user_data["pubg_id"] = text
        context.user_data["expecting_pubg_id"] = False

        await update.message.reply_text("🔢 Enter the quantity you want to recharge: \n\n To cancel the operation type /cancel")
        return SELECT_RECHARGE_QUANTITY

    if "Browse Products" in text:
        await show_categories(update, context)
        
        return True
        
    if "Game ID Recharge" in text:
        await show_recharge_categories(update, context)
        
        return True
    
    elif "Manual Order" in text:
        categories = await get_categories_manual_order()
        keyboard = [
            [InlineKeyboardButton(cat["name"], callback_data=f"m_cat_{cat['id']}")]
            for cat in categories
        ]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await update.message.reply_text("📂 <b>Select a category for your manual order:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        
        return True

    elif "My Wallet" in text:
        # Fetch wallet and user data
        wallet = await get_wallet_by_telegram_id(telegram_id)
        # We removed the print(wallet) statement here to prevent the async ORM crash
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
        balance = f"{wallet.balance:.3f}"

        # Get all payment methods
        payment_methods = await get_all_payment_methods()  # This should return a list of dicts or objects with id and name

        text = (
            f"👛 <b>Wallet Information</b>:\n\n"
            f"Hello, <b>{display_name}</b>! Your wallet balance as of <i>{current_date}</i>:\n\n"
            f"🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>\n"
            f"💰 <b>Current Balance:</b> <code>${normalize_amount(balance)}</code>\n\n"
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
            row.append(InlineKeyboardButton(f"{method['name']}", callback_data=f"pm_{method['id']}"))
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
        
        return True

    elif "my orders" in text.lower():
        tg_user = await get_or_create_telegram_user(update.effective_user)
        print('telegram user for order generation: ', tg_user.telegram_id)

        pdf_buffer = await sync_to_async(generate_order_summary_pdf)(tg_user)

        if not pdf_buffer:
            await update.message.reply_text("📭 You have no orders currently.\n\nStart shopping now! 🛍️")
            return

        await update.message.reply_document(
            document=pdf_buffer,
            filename=f"order_summary_{tg_user.telegram_id}.pdf",
            caption="📄 Here is your order summary!"
        )
        return

    elif "Leaderboard" in text:
        top_buyers = await get_top_buyers()

        if not top_buyers:
            text_response = "🏆 <b>Leaderboard</b>\n\nNo purchases have been made yet."
        else:
            text_response = "🏆 <b>Top 5 Buyers Leaderboard</b>\n\n"
            medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
            for idx, buyer in enumerate(top_buyers):
                # Extract first 4 digits of Telegram ID and add asterisks for privacy
                telegram_id_str = str(buyer['user__telegram_id'])
                name = f"{telegram_id_str[:4]}****"
                spent = buyer['total_spent']
                # The numbering is right here: {idx + 1}.
                text_response += f"{idx + 1}. {medals[idx]} <b>{name}</b> - <code>${spent:.2f}</code>\n"

        await update.message.reply_text(text_response, parse_mode="HTML")
        return True

    # elif "Game ID Recharge (Auto)" in text:
    #     await update.message.reply_text("Please send your Game ID to proceed.")

    elif "Contact Support" in text:
        await update.message.reply_text(
            "📞 We're here to help! If you have any questions or need assistance, please choose an option below:\n\n"
            "🔹 Contact Support: Reach out to our support team directly.\n"
            "🔹 Visit Support Channel: [Check out our support channel for FAQs and updates](https://t.me/msngamerofficial).\n\n"
            "✨ Feel free to ask anything!",
            parse_mode="Markdown"
        )
        
        return True

    elif "API" in text:
        await update.message.reply_text("API access is coming soon!")
        
        return True
    
    

# ======================= Manual Order Flow =============================
@block_check
async def handle_manual_pubg_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END
    
    pubg_id_text = update.message.text.strip()
    context.user_data["manual_pubg_id"] = pubg_id_text

    product_id = context.user_data.get("pending_manual_product_id")
    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    await update.message.reply_text(
        f"✅ Game ID saved: <b>{pubg_id_text}</b>\n\n"
        f"🔢 Now, enter a quantity between <b>1</b> and <b>{product.stock_quantity}</b>\n\n"
        f"🚫 <i>Send /cancel to abort.</i>",
        parse_mode="HTML"
    )
    return SELECT_MANUAL_QUANTITY



@block_check
async def handle_manual_quantity_input(update, context):
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END
    
    text = update.message.text.strip()
    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    product_id = context.user_data.get("pending_manual_product_id")

    if not product_id:
        await update.message.reply_text("⚠️ No product selected. Please start again.")
        return ConversationHandler.END

    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    try:
        qty = int(text)
        if qty <= 0:
            raise ValueError("Quantity must be positive")
        if qty > product.stock_quantity:
            await update.message.reply_text(
                f"🚫 Only <b>{product.stock_quantity}</b> units of <b>{product.name}</b> are in stock.\n"
                f"Please start again.", parse_mode="HTML"
            )
            return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("🚫 Please enter a valid positive number.")
        return SELECT_MANUAL_QUANTITY

    total = product.price * Decimal(qty)

    # Check balance exactly like standard orders
    if wallet.balance < total:
        await update.message.reply_text(
            f"❌ You need ${normalize_amount(total)} but your balance is only ${normalize_amount(wallet.balance)}."
        )
        return ConversationHandler.END

    context.user_data["pending_manual_qty"] = qty
    context.user_data["pending_manual_total"] = total

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Place Order", callback_data="confirm_manual_yes"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="confirm_manual_no"),
        ]
    ]
    
    await update.message.reply_text(
        f"📝 <b>Confirm your MANUAL order</b>\n\n"
        f"🛍️ <b>Product:</b> {product.name}\n"
        f"🔢 <b>Quantity:</b> {qty}\n"
        f"💵 <b>Total Price:</b> ${fmt_money(total)}\n\n"
        f"⚠️ <i>Your balance (${fmt_money(wallet.balance)}) is sufficient. It will be deducted immediately.</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return CONFIRM_MANUAL_PURCHASE


@block_check
async def handle_manual_purchase_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_manual_no":
        context.user_data.clear()
        await query.edit_message_text("❌ Manual order cancelled.")
        return ConversationHandler.END

    if query.data != "confirm_manual_yes":
        return ConversationHandler.END

    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    
    product_id = context.user_data.get("pending_manual_product_id")
    qty = context.user_data.get("pending_manual_qty")
    total = context.user_data.get("pending_manual_total")

    if not all([product_id, qty, total]):
        await query.edit_message_text("❌ Session expired. Please start again.")
        return ConversationHandler.END

    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    # 1. Double check manual order flags (Security check)
    is_manual_product = product.is_manual

    @sync_to_async
    def get_category_is_manual(p):
        return p.category.is_manual if p.category_id else True

    is_manual_category = await get_category_is_manual(product)

    if not is_manual_product or not is_manual_category:
        await query.edit_message_text("❌ Error: This product is no longer available for manual ordering.")
        return ConversationHandler.END

    # 2. Final sanity check for balance and stock
    if wallet.balance < total or product.stock_quantity < qty:
        await query.edit_message_text("⚠️ Order failed due to insufficient balance or stock changes.")
        return ConversationHandler.END

    # Save to database (NO balance deduction)
    # Retrieve PUBG ID if it was captured
    pubg_id = context.user_data.get("manual_pubg_id", None)

    balance_before = wallet.balance

    # Save to database AND deduct balance
    @sync_to_async
    def create_pending_manual_order():
        with transaction.atomic():
            # 1. Deduct Balance
            wallet.balance -= total
            wallet.save()

            # 2. Create Order
            order = Order.objects.create(
                user=telegram_user,
                total_price=total,
                status="Admin Pending",
                order_type="Manual",
                pubg_id=pubg_id
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=qty,
                unit_price=product.price
            )

            # 3. Create Transaction Record
            transaction_obj = Transaction.objects.create(
                user=telegram_user,
                order=order,
                payment_method=None,
                note=None,
                amount=total,
                transaction_type="purchase",
                direction="debit",
                status="confirmed",
            )
            return order, wallet.balance, transaction_obj

    order, new_balance, transaction_obj = await create_pending_manual_order()
    balance_after = new_balance

    # Create dynamic PUBG ID text for notifications
    pubg_text_admin = f"🎮 <b>PUBG ID:</b> <code>{pubg_id}</code>\n" if pubg_id else ""
    pubg_text_user = f"🎮 <b>PUBG ID:</b> <code>{pubg_id}</code>\n" if pubg_id else ""

    # Inform Customer (Order Placed)
    await query.edit_message_text(
        f"✅ <b>Manual Order Placed Successfully!</b>\n\n"
        f"🔖 <b>Order ID:</b> <code>{order.id}</code>\n"
        f"🛍️ <b>Product:</b> {product.name}\n"
        f"{pubg_text_user}"
        f"⏳ <b>Status:</b> Pending Admin Processing\n\n"
        f"Thank you! We will process this shortly.",
        parse_mode="HTML"
    )

    # Inform Customer (Transaction Receipt)
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            f"🧾✨ <b>New Transaction</b> ✨🧾\n\n"
            f"🆔 <b>Transaction:</b> <code>{transaction_obj.tx_id}</code>\n"
            f"👤 <b>User ID:</b> <code>{telegram_user.telegram_id}</code>\n"
            f"🛍️ <b>Type:</b> Manual Purchase (Pending)\n"
            f"💰 <b>Amount:</b> <b>${fmt_money(total)}</b>\n"
            f"📉 <b>Balance Before:</b> <b>${fmt_money(balance_before)}</b>\n"
            f"📈 <b>Balance After:</b> <b>${fmt_money(balance_after)}</b>\n"
            f"✅ <b>Status:</b> Deducted\n\n"
            f"📝 <i>Description: Payment reserved for manual order (Order ID: {order.id})</i>"
        ),
        parse_mode="HTML"
    )

    # Inform Admin
    admin_chat_id = await get_admin_chat_id() 
    
    admin_text = (
        f"🚨 <b>NEW MANUAL ORDER ALERT</b> 🚨\n\n"
        f"👤 <b>Customer ID:</b> <code>{telegram_user.telegram_id}</code>\n"
        f"🔖 <b>Order ID:</b> <code>{order.id}</code>\n"
        f"📌 <b>Status:</b> 🟡 Admin Pending\n\n"
        f"🛍️ <b>Product Info:</b>\n"
        f"├ 📦 Name: <b>{product.name}</b>\n"
        f"├ 🔢 Quantity: <b>{qty}</b>\n"
        f"└ 💵 Total Cost: <b>${fmt_money(total)}</b>\n\n"
        f"{pubg_text_admin}"
        f"💳 <b>Customer Wallet:</b>\n"
        f"└ Current Balance: <b>${fmt_money(wallet.balance)}</b> (Sufficient ✅)\n\n"
        f"⚙️ <i>Action Required: Please process this order in the Django Admin Panel. The balance has ALREADY been deducted from the user.</i>"
    )

    if admin_chat_id:
        try:
            await context.bot.send_message(chat_id=admin_chat_id, text=admin_text, parse_mode="HTML")
        except Exception as e:
            print(f"Failed to notify admin (ID: {admin_chat_id}): {e}")
    else:
        print(f"Warning: Admin chat ID is not configured in the database. Order {order.id} notification not sent.")

    context.user_data.clear()
    return ConversationHandler.END
# ======================= Manual Order Flow =============================
    
    
    
@block_check
async def handle_amount_input(update, context):
    # First check if it's a general command like "Wallet", "Browse Products", etc.
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END  # ✅ early exit if handled
    
    try:
        amount = float(update.message.text.strip())
        print('entered amount: ', amount)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number (e.g., 15.0)\n\n  To cancel the operation type /cancel")
        return

    user = await get_or_create_telegram_user(update.effective_user)
    method = context.user_data.get("selected_method")

    if not method:
        await update.message.reply_text("⚠️ No payment method selected.")
        return

    # Create topup and payment transaction
    transaction = await create_topup_transaction(user.id, method["id"], note=None)
    payment = await create_payment_transaction(user.id, method["id"], amount, transaction.id)

    created_at = payment.created_at
    start_time_ms = int(created_at.timestamp() * 1000)
    

    if  "bybit" in method['name'].lower():
        msg = (
            f"✅ Kindly deposit exactly <b>{normalize_amount(amount)} USDT ({method['name']})</b> to the UID below:\n\n"
            f"💼 UID: <code>{method['uid']}</code>\n\n"
            f"⏰ This invoice will expire in 20 minutes.\n\n"
            f"⏬ Kindly complete the deposit of exact amount within this time frame.\n\n"
            f"🕑 This message will be deleted after 20 minutes. 🗑️"
        )
        
    else:
        msg = (
            f"✅ Kindly deposit exactly <b>{normalize_amount(amount)} USDT ({method['name']})</b> to the Address below:\n\n"
            f"💼 Address: <code>{method['address']}</code>\n\n"
            f"⏰ This invoice will expire in 20 minutes.\n\n"
            f"⏬ Kindly complete the deposit of exact amount within this time frame.\n\n"
            f"🕑 This message will be deleted after 20 minutes. 🗑️"
        )
    sent = await update.message.reply_text(msg, parse_mode="HTML")

    # Schedule deletion after 20 mins
    asyncio.create_task(delete_message_after_delay(context.bot, update.effective_chat.id, sent.message_id))

    # Monitor for transaction
    asyncio.create_task(
        wait_for_matching_transaction(
            amount,
            user,
            context.bot,
            update.effective_chat.id,
            sent.message_id,
            start_time_ms,
            method_name=method["name"]
        )
    )

    return ConversationHandler.END



@block_check
async def handle_quantity_input(update, context):
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END  # ✅ early exit if handled
    
    text = update.message.text.strip()

    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    product_id = context.user_data.get("pending_product_id")

    if not product_id:
        await update.message.reply_text("⚠️ No product selected. Please start again with Buy.")
        return ConversationHandler.END

    # Fetch product and wallet
    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    # Validate quantity input
    try:
        qty = int(text)
        if qty <= 0:
            raise ValueError("Quantity must be positive")
        if qty > product.stock_quantity:
            await update.message.reply_text(
                f"🚫 Only <b>{product.stock_quantity}</b> units of <b>{product.name}</b> are in stock.\n"
                f"The operation has been cancelled. Please start again if you want to make a new purchase.",
                parse_mode="HTML"
            )
            return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            f"You are purchasing <b>{product.name}</b> 🎮\n\n"
            f"📝 Enter a quantity between <b>1</b> and <b>{product.stock_quantity}</b>\n\n"
            f"If you want to cancel the process, send /cancel",
            parse_mode="HTML"
        )
        return SELECT_QUANTITY

    total = product.price * Decimal(qty)

    # Check balance
    if wallet.balance < total:
        await update.message.reply_text(
            f"❌ You need ${normalize_amount(total)} but your balance is only ${normalize_amount(wallet.balance)}."
        )
        return ConversationHandler.END

    # Store values in context for confirmation step
    context.user_data["pending_qty"] = qty
    context.user_data["pending_total"] = total

    # Confirmation message with inline buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_purchase_yes"),
            InlineKeyboardButton("❌ No", callback_data="confirm_purchase_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🛒 <b>Confirm your purchase</b>\n\n"
        f"• Product: <b>{product.name}</b>\n"
        f"• Quantity: <b>{qty}</b>\n"
        f"• Total Price: <b>${normalize_amount(total)}</b>\n"
        f"• Telegram ID: <code>{user_data.id}</code>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return CONFIRM_PURCHASE



@block_check
async def handle_purchase_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # ✅ Only allow the 2 purchase confirmation buttons to trigger this handler
    if query.data not in ("confirm_purchase_yes", "confirm_purchase_no"):
        # User clicked something else while purchase confirmation was pending.
        # Clear pending values to prevent accidental completion.
        context.user_data.pop("pending_product_id", None)
        context.user_data.pop("pending_qty", None)
        context.user_data.pop("pending_total", None)

        await query.answer("❌ Purchase confirmation expired. Please start again.", show_alert=True)
        return ConversationHandler.END

    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)

    if query.data == "confirm_purchase_no":
        context.user_data.pop("pending_product_id", None)
        context.user_data.pop("pending_qty", None)
        context.user_data.pop("pending_total", None)

        await query.edit_message_text("❌ Purchase cancelled.")
        return ConversationHandler.END

    product_id = context.user_data.get("pending_product_id")
    qty = context.user_data.get("pending_qty")
    total = context.user_data.get("pending_total")

    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    # 1. Double check normal order flags (Security check)
    is_normal_product = product.is_normal

    @sync_to_async
    def get_category_is_normal(p):
        return p.category.is_normal if p.category_id else True

    is_normal_category = await get_category_is_normal(product)

    if not is_normal_product or not is_normal_category:
        await query.edit_message_text("❌ Error: This product is no longer available for standard purchase.")
        return ConversationHandler.END

    # 2. Final sanity check for balance and stock
    if wallet.balance < total or product.stock_quantity < qty:
        await query.edit_message_text("⚠️ Purchase failed due to insufficient balance or stock.")
        return ConversationHandler.END

    # Check if enough vouchers are available BEFORE placing order
    available_vouchers = await sync_to_async(list)(
        VoucherCode.objects.filter(product=product, is_used=False)[:qty]
    )
    if len(available_vouchers) < qty:
        await query.edit_message_text(
            f"⚠️ Only <b>{len(available_vouchers)}</b> voucher code(s) are currently available for <b>{product.name}</b>.\n"
            f"Please try again later when more codes are in stock.",
            parse_mode="HTML"
        )
        return ConversationHandler.END
    
    balance_before = wallet.balance

    # Place order if sufficient vouchers exist
    @sync_to_async
    def complete_recharge_order_with_vouchers():
        with transaction.atomic():
            wallet.balance -= total
            wallet.save()

            product.stock_quantity -= qty
            product.save()

            order = Order.objects.create(
                user=telegram_user,
                total_price=total,
                status="Completed"
            )
            
            transaction_obj = Transaction.objects.create(
                user=telegram_user,
                order=order,
                payment_method=None,
                note=None,
                amount=total,
                transaction_type="purchase",
                direction="debit",
                status="confirmed",
            )

            assigned_codes = []

            for i in range(qty):
                voucher = available_vouchers[i]
                voucher.is_used = True
                voucher.save()
                assigned_codes.append(voucher.code)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=1,
                    unit_price=product.price,
                    voucher_code=voucher
                )

            return order, wallet.balance, assigned_codes, transaction_obj

    order, new_balance, assigned_codes, transaction_obj = await complete_recharge_order_with_vouchers()
    
    balance_after = new_balance
    
    # Notify admin of the completed order
    await notify_admin_order_completed(context.bot, order, assigned_codes, product, tx_id=transaction_obj.tx_id)

    voucher_text = "\n".join(assigned_codes)
    file_buffer = io.StringIO(voucher_text)
    
    slug_title = product.slug.replace("-", " ").replace("_", " ").upper()
    dt_str = timezone.localtime(order.created_at).strftime("%Y-%m-%d_%H-%M-%S")
    file_buffer.name = f"{slug_title}_{dt_str}.txt"
    
    description = f"\n🧾 <b>Recharge Description:</b>\n<code>{product.recharge_description}</code>" if product.recharge_description else ""

    # ✅ Edit the confirmation message to a short status (optional but clean)
    await query.edit_message_text("✅ Purchase confirmed. Sending your voucher file…")

    # ✅ Send document + caption in ONE bubble
    file_buffer.seek(0)
    await context.bot.send_document(
        chat_id=query.from_user.id,
        document=InputFile(file_buffer, filename=file_buffer.name),
        caption=(
            f"✅ <b>Thank you for your purchase!</b>\n\n"
            f"🛒 Product: <b>{product.name}</b>\n"
            f"🔢 Quantity: <b>{qty}</b>\n"
            f"🧾 Order ID: <code>{order.id}</code>\n"
            f"💲 Cost: <b>${fmt_money(total)}</b>\n"
            f"✅ Status: <b>Completed</b>\n\n"
            f"📝 <b>Note:</b>\n"
            f"ℹ️ Kindly check the attached file for product information.\n"
            f"🔒 Do not share the file with anyone else.\n"
            f"🤔 If you have any problem, contact us @MSN_GAMERS"
        ),
        parse_mode="HTML",
    )
    
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=(
            f"🧾✨ <b>New Transaction</b> ✨🧾\n\n"
            f"🆔 <b>Transaction:</b> <code>{transaction_obj.tx_id}</code>\n"
            f"👤 <b>User ID:</b> <code>{telegram_user.telegram_id}</code>\n"
            f"🛍️ <b>Type:</b> Buy Product\n"
            f"💰 <b>Amount:</b> <b>${fmt_money(total)}</b>\n"
            f"📉 <b>Balance Before:</b> <b>${fmt_money(balance_before)}</b>\n"
            f"📈 <b>Balance After:</b> <b>${fmt_money(balance_after)}</b>\n"
            f"✅ <b>Status:</b> Success\n\n"
            f"📝 <i>Description: Payment for order processing (Order ID: {order.id})</i>"
        ),
        parse_mode="HTML"
    )

    context.user_data.clear()
    return ConversationHandler.END



@block_check
async def handle_recharge_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END  # ✅ early exit if handled
    
    try:
        qty = int(update.message.text)
        if qty <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("🚫 Please enter a valid positive number for quantity. \n\n To cancel the operation, type /cancel")
        return SELECT_RECHARGE_QUANTITY

    product_id = context.user_data.get("pending_recharge_product_id")
    pubg_id = context.user_data.get("pubg_id")

    if not product_id or not pubg_id:
        await update.message.reply_text("❌ Missing product or PUBG ID. Please start again.")
        return ConversationHandler.END

    user_data = update.effective_user
    telegram_user = await get_or_create_telegram_user(user_data)
    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    # Check if quantity exceeds available stock
    if qty > product.stock_quantity:
        await update.message.reply_text(
            f"🚫 Only <b>{product.stock_quantity}</b> items are available in stock. "
            f"Please enter a lower quantity.",
            parse_mode="HTML"
        )
        return SELECT_RECHARGE_QUANTITY

    total = product.price * Decimal(qty)

    if wallet.balance < total:
        await update.message.reply_text(
            f"💸 Insufficient balance.\n\n"
            f"💰 Required: ${normalize_amount(total)}\n"
            f"🔻 Your Balance: ${normalize_amount(wallet.balance)}"
        )
        return ConversationHandler.END

    # Store data for confirmation
    context.user_data["pending_qty"] = qty
    context.user_data["pending_total"] = total

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="confirm_recharge_yes"),
            InlineKeyboardButton("❌ No", callback_data="confirm_recharge_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🔄 <b>Confirm Recharge Purchase</b>\n\n"
        f"• Product: <b>{product.name}</b>\n"
        f"• PUBG ID: <b>{pubg_id}</b>\n"
        f"• Quantity: <b>{qty}</b>\n"
        f"• Total: <b>${total:.2f}</b>\n"
        f"• Telegram ID: <code>{user_data.id}</code>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

    return CONFIRM_RECHARGE_PURCHASE



@block_check
async def confirm_recharge_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_recharge_no":
        await query.edit_message_text("❌ Purchase canceled.")
        context.user_data.clear()
        return ConversationHandler.END

    telegram_user = await get_or_create_telegram_user(query.from_user)
    qty = context.user_data.get("pending_qty")
    total = context.user_data.get("pending_total")
    product_id = context.user_data.get("pending_recharge_product_id")
    pubg_id = context.user_data.get("pubg_id")

    if not qty or not total or not product_id or not pubg_id:
        await query.edit_message_text("❌ Missing purchase information. Please start again.")
        return ConversationHandler.END

    product, wallet = await get_product_and_wallet(telegram_user, product_id)

    if product.recharge_description:
        order, new_balance, used_voucher_codes, error, transaction_obj = await complete_recharge_order_with_vouchers(
            telegram_user, product, wallet, qty, total
        )

        if error == "no_voucher":
            await query.edit_message_text("⚠️ No vouchers available right now. Please try again later.")
            return ConversationHandler.END

        # ✅ Notify admin for completed order
        await notify_admin_order_completed(context.bot, order, used_voucher_codes, product, tx_id=transaction_obj.tx_id)

        if used_voucher_codes:
            voucher_text = "🔑 Voucher Codes are:\n" + "\n".join(f"<code>{code}</code>" for code in used_voucher_codes)
        else:
            voucher_text = "❌ No voucher code available right now.\n"

    else:
        order, new_balance, used_voucher_codes = await complete_recharge_without_description(
            telegram_user, product, wallet, qty, total, pubg_id
        )
        await notify_admin_order_pending(context.bot, order, used_voucher_codes, pubg_id, product, tx_id=transaction_obj.tx_id)
        voucher_text = ""  # Don't show any voucher message

    await query.edit_message_text(
        f"✅ Thank you for your purchase!\n\n"
        f"• Product: {product.name}\n"
        f"• PUBG ID: {pubg_id}\n"
        f"• Quantity: {qty}\n"
        f"• Total: ${normalize_amount(total)}\n\n"
        f"{voucher_text}"
        f"🛍️ Your order #{order.id} is now in process.\n\n"
        f"💰 Your new balance is ${normalize_amount(new_balance)}.",
        parse_mode="HTML"
    )

    context.user_data.clear()
    return ConversationHandler.END



@block_check
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = await get_categories()

    keyboard = [
        [InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")]
        for cat in categories
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Here are some Categories where you can find exciting products!!", reply_markup=reply_markup)
    
    
    
async def show_recharge_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recharge_categories = await get_recharge_categories()
    
    print('Recharge Categories: ', recharge_categories)

    keyboard = [
        [InlineKeyboardButton(recharge_cat["name"], callback_data=f"recharge_cat_{recharge_cat['id']}")]
        for recharge_cat in recharge_categories
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Here are some Recharge options where you can find exciting products!!", reply_markup=reply_markup)
    
    
    
@block_check
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
    
    
    
@block_check
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
    
    
    
@block_check
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END



@block_check
async def handle_bep20_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """State: BEP20_AMOUNT_INPUT — user types the desired deposit amount."""
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END

    raw = update.message.text.strip()
    try:
        requested = Decimal(raw).quantize(Decimal("0.01"))
        if requested <= 0:
            raise ValueError
    except Exception:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a positive number (e.g. <code>25.00</code>)\n\n"
            "To cancel, send /cancel",
            parse_mode="HTML",
        )
        return BEP20_AMOUNT_INPUT

    # Find a unique amount (auto-increment 0.01 per collision)
    adjusted = requested
    for _ in range(200):
        is_taken = await check_bep20_amount_active(adjusted)
        if not is_taken:
            break
        adjusted += Decimal("0.01")

    method = context.user_data.get("bep20_method")
    address = method["address"]
    context.user_data["bep20_requested_amount"] = requested
    context.user_data["bep20_adjusted_amount"] = adjusted

    if adjusted != requested:
        msg_text = (
            f"⚠️ <b>Amount Adjusted!</b>\n\n"
            f"<b>${requested:.2f}</b> is already reserved by another active session.\n\n"
            f"Your unique deposit amount is:\n"
            f"👉 <b><u>${adjusted:.2f} USDT</u></b>\n\n"
            f"📍 <b>Wallet Address:</b>\n<code>{address}</code>\n\n"
            f"✏️ To proceed, please type the <b>exact amount</b> shown above:\n"
            f"<code>{adjusted:.2f}</code>\n\n"
            f"🚫 To cancel, send /cancel"
        )
    else:
        msg_text = (
            f"💳 <b>BEP20 (BSC) Deposit</b>\n\n"
            f"📍 <b>Wallet Address:</b>\n<code>{address}</code>\n\n"
            f"💵 You will deposit exactly: <b>${adjusted:.2f} USDT</b>\n\n"
            f"✏️ To confirm, type the exact amount:\n"
            f"<code>{adjusted:.2f}</code>\n\n"
            f"🚫 To cancel, send /cancel"
        )

    await update.message.reply_text(msg_text, parse_mode="HTML")
    return BEP20_AMOUNT_CONFIRM


@block_check
async def handle_bep20_amount_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """State: BEP20_AMOUNT_CONFIRM — user types back the exact amount to confirm."""
    handled = await handle_text(update, context)
    if handled:
        return ConversationHandler.END

    raw = update.message.text.strip()
    expected: Decimal = context.user_data.get("bep20_adjusted_amount")
    method = context.user_data.get("bep20_method")

    if expected is None or method is None:
        await update.message.reply_text("⚠️ Session lost. Please start again.")
        return ConversationHandler.END

    try:
        typed = Decimal(raw).quantize(Decimal("0.01"))
    except Exception:
        await update.message.reply_text(
            f"❌ Please type the exact amount:\n<code>{expected:.2f}</code>",
            parse_mode="HTML",
        )
        return BEP20_AMOUNT_CONFIRM

    if typed != expected:
        await update.message.reply_text(
            f"❌ <b>Amount doesn't match!</b>\n\n"
            f"Please type exactly:\n<code>{expected:.2f}</code>",
            parse_mode="HTML",
        )
        return BEP20_AMOUNT_CONFIRM

    # ✅ Amount confirmed — create transaction, store amount, lock it
    user = await get_or_create_telegram_user(update.effective_user)
    tx = await create_topup_transaction(user.id, method["id"], note=None)
    await set_transaction_amount(tx.id, expected)
    await lock_bep20_amount(user, expected, tx)

    address = method["address"]
    keyboard = [
        [InlineKeyboardButton("✅ I have paid", callback_data=f"confirm_bep20_{tx.id}")],
        [InlineKeyboardButton("❌ Cancel Operation", callback_data=f"bep20_cancel_{tx.id}")],
    ]

    sent = await update.message.reply_text(
        f"✅ <b>Amount Confirmed!</b>\n\n"
        f"📤 Send <b>exactly <code>{expected:.2f} USDT (BEP20/BSC)</code></b> to:\n\n"
        f"<code>{address}</code>\n\n"
        f"⚠️ <b>Send the exact amount shown.</b> Any other amount will not be detected.\n\n"
        f"⏰ This session is valid for <b>20 minutes</b>.\n"
        f"🕑 This message will be deleted automatically after 20 minutes.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )

    # Auto-release lock and delete message after 20 minutes
    asyncio.create_task(
        release_bep20_after_delay(
            context.bot, update.effective_chat.id, sent.message_id, expected, delay=22 * 60
        )
    )

    context.user_data.clear()
    return ConversationHandler.END


@block_check
async def confirm_bep20_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: user clicked 'I have paid' for BEP20."""
    query = update.callback_query
    await query.answer()

    transaction_id = int(query.data.split("_")[-1])
    chat_id = update.effective_chat.id
    print(f"\n[BEP20 BOT] 'I have paid' clicked — transaction_id={transaction_id}")
    full_url = f"{settings.BOT_API_BASE_URL}/api/confirm-bep20-topup/"
    print(f"[BEP20 BOT] Calling URL: {full_url}")

    async with aiohttp.ClientSession() as http_session:
        async with http_session.post(
            f"{settings.BOT_API_BASE_URL}/api/confirm-bep20-topup/",
            json={"transaction_id": transaction_id},
        ) as resp:
            resp_status = resp.status
            resp_data = await resp.json()
            print(f"[BEP20 BOT] API response status: {resp_status}")
            print(f"[BEP20 BOT] API response body: {resp_data}")

    if resp_status == 200 and resp_data.get("success"):
        amount = resp_data["amount"]
        balance = resp_data["balance"]
        print(f"[BEP20 BOT] ✅ Payment verified — amount={amount}, new_balance={balance}")
        await query.edit_message_text(
            f"✅ <b>Payment received successfully!</b>\n\n"
            f"💰 <b>${float(amount):.2f} USDT</b> has been added to your wallet.\n"
            f"💼 <b>New Balance:</b> <code>${balance}</code>",
            parse_mode="HTML",
        )
        await show_wallet_info(chat_id, context, telegram_id=resp_data["telegram_id"])
    else:
        from datetime import datetime
        checked_at = datetime.now().strftime("%H:%M:%S")
        print(f"[BEP20 BOT] ❌ Verification failed at {checked_at} — reason: {resp_data.get('detail')}")
        keyboard = [
            [InlineKeyboardButton("🔄 Verify Again", callback_data=f"confirm_bep20_{transaction_id}")],
            [InlineKeyboardButton("❌ Cancel Operation", callback_data=f"bep20_cancel_{transaction_id}")],
        ]
        await query.edit_message_text(
            f"❌ <b>No matching deposit found.</b>\n\n"
            f"🕐 Last checked at: <code>{checked_at}</code>\n\n"
            f"Please make sure you sent the <b>exact amount</b> and wait a few moments before trying again.\n\n"
            f"🔄 Tap <b>Verify Again</b> to recheck.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )


@block_check
async def bep20_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: user clicked 'Cancel Operation' on the BEP20 payment message."""
    query = update.callback_query
    await query.answer()

    transaction_id = int(query.data.split("_")[-1])
    await cancel_bep20_transaction(transaction_id)
    await query.edit_message_text("❌ BEP20 payment operation cancelled.")