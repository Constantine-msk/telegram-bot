import os
import re
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

stats = {"total": 0, "users": set()}

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Отправь номер телефона — пришлю ссылки для Telegram, WhatsApp и Viber.",
        "result": "📞 Номер: `+{number}`\n\nВыбери мессенджер:",
        "history_empty": "📋 История пуста.",
        "history_title": "🕐 Последние номера:",
        "invalid": "❌ Не похоже на номер телефона.\n\nПример: `+79001234567`",
        "lang_changed": "🇷🇺 Язык изменён на русский.",
        "referral": "🤝 Твоя реферальная ссылка:\nhttps://t.me/{bot_username}?start=ref_{user_id}",
        "stats_private": "📊 Статистика только для админа.",
        "help": "ℹ️ Отправь номер в любом формате, например: `+79001234567`."
    },
    "en": {
        "welcome": "👋 Hi! Send a phone number — I'll generate links for Telegram, WhatsApp and Viber.",
        "result": "📞 Number: `+{number}`\n\nChoose messenger:",
        "history_empty": "📋 History is empty.",
        "history_title": "🕐 Recent numbers:",
        "invalid": "❌ Doesn't look like a phone number.\n\nExample: +79001234567",
        "lang_changed": "🇬🇧 Language changed to English.",
        "referral": "🤝 Your referral link:\nhttps://t.me/{bot_username}?start=ref_{user_id}",
        "stats_private": "📊 Stats are for admin only.",
        "help": "ℹ️ Send a phone number in any format, e.g.: +79001234567"
    }
}

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "ru")

def t(key: str, context: ContextTypes.DEFAULT_TYPE, **kwargs) -> str:
    lang = get_lang(context)
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, TEXTS["ru"][key])
    return text.format(**kwargs) if kwargs else text

def parse_phone(raw: str):
    digits = re.sub(r"[^\d]", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) < 7 or len(digits) > 15:
        return None
    return digits

def messenger_keyboard(number: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✈️ Telegram", url=f"https://t.me/+{number}"),
            InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{number}"),
        ],
        [
            InlineKeyboardButton("📳 Viber", url=f"https://viber.click/{number}"),
        ],
        [
            InlineKeyboardButton("📋 История", callback_data="history"),
            InlineKeyboardButton("🔄 Ещё номер", callback_data="new"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats["users"].add(user_id)
    await update.message.reply_text(t("welcome", context), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    raw_text = update.message.text.strip()
    number = parse_phone(raw_text)
    if not number:
        await update.message.reply_text(t("invalid", context), parse_mode="Markdown")
        return
    if "history" not in context.user_data:
        context.user_data["history"] = []
    entry = {"number": number, "date": datetime.now().strftime("%d.%m %H:%M")}
    context.user_data["history"].append(entry)
    context.user_data["history"] = context.user_data["history"][-5:]
    stats["total"] += 1
    stats["users"].add(update.effective_user.id)
    await update.message.reply_text(
        t("result", context, number=number),
        parse_mode="Markdown",
        reply_markup=messenger_keyboard(number)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()
    if data == "history":
        history = context.user_data.get("history", [])
        if not history:
            await query.message.reply_text(t("history_empty", context))
            return
        lines = [t("history_title", context)]
        btns = []
        for e in reversed(history):
            lines.append(f"• `+{e['number']}`")
            btns.append([InlineKeyboardButton(f"📞 +{e['number']}", callback_data=f"repeat:{e['number']}")])
        await query.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "new":
        await query.message.reply_text(t("welcome", context))
    elif data.startswith("repeat:"):
        num = data.split(":")[1]
        await query.message.reply_text(t("result", context, number=num), parse_mode="Markdown", reply_markup=messenger_keyboard(num))

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"📊 Запросов: {stats['total']}\nUsers: {len(stats['users'])}")

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = get_lang(context)
    context.user_data["lang"] = "en" if current == "ru" else "ru"
    await update.message.reply_text(t("lang_changed", context))

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
    else:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats_cmd))
        app.add_handler(CommandHandler("lang", lang_cmd))
        app.add_handler(CallbackQueryHandler(handle_button))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.run_polling(drop_pending_updates=True)
