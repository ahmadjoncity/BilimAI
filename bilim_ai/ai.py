"""AI provayder bilan ishlash moduli.

Quyidagi bepul provayderlarni qo'llab-quvvatlaydi (avtomatik fallback bilan):
  1. Groq (Llama 3.3) — eng tez va ishonchli, kalit talab qiladi
  2. Google Gemini   — matn + rasm (vision), kalit talab qiladi
  3. Pollinations    — kalitsiz bepul fallback (oxirgi chora)

Agar bittasi xato bersa, kod avtomatik ravishda keyingisiga o'tadi.
"""

from __future__ import annotations

import logging

import httpx

from . import config
from .prompt import SYSTEM_PROMPT

logger = logging.getLogger("BilimAI.ai")


class AIError(Exception):
    """AI bilan bog'liq xatolar."""


# ----------------------- Gemini -----------------------

# Gemini'da sinaladigan modellar ro'yxati (eskirgan modellar uchun fallback)
_GEMINI_MODELS = [
    config.GEMINI_MODEL,
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
]


def _gemini_generate(parts) -> str:
    """Gemini'ga so'rov yuboradi; eskirgan model bo'lsa keyingisiga o'tadi."""
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    last_error: Exception | None = None
    seen: set[str] = set()
    for model_name in _GEMINI_MODELS:
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT,
            )
            resp = model.generate_content(parts)
            return (resp.text or "").strip() or "Kechirasiz, javob bo'sh chiqdi."
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            msg = str(exc).lower()
            # 404 / not found / not supported bo'lsa — keyingi modelga o'tamiz
            if "404" in msg or "not found" in msg or "not supported" in msg:
                logger.warning("Gemini modeli '%s' mavjud emas, keyingisiga o'tamiz",
                               model_name)
                continue
            # Boshqa xato — to'xtaymiz
            raise AIError(f"Gemini xatosi: {exc}") from exc
    raise AIError(f"Gemini: barcha modellar ishlamadi. Oxirgi xato: {last_error}")


def _ask_gemini(text: str) -> str:
    if not config.GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY yo'q")
    return _gemini_generate(text)


def _ask_gemini_image(image_bytes: bytes, mime_type: str, text: str) -> str:
    if not config.GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY yo'q")
    prompt = text or (
        "Rasmdagi masala yoki savolni aniqla va to'liq, bosqichma-bosqich yechib ber."
    )
    return _gemini_generate(
        [{"mime_type": mime_type, "data": image_bytes}, prompt]
    )


# ----------------------- Groq -----------------------

def _ask_groq(text: str) -> str:
    if not config.GROQ_API_KEY:
        raise AIError("GROQ_API_KEY yo'q")
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


# ----------------------- Pollinations (kalitsiz bepul) -----------------------

def _ask_pollinations(text: str) -> str:
    """Pollinations.ai — bepul, kalitsiz fallback."""
    try:
        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "model": "openai",
        }
        with httpx.Client(timeout=60) as client:
            r = client.post("https://text.pollinations.ai/openai", json=payload)
            r.raise_for_status()
            data = r.json()
            answer = data["choices"][0]["message"]["content"]
            return (answer or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise AIError(f"Pollinations xatosi: {exc}") from exc


# ----------------------- Asosiy funksiyalar (fallback bilan) -----------------------

def ask(text: str) -> str:
    """Matnli savolga javob — bir nechta provayderda navbat bilan urinib ko'radi."""
    # Provayderlar tartibi: avval foydalanuvchi tanlagani, keyin qolganlari
    chosen = config.active_provider()
    order: list[str] = []
    if chosen:
        order.append(chosen)
    for p in ("groq", "gemini"):
        if p not in order:
            order.append(p)
    order.append("pollinations")  # oxirgi chora — kalitsiz

    last_error: Exception | None = None
    for provider in order:
        try:
            if provider == "groq" and config.GROQ_API_KEY:
                logger.info("Provayder: Groq")
                return _ask_groq(text)
            if provider == "gemini" and config.GEMINI_API_KEY:
                logger.info("Provayder: Gemini")
                return _ask_gemini(text)
            if provider == "pollinations":
                logger.info("Provayder: Pollinations (fallback)")
                return _ask_pollinations(text)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Provayder %s ishlamadi: %s", provider, exc)
            continue

    raise AIError(
        f"Barcha AI provayderlar ishlamadi. Oxirgi xato: {last_error}. "
        f"Render Environment'da GROQ_API_KEY yoki GEMINI_API_KEY to'g'ri qo'yilganini tekshiring."
    )


def ask_with_image(image_bytes: bytes, mime_type: str = "image/jpeg",
                   caption: str = "") -> str:
    """Rasm + matn bilan savol. Faqat Gemini vision'ni qo'llab-quvvatlaydi."""
    if not config.GEMINI_API_KEY:
        raise AIError(
            "Rasm bilan ishlash uchun GEMINI_API_KEY kerak (Groq va Pollinations rasmni qo'llab-quvvatlamaydi). "
            "Render Environment'da GEMINI_API_KEY qo'shing."
        )
    return _ask_gemini_image(image_bytes, mime_type, caption)
