import os
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo  # стандартная библиотека, Python 3.9+

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

# Токен бота: читаем ТОЛЬКО из переменной окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Часовой пояс
TZ = ZoneInfo("Asia/Tbilisi")

# Время начала и конца "тихого режима"
# Например: QUIET_START = 19:00, QUIET_END = 08:00
QUIET_START = time(19, 0)
QUIET_END = time(10, 0)

REMINDER_TEXT = (
    "🌙 Shhh...\n"
    "ახლა ჩეთში მშვიდი საათებია\n"
    "Сейчас тихое время в этом чате\n"
    "It’s quiet hours in this chat right now\n"
)

# Антиспам: минимальный интервал между напоминаниями в одном чате
MIN_REMINDER_INTERVAL = timedelta(minutes=5)

# Здесь будем хранить время последнего напоминания по chat.id
last_reminder_time: dict[int, datetime] = {}


def is_quiet_time(now: datetime) -> bool:
    """Проверяем, попадает ли текущее время в тихий период."""
    current_t = now.time()

    if QUIET_START < QUIET_END:
        # Тихий период внутри одних суток, напр. 20:00–23:00
        return QUIET_START <= current_t < QUIET_END
    else:
        # Тихий период через полночь, напр. 22:00–08:00
        return current_t >= QUIET_START or current_t < QUIET_END


def can_send_reminder(chat_id: int, now: datetime) -> bool:
    """Проверяем, прошёл ли достаточный интервал с прошлого напоминания для этого чата."""
    last_time = last_reminder_time.get(chat_id)
    if last_time is None:
        # Ещё не напоминали ни разу
        return True
    return now - last_time >= MIN_REMINDER_INTERVAL


def update_last_reminder_time(chat_id: int, now: datetime) -> None:
    last_reminder_time[chat_id] = now


async def message_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для всех сообщений в группе.
    Если сейчас тихое время — отправляем напоминание (с антиспамом).
    """
    message = update.message
    if message is None:
        return

    chat = message.chat

    # Работаем только в группах/супергруппах
    if chat.type not in ("group", "supergroup"):
        return

    # Игнорируем сообщения от ботов
    if message.from_user and message.from_user.is_bot:
        return

    now = datetime.now(TZ)

    if not is_quiet_time(now):
        return

    # Антиспам-проверка
    if not can_send_reminder(chat.id, now):
        logger.info(
            "Skip reminder in chat %s (%s) due to anti-spam",
            chat.id,
            chat.title,
        )
        return

    # Обновляем время последнего напоминания и отправляем сообщение
    update_last_reminder_time(chat.id, now)

    logger.info(
        "Send quiet-time reminder in chat %s (%s) from user %s",
        chat.id,
        chat.title,
        message.from_user.username if message.from_user else "unknown",
    )
    await message.reply_text(REMINDER_TEXT)


def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "На Railway добавь переменную окружения TELEGRAM_BOT_TOKEN с токеном бота."
        )

    app = ApplicationBuilder().token(TOKEN).build()

    # Обрабатываем все сообщения, кроме команд
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            message_control,
        )
    )

    logger.info("ShhhBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
