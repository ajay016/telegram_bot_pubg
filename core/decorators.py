from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from .models import TelegramUser
from telegram.ext import ConversationHandler



@sync_to_async
def is_user_blocked(telegram_id):
    try:
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        return user.is_blocked
    except TelegramUser.DoesNotExist:
        return False
    

def block_check(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id
        if await is_user_blocked(telegram_id):
            await update.message.reply_text("🚫 You are blocked from using this bot.")
            return
        return await func(update, context)
    return wrapper