import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8137653684:AAFKpAWxC9bcvEuOhck2xrO_hDTtNF1FDuw"


def format_phone(phone: str) -> str | None:
    """Очищает номер и возвращает ссылку или None если номер некорректный."""
    # Убираем всё кроме цифр и +
    digits = re.sub(r"[^\d]", "", phone)

    # Если начинается с 8 — заменяем на 7 (российские номера)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]

    # Проверяем длину (10-15 цифр по стандарту E.164)
    if len(digits) < 10 or len(digits) > 15:
        return None

    return f"https://t.me/+{digits}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Отправь мне номер телефона, и я пришлю ссылку для открытия чата в Telegram.\n\n"
        "Примеры форматов:\n"
        "• +79001234567\n"
        "• 89001234567\n"
        "• 79001234567\n"
        "• +7 (900) 123-45-67"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    link = format_phone(text)

    if link:
        await update.message.reply_text(
            f"✅ Ссылка для открытия чата:\n\n{link}\n\n"
            f"Нажмите на ссылку — Telegram откроет диалог с этим пользователем."
        )
    else:
        await update.message.reply_text(
            "❌ Не похоже на номер телефона. Попробуйте ещё раз.\n\n"
            "Пример: +79001234567"
        )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()
