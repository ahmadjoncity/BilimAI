"""BilimAI - Telegram bot.

Imkoniyatlar:
    • Savol-javob (matn) — BEPUL
    • Rasmdagi masalani yechish — BEPUL
    • 🎨 Rasm yaratish (/rasm) — PULLIK OBUNA
    • 📊 Prezentatsiya yaratish (/prezentatsiya) — PULLIK OBUNA

Ishga tushirish:
    1) .env faylga TELEGRAM_BOT_TOKEN va AI kalitini qo'ying
    2) python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os

from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bilim_ai import ai, config, image_gen, presentation, subscription
from bilim_ai.prompt import WELCOME_MESSAGE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("BilimAI.bot")

# Telegram bitta xabarda 4096 belgidan ko'p qabul qilmaydi
TG_LIMIT = 4096

ADMIN_CONTACT = "@ravshanovichch"


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


async def _run(func, *args):
    """Bloklovchi (sync) chaqiruvni alohida thread'da ishga tushiradi."""
    return await asyncio.to_thread(func, *args)


def _premium_required_text() -> str:
    return (
        "🔒 *Bu funksiya faqat pullik obuna uchun.*\n\n"
        "🎨 Rasm yaratish va 📊 prezentatsiya tayyorlash — premium imkoniyatlar.\n\n"
        f"Obuna bo'lish uchun admin bilan bog'laning: {ADMIN_CONTACT}\n\n"
        "Obuna bo'lgach, sizning Telegram ID raqamingiz tizimga qo'shiladi va "
        "barcha funksiyalar ochiladi. (ID ni bilish uchun /id buyrug'ini bosing)"
    )


def _is_premium(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    return subscription.is_premium(user.id, user.username)


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    return subscription.is_admin(user.id, user.username)


# ----------------------- Asosiy buyruqlar -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        WELCOME_MESSAGE, parse_mode=constants.ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*BilimAI buyruqlari:*\n\n"
        "📚 *Bepul:*\n"
        "• Savolingizni yozing — javob beraman\n"
        "• Masala rasmini yuboring — yechib beraman\n\n"
        "💎 *Pullik obuna (premium):*\n"
        "• `/rasm tavsif` — tavsif bo'yicha rasm yarataman\n"
        "• `/prezentatsiya mavzu` — taqdimot (.pptx) tayyorlayman\n\n"
        "ℹ️ *Boshqa:*\n"
        "• /obuna — obuna haqida ma'lumot\n"
        "• /id — Telegram ID raqamingiz\n"
        "• /help — yordam\n\n"
        f"Pullik obuna uchun: {ADMIN_CONTACT}"
    )
    await update.message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    status = "💎 Premium" if _is_premium(update) else "🆓 Oddiy (bepul)"
    await update.message.reply_text(
        f"🆔 Sizning Telegram ID: `{user.id}`\n"
        f"👤 Username: @{user.username if user.username else '—'}\n"
        f"Holat: {status}\n\n"
        f"Pullik obuna uchun ID raqamingizni adminга yuboring: {ADMIN_CONTACT}",
        parse_mode=constants.ParseMode.MARKDOWN,
    )


