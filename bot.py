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

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    constants,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
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

ADMIN_USERNAME_PLAIN = config.ADMIN_USERNAME
ADMIN_CONTACT = f"@{ADMIN_USERNAME_PLAIN}"
ADMIN_LINK = f"https://t.me/{ADMIN_USERNAME_PLAIN}"
MD = constants.ParseMode.MARKDOWN

# Telegram "Menu" tugmasi uchun buyruqlar ro'yxati
COMMANDS = [
    BotCommand("start", "🏠 Bosh menyu"),
    BotCommand("rasm", "🎨 Rasm yaratish (premium)"),
    BotCommand("prezentatsiya", "📊 Prezentatsiya (premium)"),
    BotCommand("obuna", "💎 Pullik obuna"),
    BotCommand("id", "🆔 Mening ID raqamim"),
    BotCommand("help", "ℹ️ Yordam"),
]


# ----------------------- Yordamchi funksiyalar -----------------------

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


def _is_premium(update: Update) -> bool:
    user = update.effective_user
    return bool(user) and subscription.is_premium(user.id, user.username)


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user) and subscription.is_admin(user.id, user.username)


# ----------------------- Klaviaturalar (menyular) -----------------------

def main_menu_kb() -> InlineKeyboardMarkup:
    """Bosh menyu — tugmalar."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎨 Rasm yaratish", callback_data="m:rasm"),
                InlineKeyboardButton("📊 Prezentatsiya", callback_data="m:ppt"),
            ],
            [
                InlineKeyboardButton("📚 Savol berish", callback_data="m:savol"),
                InlineKeyboardButton("💎 Obuna", callback_data="m:obuna"),
            ],
            [
                InlineKeyboardButton("🆔 Mening ID", callback_data="m:id"),
                InlineKeyboardButton("ℹ️ Yordam", callback_data="m:help"),
            ],
            [InlineKeyboardButton("👨‍💻 Admin bilan bog'lanish", url=ADMIN_LINK)],
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    """Bosh menyuga qaytish tugmasi."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Bosh menyu", callback_data="m:home")]]
    )


def obuna_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👨‍💻 Admin bilan bog'lanish", url=ADMIN_LINK)],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="m:home")],
        ]
    )


# ----------------------- Matnlar -----------------------

def _premium_required_text() -> str:
    return (
        "🔒 *Bu funksiya faqat pullik obuna uchun.*\n\n"
        "🎨 Rasm yaratish va 📊 prezentatsiya tayyorlash — premium imkoniyatlar.\n\n"
        f"📩 Obuna bo'lish uchun admin bilan bog'laning: {ADMIN_CONTACT}\n\n"
        "Obuna bo'lgach, ID raqamingiz tizimga qo'shiladi va barcha funksiyalar "
        "ochiladi. (ID ni bilish uchun /id)"
    )


def _help_text() -> str:
    return (
        "*ℹ️ BilimAI — yordam*\n\n"
        "📚 *Bepul imkoniyatlar:*\n"
        "• Savolingizni shunchaki yozing — javob beraman\n"
        "• Masala *rasmini* yuboring — yechib beraman\n"
        "  (Matematika, Fizika, Kimyo, Biologiya, Tarix, Ingliz tili, Dasturlash...)\n\n"
        "💎 *Pullik obuna (premium):*\n"
        "• `/rasm tavsif` — tavsif bo'yicha AI rasm chizadi\n"
        "• `/prezentatsiya mavzu` — tayyor .pptx taqdimot\n\n"
        "🔘 *Buyruqlar:*\n"
        "/start — bosh menyu\n"
        "/obuna — obuna haqida\n"
        "/id — Telegram ID raqamingiz\n"
        "/help — shu yordam\n\n"
        f"💬 Pullik obuna uchun: {ADMIN_CONTACT}"
    )


