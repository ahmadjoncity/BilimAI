"""BilimAI konfiguratsiyasi - muhit o'zgaruvchilarini o'qiydi."""

import os

from dotenv import load_dotenv

# .env faylini yuklash (lokal ishlatish uchun)
load_dotenv()


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


# AI provayder: "gemini" yoki "groq"
AI_PROVIDER = _get("AI_PROVIDER", "gemini").lower()

# Gemini
GEMINI_API_KEY = _get("GEMINI_API_KEY")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-1.5-flash")

# Groq
GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Telegram
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")

# --- Admin / Obuna sozlamalari ---
# Admin username (@ siz). Bu odam barcha funksiyalardan bepul foydalanadi
# va premium foydalanuvchilarni qo'sha oladi.
ADMIN_USERNAME = _get("ADMIN_USERNAME", "ravshanovichch").lstrip("@").lower()
# Admin Telegram ID (ixtiyoriy, raqamli). Bilsangiz qo'ying - ishonchliroq bo'ladi.
ADMIN_ID = _get("ADMIN_ID")
# Premium foydalanuvchilar saqlanadigan fayl
PREMIUM_FILE = _get("PREMIUM_FILE", "premium_users.json")

# --- Webhook (Render/Koyeb kabi bepul hostinglar uchun) ---
# Ilovangizning ochiq URL manzili. Masalan: https://bilimai.onrender.com
# Agar bo'sh bo'lsa, web server faqat web interfeys sifatida ishlaydi (bot webhooksiz).
WEBHOOK_URL = _get("WEBHOOK_URL", "").rstrip("/")

# Web server porti
PORT = int(_get("PORT", "8000") or "8000")


def active_provider() -> str:
    """Mavjud kalitga qarab haqiqiy provayderni aniqlaydi."""
    if AI_PROVIDER == "groq" and GROQ_API_KEY:
        return "groq"
    if AI_PROVIDER == "gemini" and GEMINI_API_KEY:
        return "gemini"
    # Fallback: qaysi kalit bor bo'lsa
    if GEMINI_API_KEY:
        return "gemini"
    if GROQ_API_KEY:
        return "groq"
    return ""


def is_configured() -> bool:
    return bool(active_provider())
