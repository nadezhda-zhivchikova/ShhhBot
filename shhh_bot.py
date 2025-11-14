import os
import logging
from datetime import datetime, time
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

# ========== НАСТРОЙКИ БОТА ==========

# Токен бота: лучше передавать через переменную окружения TELEGRAM_BOT_TOKEN
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")

# Часовой пояс (можешь поменять при необходимости)
TZ = ZoneInfo("Asia/Tbilisi")

# Время начала и конца "тихого режима"
# Например: QUIET_START = 19:00, QUIET_END = 08:00
QUIET_START = time(19, 0)  # 22:00
QUIET_END = time(8, 0)     # 08:00

# Текст напоминания
REMINDER_TEXT = (
  "🌙 Shhh... It’s quiet hours in this chat right now."
)


def is_quiet_time(now: datetime) -> bool:
    """
    Проверяем, попадает ли текущее время в тихий период.
    Учитываем случай, когда тихий период 'переламывает' полночь (22:00–08:00).
    """
    current_t = now.time()

    if QUIET_START < QUIET_END:
        # Тихий период внутри одних суток, напр. 20:00–23:00
        return QUIET_START <= current_t < QUIET_END
    else:
        # Тихий период через полночь, напр. 22:00–08:00
        return current_t >= QUIET_START or current_t < QUIET_END


async def message_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для всех сообщений в группе.
    Если сейчас тихое время — отправляем напоминание.
    """
    message = update.message
    if message is None:
        # Например, это может быть служебное обновление, которое нам не нужно
        return

    chat = message.chat

    # Работаем только в группах/супергруппах
    if chat.type not in ("group", "supergroup"):
        return

    # Можно игнорировать сообщения от других ботов
    if message.from_user and message.from_user.is_bot:
        return

    now = datetime.now(TZ)

    if is_quiet_time(now):
        logger.info(
            "Quiet time message in chat %s (%s) from user %s",
            chat.id,