def _obuna_text(is_premium: bool) -> str:
    if is_premium:
        return (
            "✅ *Sizda premium obuna FAOL!* 🎉\n\n"
            "Barcha funksiyalardan to'liq foydalanishingiz mumkin:\n"
            "🎨 /rasm — rasm yaratish\n"
            "📊 /prezentatsiya — taqdimot tayyorlash\n\n"
            "Rahmat! 💙"
        )
    return (
        "💎 *PULLIK OBUNA (PREMIUM)*\n\n"
        "Premium bilan quyidagilar ochiladi:\n\n"
        "🎨 *Rasm yaratish*\n"
        "   Istalgan tavsif bo'yicha AI rasm chizadi\n\n"
        "📊 *Prezentatsiya*\n"
        "   Mavzu bo'yicha tayyor .pptx taqdimot\n\n"
        "━━━━━━━━━━━━━━━\n"
        f"📩 Obuna bo'lish uchun admin bilan bog'laning:\n{ADMIN_CONTACT}\n\n"
        "Yozganda /id orqali olingan ID raqamingizni yuboring."
    )


def _id_text(update: Update) -> str:
    user = update.effective_user
    status = "💎 Premium" if _is_premium(update) else "🆓 Oddiy (bepul)"
    uname = f"@{user.username}" if user.username else "—"
    return (
        f"🆔 *Sizning ma'lumotlaringiz:*\n\n"
        f"ID: `{user.id}`\n"
        f"Username: {uname}\n"
        f"Holat: {status}\n\n"
        f"💬 Pullik obuna uchun ID raqamingizni adminga yuboring: {ADMIN_CONTACT}"
    )


# ----------------------- Asosiy buyruqlar -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("await", None)
    await update.message.reply_text(
        WELCOME_MESSAGE, parse_mode=MD, reply_markup=main_menu_kb()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        _help_text(), parse_mode=MD, reply_markup=back_kb()
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        _id_text(update), parse_mode=MD, reply_markup=back_kb()
    )


async def obuna(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        _obuna_text(_is_premium(update)), parse_mode=MD, reply_markup=obuna_kb()
    )


# ----------------------- Rasm va prezentatsiya (umumiy oqim) -----------------------

async def _do_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.UPLOAD_PHOTO
    )
    notice = await context.bot.send_message(
        chat_id, "🎨 Rasm yaratilmoqda… (10-30 soniya)"
    )
    try:
        image_bytes = await _run(image_gen.generate_image, prompt)
        await context.bot.send_photo(chat_id, photo=image_bytes, caption=f"🎨 {prompt}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rasm yaratish xatosi")
        await context.bot.send_message(chat_id, f"⚠️ Rasm yaratib bo'lmadi: {exc}")
    finally:
        try:
            await notice.delete()
        except Exception:  # noqa: BLE001
            pass


