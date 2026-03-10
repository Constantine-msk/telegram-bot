import os
import re
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # Ваш Telegram ID для /stats

logging.basicConfig(level=logging.INFO)

# --- ХРАНИЛИЩЕ ---
stats = {"total": 0, "users": set()}  # В памяти (сбрасывается при рестарте)

# --- ТЕКСТЫ ---
TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Отправь номер телефона — пришлю ссылки для Telegram, WhatsApp и Viber.",
        "result": "📞 Номер: `+{number}`\n\nВыбери мессенджер:",
        "history_empty": "📋 История пуста.",
        "history_title": "🕐 Последние номера:",
        "invalid": "❌ Не похоже на номер телефона.\n\nПример: `+79001234567`",
        "lang_changed": "🇷🇺 Язык изменён на русский.",
        "referral": "🤝 Твоя реферальная ссылка:\nhttps://t.me/{bot_username}?start=ref_{user_id}\n\nПоделись с друзьями!",
        "stats_private": "📊 Статистика только для админа.",
        "cancel": "Отменено.",
        "help": (
            "ℹ️ *Как пользоваться:*\n\n"
            "Просто отправь номер телефона в любом формате:\n"
            "`+79001234567`\n`89001234567`\n`+7 (900) 123-45-67`\n\n"
            "*Команды:*\n"
            "/start — Начало\n"
            "/history — Последние номера\n"
            "/lang — Сменить язык EN/RU\n"
            "/ref — Реферальная ссылка\n"
            "/stats — Статистика (только админ)\n"
            "/help — Помощь"
        ),
    },
    "en": {
        "welcome": "👋 Hi! Send a phone number — I'll generate links for Telegram, WhatsApp and Viber.",
        "result": "📞 Number: `+{number}`\n\nChoose messenger:",
        "history_empty": "📋 History is empty.",
        "history_title": "🕐 Recent numbers:",
        "invalid": "❌ Doesn't look like a phone number.\n\nExample: `+79001234567`",
        "lang_changed": "🇬🇧 Language changed to English.",
        "referral": "🤝 Your referral link:\nhttps://t.me/{bot_username}?start=ref_{user_id}\n\nShare with friends!",
        "stats_private": "📊 Stats are for admin only.",
        "cancel": "Cancelled.",
        "help": (
            "ℹ️ *How to use:*\n\n"
            "Just send a phone number in any format:\n"
            "`+79001234567`\n`89001234567`\n`+7 (900) 123-45-67`\n\n"
            "*Commands:*\n"
            "/start — Start\n"
            "/history — Recent numbers\n"
            "/lang — Switch language EN/RU\n"
            "/ref — Referral link\n"
            "/stats — Statistics (admin only)\n"
            "/help — Help"
        ),
    }
}


def get_lang(context) -> str:
    return context.user_data.get("lang", "ru")


def t(key: str, context, **kwargs) -> str:
    lang = get_lang(context)
    text = TEXTS[lang].get(key, TEXTS["ru"][key])
    return text.format(**kwargs) if kwargs else text


def parse_phone(raw: str):
    digits = re.sub(r"[^\d]", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) < 10 or len(digits) > 15:
        return None
    return digits


def messenger_keyboard(number: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
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
    ])


# --- КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats["users"].add(user.id)

    # Реферальная система
    args = context.args
    if args and args[0].startswith("ref_"):
        ref_id = args[0].replace("ref_", "")
        if ref_id.isdigit() and int(ref_id) != user.id:
            context.user_data["referred_by"] = int(ref_id)

    await update.message.reply_text(
        t("welcome", context),
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t("help", context), parse_mode="Markdown")


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = context.user_data.get("history", [])
    if not history:
        await update.message.reply_text(t("history_empty", context))
        return

    lines = [t("history_title", context)]
    for i, entry in enumerate(reversed(history[-5:]), 1):
        lines.append(f"{i}. `+{entry['number']}` — {entry['date']}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📞 +{e['number']}", callback_data=f"repeat:{e['number']}")]
        for e in reversed(history[-5:])
    ])
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = get_lang(context)
    new_lang = "en" if current == "ru" else "ru"
    context.user_data["lang"] = new_lang
    await update.message.reply_text(t("lang_changed", context))


async def ref_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = await context.bot.get_me()
    await update.message.reply_text(
        t("referral", context, bot_username=bot.username, user_id=user.id),
        parse_mode="Markdown"
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if ADMIN_ID and user.id != ADMIN_ID:
        await update.message.reply_text(t("stats_private", context))
        return

    await update.message.reply_text(
        f"📊 *Статистика бота*\n\n"
        f"🔢 Всего запросов: `{stats['total']}`\n"
        f"👥 Уникальных пользователей: `{len(stats['users'])}`",
        parse_mode="Markdown"
    )


# --- СООБЩЕНИЯ ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    stats["users"].add(user.id)

    number = parse_phone(text)

    if not number:
        await update.message.reply_text(t("invalid", context), parse_mode="Markdown")
        return

    # Сохранить в историю
    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append({
        "number": number,
        "date": datetime.now().strftime("%d.%m %H:%M")
    })
    context.user_data["history"] = context.user_data["history"][-10:]

    stats["total"] += 1

    await update.message.reply_text(
        t("result", context, number=number),
        parse_mode="Markdown",
        reply_markup=messenger_keyboard(number)
    )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "history":
        history = context.user_data.get("history", [])
        if not history:
            await query.message.reply_text(t("history_empty", context))
            return
        lines = [t("history_title", context)]
        for i, entry in enumerate(reversed(history[-5:]), 1):
            lines.append(f"{i}. `+{entry['number']}` — {entry['date']}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📞 +{e['number']}", callback_data=f"repeat:{e['number']}")]
            for e in reversed(history[-5:])
        ])
        await query.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    elif query.data == "new":
        await query.message.reply_text(
            t("welcome", context),
            parse_mode="Markdown"
        )

    elif query.data.startswith("repeat:"):
        number = query.data.replace("repeat:", "")
        await query.message.reply_text(
            t("result", context, number=number),
            parse_mode="Markdown",
            reply_markup=messenger_keyboard(number)
        )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("ref", ref_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ LMWTOT бот запущен!")
    app.run_polling()
