import os
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========== НАСТРОЙКИ ==========

# Токен бота: лучше передавать через переменную окружения TELEGRAM_BOT_TOKEN
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8588146758:AAHTib20vMVE_0J0fqmTI03ZzPBlwuYa88M")

#TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
#if not TOKEN:
#    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

# БАЗОВЫЙ URL сервиса на Railway, например:
# https://shhhbot-production.up.railway.app
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://start-production-40ad.up.railway.app")
if not WEBHOOK_BASE_URL:
    raise RuntimeError("WEBHOOK_BASE_URL is not set")

# Railway обычно прокидывает PORT в переменную окружения
PORT = int(os.getenv("PORT", "8080"))

# Часовой пояс
TZ = ZoneInfo("Asia/Tbilisi")

# Тихие часы
QUIET_START = time(19, 0)
QUIET_END = time(8, 0)

REMINDER_TEXT = (
    """🌙 Shhh...\n 
        ახლა ჩეთში მშვიდი საათებია\n
        Сейчас тихое время в этом чате\n
        It’s quiet hours in this chat right now\n
    """
)

# Антиспам
MIN_REMINDER_INTERVAL = timedelta(minutes=5)
last_reminder_time: dict[int, datetime] = {}


def is_quiet_time(now: datetime) -> bool:
    current_t = now.time()
    if QUIET_START < QUIET_END:
        return QUIET_START <= current_t < QUIET_END
    else:
        return current_t >= QUIET_START or current_t < QUIET_END


def can_send_reminder(chat_id: int, now: datetime) -> bool:
    last_time = last_reminder_time.get(chat_id)
    if last_time is None:
        return True
    return now - last_time >= MIN_REMINDER_INTERVAL


def update_last_reminder_time(chat_id: int, now: datetime) -> None:
    last_reminder_time[chat_id] = now


async def message_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    chat = message.chat

    if chat.type not in ("group", "supergroup"):
        return

    if message.from_user and message.from_user.is_bot:
        return

    now = datetime.now(TZ)

    if not is_quiet_time(now):
        return

    if not can_send_reminder(chat.id, now):
        logger.info(
            "Skip reminder in chat %s (%s) due to anti-spam",
            chat.id,
            chat.title,
        )
        return

    update_last_reminder_time(chat.id, now)

    logger.info(
        "Send quiet-time reminder in chat %s (%s) from user %s",
        chat.id,
        chat.title,
        message.from_user.username if message.from_user else "unknown",
    )
    await message.reply_text(REMINDER_TEXT)

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_control,
        )
    )

    # URL, по которому Telegram будет слать обновления
    webhook_url = f"{WEBHOOK_BASE_UR}/{TOKEN}"

    logger.info("Starting ShhhBot with webhook at %s", webhook_url)

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        path=TOKEN,              # <-- было url_path=TOKEN, должно быть path
        webhook_url=webhook_url, # внешний URL
        allowed_updates=Update.ALL_TYPES,
    )

if __name__ == "__main__":
    main()

