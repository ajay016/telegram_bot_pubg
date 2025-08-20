from functools import wraps
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
    @wraps(func)
    async def wrapper(*args, **kwargs):
        update = None

        # Try to extract `update` from args
        for arg in args:
            if isinstance(arg, Update):
                update = arg
                break

        # Fallback to kwargs
        if not update:
            update = kwargs.get('update')

        # If update is found, check if user is blocked
        if update:
            telegram_id = update.effective_user.id
            if await is_user_blocked(telegram_id):
                if update.message:
                    await update.message.reply_text("🚫 You are blocked from using this bot.")
                elif update.callback_query:
                    await update.callback_query.answer("🚫 You are blocked from using this bot.", show_alert=True)
                return

        return await func(*args, **kwargs)
    return wrapper