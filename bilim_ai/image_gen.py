"""Rasm yaratish (text-to-image) moduli.

To'liq BEPUL ishlaydi - kalit shart emas:
  - Pollinations.ai  -> bepul, ro'yxatdan o'tmasdan (asosiy)

Foydalanish:
    from bilim_ai.image_gen import generate_image
    rasm_baytlari = generate_image("quyosh botayotgan tog'lar")
"""

from __future__ import annotations

import logging
import urllib.parse

import httpx

logger = logging.getLogger("BilimAI.image_gen")


class ImageGenError(Exception):
    """Rasm yaratishda yuzaga keladigan xatolar."""


# Pollinations bepul rasm yaratish API'si (kalit kerak emas)
_POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    timeout: float = 120.0,
) -> bytes:
    """Berilgan tavsif (prompt) asosida rasm yaratadi va PNG/JPEG baytlarini qaytaradi.

    Args:
        prompt: Rasm tavsifi (istalgan tilda; ingliz tilida aniqroq chiqadi).
        width, height: rasm o'lchami.
        timeout: kutish vaqti (soniya).
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise ImageGenError("Rasm uchun tavsif (prompt) bo'sh bo'lishi mumkin emas.")

    encoded = urllib.parse.quote(prompt, safe="")
    url = _POLLINATIONS_URL.format(prompt=encoded)
    params = {
        "width": width,
        "height": height,
        "nologo": "true",
        "model": "flux",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            content = resp.content
            ctype = resp.headers.get("content-type", "")
            if not content or "image" not in ctype:
                raise ImageGenError(
                    "Rasm yaratib bo'lmadi (xizmat band bo'lishi mumkin). "
                    "Birozdan keyin qayta urinib ko'ring."
                )
            return content
    except httpx.HTTPError as exc:
        logger.exception("Pollinations xatosi")
        raise ImageGenError(f"Rasm yaratishda tarmoq xatosi: {exc}") from exc
