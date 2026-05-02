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








def normalize_amount(val):
    return str(Decimal(val).normalize())



@sync_to_async
def get_admin_chat_id():
    obj = AdminChatID.objects.first()
    return obj.chat_id if obj else None


def fmt_money(v) -> str:
    """
    Show 2 decimals normally.
    If value needs more precision, show up to 4 decimals.
    Never show scientific notation.
    """
    v = Decimal(str(v))  # safe conversion from float/Decimal
    q4 = v.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
    q2 = v.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # if more precision than 2dp exists -> show 4dp
    if q4 != q2.quantize(Decimal("0.0001")):
        return f"{q4:.4f}"
    return f"{q2:.2f}"



async def delete_message_after_delay(bot, chat_id, message_id, delay=20*60):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Failed to delete message: {e}")



async def notify_admin_order_completed(bot: Bot, order, assigned_codes, product, tx_id=None):
    admin_chat_id = await get_admin_chat_id()
    if not admin_chat_id:
        return  # No admin chat ID set, so don't send

    # voucher_lines = "\n".join([f"🎟️ <code>{code}</code>" for code in assigned_codes])
    voucher_text = "\n".join(assigned_codes)
    file_buffer = io.StringIO(voucher_text)
    
    slug_title = product.slug.replace("-", " ").replace("_", " ").upper()
    dt_str = timezone.localtime(order.created_at).strftime("%Y-%m-%d_%H-%M-%S")
    file_buffer.name = f"{slug_title}_{dt_str}.txt"
    
    message = (
        f"📦 <b>New Completed Order</b>\n\n"
        f"🧑 User: <code>{order.user.telegram_id}</code>\n"
        f"🆔 Order ID: <code>{order.id}</code>\n"
        f"🧾 Tx ID: <code>{tx_id or 'N/A'}</code>\n"
        f"💲 Total: <b>${normalize_amount(order.total_price)}</b>\n"
        f"📅 Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"✅ Status: <b>{order.status}</b>\n\n"
        f"📄 Voucher codes are attached as a text file."
    )

    # Send message and attached voucher file in one block
    await bot.send_message(
        chat_id=admin_chat_id,
        text=message,
        parse_mode="HTML"
    )

    file_buffer.seek(0)
    await bot.send_document(
        chat_id=admin_chat_id,
        document=InputFile(file_buffer, filename=file_buffer.name),
        caption="🎁 Voucher Codes"
    )
    
    

async def notify_admin_order_pending(bot: Bot, order, assigned_codes, game_id, product, tx_id=None):
    admin_chat_id = await get_admin_chat_id()
    if not admin_chat_id:
        return  # No admin chat ID set, so don't send

    voucher_text = "\n".join(assigned_codes)
    file_buffer = io.StringIO(voucher_text)
    
    slug_title = product.slug.replace("-", " ").replace("_", " ").upper()
    dt_str = timezone.localtime(order.created_at).strftime("%Y-%m-%d_%H-%M-%S")
    file_buffer.name = f"{slug_title}_{dt_str}.txt"
    
    message = (
        f"📦 <b>New Completed Order</b>\n\n"
        f"🧑 User: <code>{order.user.telegram_id}</code>\n"
        f"🧑 <b>Game ID:</b> <code>{game_id}</code>\n"
        f"🆔 Order ID: <code>{order.id}</code>\n"
        f"🧾 Tx ID: <code>{tx_id or 'N/A'}</code>\n"
        f"💲 Total: <b>${normalize_amount(order.total_price)}</b>\n"
        f"📅 Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"✅ Status: <b>{order.status}</b>\n\n"
        f"📄 Voucher codes are attached as a text file."
    )

    await bot.send_message(
        chat_id=admin_chat_id,
        text=message,
        parse_mode="HTML"
    )

    file_buffer.seek(0)
    await bot.send_document(
        chat_id=admin_chat_id,
        document=InputFile(file_buffer, filename=file_buffer.name),
        caption="🎁 Voucher Codes"
    )
    
    
    
async def _send_broadcast(announcement_id):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    announcement = await Announcement.objects.aget(id=announcement_id)
    
    users = TelegramUser.objects.all()
    
    caption = f"📢 <b>{announcement.title or 'Announcement'}</b>\n\n{announcement.message}"

    async for user in users:
        try:
            # 1) Send Image or Text
            if announcement.image and hasattr(announcement.image, "path"):
                with open(announcement.image.path, "rb") as f:
                    await bot.send_photo(
                        chat_id=user.telegram_id, 
                        photo=f, 
                        caption=caption, 
                        parse_mode="HTML"
                    )
            else:
                await bot.send_message(
                    chat_id=user.telegram_id, 
                    text=caption, 
                    parse_mode="HTML"
                )

            # 2) Send Attachment
            if announcement.attachment and hasattr(announcement.attachment, "path"):
                with open(announcement.attachment.path, "rb") as f:
                    await bot.send_document(
                        chat_id=user.telegram_id, 
                        document=f, 
                        caption="📎 Attachment"
                    )
            
            # 🛡️ Rate limit protection
            await asyncio.sleep(0.05)

        except Exception as e:
            print(f"Failed to send to {user.telegram_id}: {e}")

    announcement.is_broadcasted = True
    announcement.broadcasted_at = timezone.now()
    await announcement.asave()


def trigger_broadcast(announcement_id):
    """Synchronous wrapper to call from Django Admin"""
    asyncio.run(_send_broadcast(announcement_id))