async def _do_ppt(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT
    )
    notice = await context.bot.send_message(
        chat_id, "📊 Prezentatsiya tayyorlanmoqda… (15-40 soniya)"
    )
    path = None
    try:
        path = await _run(presentation.create_presentation, topic, 8)
        safe = "".join(c for c in topic if c.isalnum() or c in " _-").strip()[:40]
        with open(path, "rb") as f:
            await context.bot.send_document(
                chat_id,
                document=f,
                filename=f"{safe or 'prezentatsiya'}.pptx",
                caption=f"📊 «{topic}» — tayyor!",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Prezentatsiya xatosi")
        await context.bot.send_message(
            chat_id, f"⚠️ Prezentatsiya tayyorlab bo'lmadi: {exc}"
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


async def rasm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_premium(update):
        await update.message.reply_text(
            _premium_required_text(), parse_mode=MD, reply_markup=obuna_kb()
        )
        return
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        context.user_data["await"] = "rasm"
        await update.message.reply_text(
            "🎨 Qanday rasm chizay? Tavsifni yozing.\n"
            "_Masalan: quyosh botayotgan tog'lar ustida burgut_",
            parse_mode=MD,
        )
        return
    await _do_image(update, context, prompt)


async def prezentatsiya(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_premium(update):
        await update.message.reply_text(
            _premium_required_text(), parse_mode=MD, reply_markup=obuna_kb()
        )
        return
    topic = " ".join(context.args) if context.args else ""
    if not topic:
        context.user_data["await"] = "ppt"
        await update.message.reply_text(
            "📊 Qaysi mavzuda prezentatsiya kerak? Mavzuni yozing.\n"
            "_Masalan: Suv aylanishi_",
            parse_mode=MD,
        )
        return
    await _do_ppt(update, context, topic)


# ----------------------- Tugmalar (callback) -----------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "m:home":
        context.user_data.pop("await", None)
        await query.edit_message_text(
            WELCOME_MESSAGE, parse_mode=MD, reply_markup=main_menu_kb()
        )
    elif data == "m:help":
        await query.edit_message_text(
            _help_text(), parse_mode=MD, reply_markup=back_kb()
        )
    elif data == "m:obuna":
        await query.edit_message_text(
            _obuna_text(_is_premium(update)), parse_mode=MD, reply_markup=obuna_kb()
        )
    elif data == "m:id":
        await query.edit_message_text(
            _id_text(update), parse_mode=MD, reply_markup=back_kb()
        )
    elif data == "m:savol":
        await query.edit_message_text(
            "📚 *Savol berish*\n\nShunchaki savolingizni yozing yoki masala "
            "*rasmini* yuboring — men javob beraman!\n\n"
            "_Masalan: 12 ni 4 ga bo'lsak nechchi bo'ladi?_",
            parse_mode=MD,
            reply_markup=back_kb(),
        )
    elif data == "m:rasm":
        if not _is_premium(update):
            await query.edit_message_text(
                _premium_required_text(), parse_mode=MD, reply_markup=obuna_kb()
            )
            return
        context.user_data["await"] = "rasm"
        await query.edit_message_text(
            "🎨 *Rasm yaratish*\n\nQanday rasm chizay? Tavsifini yozib yuboring.\n"
            "_Masalan: kosmosdagi mushuk, neon uslubida_",
            parse_mode=MD,
            reply_markup=back_kb(),
        )
    elif data == "m:ppt":
        if not _is_premium(update):
            await query.edit_message_text(
                _premium_required_text(), parse_mode=MD, reply_markup=obuna_kb()
            )
            return
        context.user_data["await"] = "ppt"
        await query.edit_message_text(
            "📊 *Prezentatsiya*\n\nQaysi mavzuda kerak? Mavzuni yozib yuboring.\n"
            "_Masalan: Sun'iy intellekt nima?_",
            parse_mode=MD,
            reply_markup=back_kb(),
        )


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
            parse_mode=MD,
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
        f"✅ `{user_id}` premiumga qo'shildi ({muddat}).", parse_mode=MD
    )


async def del_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return
    if not context.args:
        await update.message.reply_text(
            "Foydalanish: `/delpremium <user_id>`", parse_mode=MD
        )
        return
    ok = subscription.remove_premium(context.args[0])
    if ok:
        await update.message.reply_text(
            f"✅ `{context.args[0]}` premiumdan o'chirildi.", parse_mode=MD
        )
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
    await update.message.reply_text("\n".join(lines), parse_mode=MD)


# ----------------------- Matn / Rasm bilan savol -----------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Tugma orqali rasm/prezentatsiya kutilayotgan bo'lsa
    waiting = context.user_data.pop("await", None)
    text = update.message.text
    if waiting == "rasm":
        await _do_image(update, context, text)
        return
    if waiting == "ppt":
        await _do_ppt(update, context, text)
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    try:
        answer = await _run(ai.ask, text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI xatosi")
        answer = f"⚠️ Xatolik yuz berdi: {exc}"
    for chunk in _split(answer):
        await update.message.reply_text(chunk)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("await", None)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING
    )
    try:
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        image_bytes = bytes(await tg_file.download_as_bytearray())
        caption = update.message.caption or ""
        answer = await _run(ai.ask_with_image, image_bytes, "image/jpeg", caption)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rasm bilan ishlashda xato")
        answer = f"⚠️ Rasmni yechishda xatolik: {exc}"
    for chunk in _split(answer):
        await update.message.reply_text(chunk)


# ----------------------- Sozlash -----------------------

async def _post_init(app: Application) -> None:
    """Bot ishga tushganda 'Menu' tugmasi buyruqlarini o'rnatadi."""
    try:
        await app.bot.set_my_commands(COMMANDS)
    except Exception:  # noqa: BLE001
        logger.exception("Buyruqlar menyusini o'rnatishda xato")


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

    app = Application.builder().token(token).post_init(_post_init).build()

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

    # Tugmalar
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^m:"))

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
