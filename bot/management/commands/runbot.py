from email.mime import application
import os
import django
import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters
)

# 1. Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "telegram_bot_project.settings")
django.setup()

# 2. Import your modules AFTER Django is setup
from bot.tg_bot.states import *
from bot.tg_bot.handlers import (
    handle_manual_purchase_confirmation, handle_manual_quantity_input, start, button_handler, handle_text, handle_amount_input,
    handle_quantity_input, handle_purchase_confirmation,
    handle_recharge_quantity_input, confirm_recharge_purchase_callback, cancel,
    handle_bep20_amount_input, handle_bep20_amount_confirm, confirm_bep20_callback, bep20_cancel_callback,
)

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# 3. Define Bot Commands
async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Restart the bot"),
        BotCommand("cancel", "Cancel current operation")
    ])

# 4. Setup Conversation Handler
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CallbackQueryHandler(button_handler),
    ],
    states={
        AMOUNT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount_input),
        ],
        SELECT_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity_input)
        ],
        TYPING_RECHARGE_PUBG_ID: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
        ],
        SELECT_RECHARGE_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recharge_quantity_input)
        ],
        CONFIRM_PURCHASE: [
            CallbackQueryHandler(handle_purchase_confirmation)
        ],
        CONFIRM_RECHARGE_PURCHASE: [
            CallbackQueryHandler(confirm_recharge_purchase_callback)
        ],
        SELECT_MANUAL_QUANTITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_quantity_input)
        ],
        CONFIRM_MANUAL_PURCHASE: [
            CallbackQueryHandler(handle_manual_purchase_confirmation)
        ],
        BEP20_AMOUNT_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bep20_amount_input)
        ],
        BEP20_AMOUNT_CONFIRM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bep20_amount_confirm)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
    ],
)

# 5. Define the Django Command
class Command(BaseCommand):
    help = "Run the Telegram bot and WebSocket listener"

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_handler(CallbackQueryHandler(confirm_bep20_callback, pattern=r"^confirm_bep20_\d+$"))
        application.add_handler(CallbackQueryHandler(bep20_cancel_callback, pattern=r"^bep20_cancel_\d+$"))

        async def post_init(app):
            # Set commands
            await set_commands(app)
            
            # Uncomment and import this when you are ready to use websockets again
            # asyncio.create_task(bybit_transaction_listener())
            print("🌐 WebSocket listener ready")

        application.post_init = post_init

        print("🤖 Bot is running...")
        application.run_polling()