async def obuna(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _is_premium(update):
        await update.message.reply_text(
            "✅ Sizda *premium obuna* faol! Barcha funksiyalardan foydalanishingiz mumkin:\n"
            "🎨 /rasm — rasm yaratish\n"
            "📊 /prezentatsiya — taqdimot tayyorlash",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    await update.message.reply_text(
        "💎 *PULLIK OBUNA (PREMIUM)*\n\n"
        "Premium obuna bilan quyidagilar ochiladi:\n"
        "🎨 *Rasm yaratish* — istalgan tavsif bo'yicha sun'iy intellekt rasm chizadi\n"
        "📊 *Prezentatsiya* — mavzu bo'yicha tayyor .pptx taqdimot\n\n"
        f"📩 Obuna bo'lish uchun admin bilan bog'laning: {ADMIN_CONTACT}\n\n"
        "Yozganda /id buyrug'i orqali olingan ID raqamingizni yuboring.",
        parse_mode=constants.ParseMode.MARKDOWN,
    )


# ----------------------- Premium: Rasm yaratish -----------------------

async def rasm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_premium(update):
        await update.message.reply_text(
            _premium_required_text(), parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text(
            "🎨 Rasm yaratish uchun tavsif yozing.\n"
            "Masalan: `/rasm quyosh botayotgan tog'lar ustida burgut`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=constants.ChatAction.UPLOAD_PHOTO,
    )
    notice = await update.message.reply_text("🎨 Rasm yaratilmoqda… (10-30 soniya)")
    try:
        image_bytes = await _run(image_gen.generate_image, prompt)
        await update.message.reply_photo(photo=image_bytes, caption=f"🎨 {prompt}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rasm yaratish xatosi")
        await update.message.reply_text(f"⚠️ Rasm yaratib bo'lmadi: {exc}")
    finally:
        try:
            await notice.delete()
        except Exception:  # noqa: BLE001
            pass


# ----------------------- Premium: Prezentatsiya -----------------------

async def prezentatsiya(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_premium(update):
        await update.message.reply_text(
            _premium_required_text(), parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    topic = " ".join(context.args) if context.args else ""
    if not topic:
        await update.message.reply_text(
            "📊 Prezentatsiya uchun mavzu yozing.\n"
            "Masalan: `/prezentatsiya Suv aylanishi`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=constants.ChatAction.UPLOAD_DOCUMENT,
    )
    notice = await update.message.reply_text(
        "📊 Prezentatsiya tayyorlanmoqda… (15-40 soniya)"
    )
    path = None
    try:
        path = await _run(presentation.create_presentation, topic, 8)
        safe_name = "".join(
            c for c in topic if c.isalnum() or c in " _-"
        ).strip()[:40] or "prezentatsiya"
        with open(path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"{safe_name}.pptx",
                caption=f"📊 «{topic}» — tayyor!",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Prezentatsiya xatosi")
        await update.message.reply_text(
            f"⚠️ Prezentatsiya tayyorlab bo'lmadi: {exc}"
        )
    finally:
        try:
            await notice.delete()
        except Exception:  # noqa: BLE001
            pass
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


# ----------------------- Admin buyruqlari -----------------------

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return
    if not context.args:
        await update.message.reply_text(
            "Foydalanish: `/addpremium <user_id> [kun] [username]`\n"
            "Masalan: `/addpremium 123456789 30 ali`\n"
            "Kun = 0 yoki ko'rsatilmasa — muddatsiz.",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    user_id = context.args[0]
    days = 0
    username = ""
    if len(context.args) >= 2 and context.args[1].isdigit():
        days = int(context.args[1])
    if len(context.args) >= 3:
        username = context.args[2]
    subscription.add_premium(user_id, username=username, days=days)
    muddat = f"{days} kun" if days else "muddatsiz"
    await update.message.reply_text(
        f"✅ `{user_id}` premiumga qo'shildi ({muddat}).",
        parse_mode=constants.ParseMode.MARKDOWN,
    )


async def del_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return
    if not context.args:
        await update.message.reply_text(
            "Foydalanish: `/delpremium <user_id>`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )
        return
    ok = subscription.remove_premium(context.args[0])
    if ok:
        await update.message.reply_text(f"✅ `{context.args[0]}` premiumdan o'chirildi.",
                                        parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Bunday premium foydalanuvchi topilmadi.")


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return
    data = subscription.list_premium()
    if not data:
        await update.message.reply_text("Hozircha premium foydalanuvchilar yo'q.")
        return
    lines = ["💎 *Premium foydalanuvchilar:*"]
    for uid, info in data.items():
        uname = info.get("username", "")
        exp = info.get("expires")
        when = ""
        if exp:
            import datetime

            when = " — " + datetime.datetime.fromtimestamp(exp).strftime("%Y-%m-%d")
        lines.append(f"• `{uid}` @{uname}{when}")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=constants.ParseMode.MARKDOWN
    )


# ----------------------- Matn / Rasm bilan savol -----------------------

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


def build_application(token: str | None = None) -> Application:
    """Telegram Application yaratadi va barcha handlerlarni ro'yxatdan o'tkazadi.

    Ham polling (bot.py), ham webhook (web.py) rejimida ishlatiladi.
    """
    token = token or config.TELEGRAM_BOT_TOKEN
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN topilmadi! .env faylga botingiz tokenini qo'shing "
            "(@BotFather dan oling)."
        )

    app = Application.builder().token(token).build()

    # Asosiy
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(CommandHandler(["obuna", "premium"], obuna))

    # Premium funksiyalar
    app.add_handler(CommandHandler(["rasm", "image"], rasm))
    app.add_handler(CommandHandler(["prezentatsiya", "ppt", "slayd"], prezentatsiya))

    # Admin
    app.add_handler(CommandHandler("addpremium", add_premium))
    app.add_handler(CommandHandler("delpremium", del_premium))
    app.add_handler(CommandHandler("users", users))

    # Matn va rasm
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


def main() -> None:
    """Polling rejimida ishga tushiradi (mahalliy/VPS uchun qulay)."""
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

    app = build_application()

    logger.info(
        "BilimAI bot (polling) ishga tushdi. Provayder: %s | Admin: @%s",
        config.active_provider() or "yo'q",
        config.ADMIN_USERNAME,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
