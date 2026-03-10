import os
import re
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройка логирования для Railway (чтобы видеть ошибки в консоли)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Чтение переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# Временное хранилище (сбрасывается при перезапуске контейнера на Railway)
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
        "help": "ℹ️ Отправь номер в любом формате, например: `+79001234567` или `89001234567`."
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
            InlineKeyboardButton("📳 Viber", url=f"viber://chat?number=%2B{number}"),
        ],
        [
            InlineKeyboardButton("📋 История", callback_data="history"),
            InlineKeyboardButton("🔄 Ещё номер", callback_data="new"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- ОБРАБОТЧИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats
