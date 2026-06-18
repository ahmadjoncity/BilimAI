"""AI provayder bilan ishlash moduli.

Ikkita bepul provayderni qo'llab-quvvatlaydi:
  - Google Gemini  -> matn + rasm (vision). Avtomatik fallback (zaxira) modellar.
  - Groq (Llama)   -> faqat matn (juda tez)

Foydalanish:
    from bilim_ai.ai import ask, ask_with_image
    javob = ask("2x + 5 = 15, x ni top")
"""

from __future__ import annotations

import logging
from typing import List

from . import config
from .prompt import SYSTEM_PROMPT

logger = logging.getLogger("BilimAI.ai")


class AIError(Exception):
    """AI bilan bog'liq xatolar."""


# ---------------------- Gemini ----------------------

def _gemini_models_to_try() -> List[str]:
    """Sinab ko'rish kerak bo'lgan modellar ro'yxati (asosiy + fallback)."""
    seen, out = set(), []
    for m in [config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _gemini_model(model_name: str, system: str = SYSTEM_PROMPT):
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system,
    )


def _is_model_unavailable(exc: Exception) -> bool:
    """Xato model topilmaganligi/eskirganligini bildiradimi?"""
    msg = str(exc).lower()
    keywords = (
        "404",
        "not found",
        "is not found",
        "deprecated",
        "no longer available",
        "is not supported",
        "model not found",
        "permission denied",
        "403",
    )
    return any(k in msg for k in keywords)


def _try_gemini(call):
    """Gemini'ni asosiy va fallback modellar bilan navbatma-navbat sinaydi.

    `call` — bitta argument (model_name) qabul qiluvchi funksiya.
    Birinchi muvaffaqiyatli javobni qaytaradi.
    """
    if not config.GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY topilmadi. Render Environment'da kalit qo'shing.")

    last_exc: Exception | None = None
    for model_name in _gemini_models_to_try():
        try:
            return call(model_name)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_model_unavailable(exc):
                logger.warning(
                    "Gemini model '%s' ishlamadi: %s. Keyingisini sinaymiz.",
                    model_name, exc,
                )
                continue
            # Boshqa xato (kvota, tarmoq) — keyingilarni sinashning ma'nosi yo'q
            raise AIError(_friendly_gemini_error(exc)) from exc

    # Hech bir model ishlamadi
    raise AIError(
        "Hech bir Gemini modeli ishlamadi. Modellar eskirgan bo'lishi mumkin. "
        f"Oxirgi xato: {last_exc}"
    )


def _friendly_gemini_error(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "api key" in low or "api_key" in low or "401" in low:
        return (
            "Gemini API kalit noto'g'ri yoki amal qilmaydi. "
            "Yangi kalit oling: https://aistudio.google.com/app/apikey"
        )
    if "quota" in low or "rate" in low or "429" in low:
        return (
            "Gemini bepul kvotasi tugadi. Bir necha daqiqa kuting yoki "
            "boshqa Google akkauntdan yangi kalit oling."
        )
    if "timeout" in low or "deadline" in low:
        return "Gemini javobi kechikdi (timeout). Qayta urinib ko'ring."
    return f"Gemini xatosi: {msg}"


def _ask_gemini(text: str, system: str = SYSTEM_PROMPT) -> str:
    def call(model_name: str) -> str:
        model = _gemini_model(model_name, system)
        resp = model.generate_content(text)
        return (resp.text or "").strip() or "Kechirasiz, javob bo'sh chiqdi."

    return _try_gemini(call)


def _ask_gemini_image(image_bytes: bytes, mime_type: str, text: str) -> str:
    def call(model_name: str) -> str:
        model = _gemini_model(model_name, SYSTEM_PROMPT)
        prompt = text or (
            "Rasmdagi masala yoki savolni aniqla va to'liq, bosqichma-bosqich "
            "yechib ber."
        )
        resp = model.generate_content(
            [
                {"mime_type": mime_type, "data": image_bytes},
                prompt,
            ]
        )
        return (resp.text or "").strip() or "Kechirasiz, javob bo'sh chiqdi."

    return _try_gemini(call)


# ---------------------- Groq ----------------------

def _ask_groq(text: str, system: str = SYSTEM_PROMPT) -> str:
    if not config.GROQ_API_KEY:
        raise AIError("GROQ_API_KEY topilmadi. .env faylga kalitni qo'shing.")
    from groq import Groq

    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            temperature=0.6,
            max_tokens=2048,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise AIError(f"Groq xatosi: {exc}") from exc


# ---------------------- Umumiy interfeys ----------------------

def ask(text: str) -> str:
    """Matnli savolga javob qaytaradi."""
    provider = config.active_provider()
    if not provider:
        raise AIError(
            "Hech qanday AI kaliti sozlanmagan. GEMINI_API_KEY yoki "
            "GROQ_API_KEY qo'shing."
        )
    if provider == "groq":
        return _ask_groq(text)
    return _ask_gemini(text)


def ask_with_system(text: str, system: str) -> str:
    """Maxsus tizim ko'rsatmasi bilan savol beradi (masalan JSON formatda)."""
    provider = config.active_provider()
    if not provider:
        raise AIError(
            "Hech qanday AI kaliti sozlanmagan. GEMINI_API_KEY yoki "
            "GROQ_API_KEY qo'shing."
        )
    if provider == "groq":
        return _ask_groq(text, system)
    return _ask_gemini(text, system)


def ask_with_image(
    image_bytes: bytes, mime_type: str = "image/jpeg", caption: str = ""
) -> str:
    """Rasm + (ixtiyoriy) matn bilan savol. Faqat Gemini vision'ni qo'llab-quvvatlaydi."""
    if not config.GEMINI_API_KEY:
        raise AIError(
            "Rasm bilan ishlash uchun Gemini kerak. GEMINI_API_KEY qo'shing "
            "(Groq rasmni qo'llab-quvvatlamaydi)."
        )
    return _ask_gemini_image(image_bytes, mime_type, caption)
