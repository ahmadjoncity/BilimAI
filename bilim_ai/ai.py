"""AI provayder bilan ishlash moduli.

Ikkita bepul provayderni qo'llab-quvvatlaydi:
  - Google Gemini  -> matn + rasm (vision)
  - Groq (Llama)   -> faqat matn (juda tez)

Foydalanish:
    from bilim_ai.ai import ask, ask_with_image
    javob = ask("2x + 5 = 15, x ni top")
"""

from __future__ import annotations

from typing import Optional

from . import config
from .prompt import SYSTEM_PROMPT

# Provayderlarni kerak bo'lganda import qilamiz (lazy), shunda
# bitta kalit yo'q bo'lsa ham ilova ishga tushaveradi.


class AIError(Exception):
    """AI bilan bog'liq xatolar."""


def _gemini_model(vision: bool = False):
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )


def _ask_gemini(text: str) -> str:
    if not config.GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY topilmadi. .env faylga kalitni qo'shing.")
    model = _gemini_model()
    resp = model.generate_content(text)
    return (resp.text or "").strip() or "Kechirasiz, javob bo'sh chiqdi."


def _ask_gemini_image(image_bytes: bytes, mime_type: str, text: str) -> str:
    if not config.GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY topilmadi. .env faylga kalitni qo'shing.")
    model = _gemini_model(vision=True)
    prompt = text or (
        "Rasmdagi masala yoki savolni aniqla va to'liq, bosqichma-bosqich yechib ber."
    )
    resp = model.generate_content(
        [
            {"mime_type": mime_type, "data": image_bytes},
            prompt,
        ]
    )
    return (resp.text or "").strip() or "Kechirasiz, javob bo'sh chiqdi."


def _ask_groq(text: str) -> str:
    if not config.GROQ_API_KEY:
        raise AIError("GROQ_API_KEY topilmadi. .env faylga kalitni qo'shing.")
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.6,
        max_tokens=2048,
    )
    return (completion.choices[0].message.content or "").strip()


def ask(text: str) -> str:
    """Matnli savolga javob qaytaradi."""
    provider = config.active_provider()
    if not provider:
        raise AIError(
            "Hech qanday AI kaliti sozlanmagan. .env faylga GEMINI_API_KEY yoki "
            "GROQ_API_KEY qo'shing."
        )
    if provider == "groq":
        return _ask_groq(text)
    return _ask_gemini(text)


def ask_with_image(image_bytes: bytes, mime_type: str = "image/jpeg",
                   caption: str = "") -> str:
    """Rasm + (ixtiyoriy) matn bilan savol. Faqat Gemini vision'ni qo'llab-quvvatlaydi."""
    if not config.GEMINI_API_KEY:
        raise AIError(
            "Rasm bilan ishlash uchun Gemini kerak. .env faylga GEMINI_API_KEY qo'shing "
            "(Groq rasmni qo'llab-quvvatlamaydi)."
        )
    return _ask_gemini_image(image_bytes, mime_type, caption)
