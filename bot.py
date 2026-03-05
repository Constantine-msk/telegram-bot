import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = 8137653684:AAFKpAWxC9bcvEuOhck2xrO_hDTtNF1FDuw


def format_phone(raw: str) -> str | None:
    digits = re.sub(r"[^\d]", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) < 10 or len(digits) > 15:
        return None
    return digits


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Отправь мне номер телефона — пришлю ссылки для открытия чата в:\n\n"
        "✈️ Telegram\n"
        "💬 WhatsApp\n\n"
        "Примеры форматов:\n"
        "• +79001234567\n"
        "• 89001234567\n"
        "• +7 (900) 123-45-67"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    digits = format_phone(text)

    if not digits:
        await update.message.reply_text("❌ Не похоже на номер телефона. Попробуйте: +79001234567")
        return

    tg_link = f"https://t.me/+{digits}"
    wa_link = f"https://wa.me/{digits}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✈️ Открыть в Telegram", url=tg_link)],
        [InlineKeyboardButton("💬 Открыть в WhatsApp", url=wa_link)],
    ])

    await update.message.reply_text(
        f"📞 Номер: +{digits}\n\n"
        f"✈️ Telegram: {tg_link}\n"
        f"💬 WhatsApp: {wa_link}",
        reply_markup=keyboard
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()
