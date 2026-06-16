"""BilimAI - Telegram bot.

Ishga tushirish:
    1) .env faylga TELEGRAM_BOT_TOKEN va AI kalitini qo'ying
    2) python bot.py
"""

import logging

from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bilim_ai import ai, config
from bilim_ai import presentation as pptx_gen
from bilim_ai.prompt import WELCOME_MESSAGE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("BilimAI.bot")

# Telegram bitta xabarda 4096 belgidan ko'p qabul qilmaydi
TG_LIMIT = 4096


def _split(text: str, limit: int = TG_LIMIT):
    """Uzun javobni bo'laklarga ajratadi."""
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        WELCOME_MESSAGE, parse_mode=constants.ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Savolingizni shunchaki yozing. Masala rasmini yuborsangiz ham yechib beraman.\n\n"
        "Buyruqlar:\n"
        "/start - boshlash\n"
        "/help - yordam\n"
        "/prezentatsiya <mavzu> - PowerPoint prezentatsiya yaratish\n\n"
        "Masalan: /prezentatsiya Suvning tabiatdagi aylanishi"
    )


async def presentation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    topic = " ".join(context.args).strip()
    if not topic:
        await update.message.reply_text(
            "Mavzuni yozing. Masalan:\n/prezentatsiya Quyosh sistemasi"
        )
        return
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_DOCUMENT
    )
    await update.message.reply_text(f"📊 \"{topic}\" mavzusida prezentatsiya tayyorlanmoqda…")
    try:
        data, title = await _run(pptx_gen.create_presentation, topic, 8)
        import io

        bio = io.BytesIO(data)
        safe = "".join(c for c in title if c.isalnum() or c in " -_").strip() or "prezentatsiya"
        bio.name = f"{safe}.pptx"
        await update.message.reply_document(
            document=bio,
            filename=bio.name,
            caption=f"✅ \"{title}\" tayyor! PowerPoint yoki Google Slides'da oching.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Prezentatsiya xatosi")
        await update.message.reply_text(f"⚠️ Prezentatsiya yaratishda xatolik: {exc}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = update.message.text
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    try:
        answer = await _run(ai.ask, question)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI xatosi")
        answer = f"⚠️ Xatolik yuz berdi: {exc}"
    for chunk in _split(answer):
        await update.message.reply_text(chunk)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    try:
        # Eng katta o'lchamli rasmni olamiz
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        image_bytes = bytes(await tg_file.download_as_bytearray())
        caption = update.message.caption or ""
        answer = await _run(
            ai.ask_with_image, image_bytes, "image/jpeg", caption
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rasm bilan ishlashda xato")
        answer = f"⚠️ Rasmni yechishda xatolik: {exc}"
    for chunk in _split(answer):
        await update.message.reply_text(chunk)


async def _run(func, *args):
    """Bloklovchi (sync) AI chaqiruvini alohida thread'da ishga tushiradi."""
    import asyncio

    return await asyncio.to_thread(func, *args)


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN topilmadi! .env faylga botingiz tokenini qo'shing "
            "(@BotFather dan oling)."
        )
    if not config.is_configured():
        logger.warning(
            "Diqqat: AI kaliti (GEMINI_API_KEY yoki GROQ_API_KEY) sozlanmagan. "
            "Bot ishga tushadi, lekin savollarga javob bera olmaydi."
        )

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("prezentatsiya", presentation_command))
    app.add_handler(CommandHandler("presentation", presentation_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("BilimAI bot ishga tushdi. Provayder: %s", config.active_provider() or "yo'q")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
