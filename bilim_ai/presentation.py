"""Prezentatsiya (.pptx) yaratish moduli.

Ishlash tartibi:
  1. AI (Gemini/Groq) mavzu bo'yicha slaydlar kontentini JSON ko'rinishda yaratadi.
  2. python-pptx kutubxonasi yordamida chiroyli .pptx fayl quriladi.

Foydalanish:
    from bilim_ai.presentation import create_presentation
    fayl_yoli = create_presentation("Suv aylanishi", slides=8)
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from typing import Any, Dict

from . import ai, config
from .prompt import presentation_prompt

logger = logging.getLogger("BilimAI.presentation")


class PresentationError(Exception):
    """Prezentatsiya yaratishda yuzaga keladigan xatolar."""


# Slayd ranglari (zamonaviy ko'k mavzu)
_BG = (0x0F, 0x14, 0x19)
_ACCENT = (0x4F, 0x9C, 0xF9)
_TEXT = (0xE6, 0xED, 0xF3)
_MUTED = (0x8B, 0x98, 0xA9)


def _extract_json(text: str) -> Dict[str, Any]:
    """AI javobidan JSON qismini ajratib oladi."""
    text = (text or "").strip()
    # ```json ... ``` bloklarini olib tashlash
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Matn ichidan birinchi { ... } blokni topishga urinish
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise PresentationError(
                    f"AI javobidan prezentatsiya ma'lumotini o'qib bo'lmadi: {exc}"
                ) from exc
        raise PresentationError(
            "AI to'g'ri formatda javob bermadi. Qayta urinib ko'ring."
        )


def generate_outline(topic: str, slides: int = 8) -> Dict[str, Any]:
    """AI orqali prezentatsiya rejasini (JSON) yaratadi."""
    if not config.is_configured():
        raise PresentationError(
            "AI kaliti sozlanmagan. Prezentatsiya uchun GEMINI_API_KEY yoki "
            "GROQ_API_KEY kerak."
        )
    prompt = presentation_prompt(topic, slides=slides)
    raw = ai.ask(prompt)
    data = _extract_json(raw)
    if "slides" not in data or not isinstance(data["slides"], list):
        raise PresentationError("AI javobida slaydlar topilmadi.")
    return data


def _rgb(color):
    from pptx.dml.color import RGBColor

    return RGBColor(*color)


def build_pptx(data: Dict[str, Any], out_path: str | None = None) -> str:
    """Berilgan reja (JSON) asosida .pptx fayl yaratadi va fayl yo'lini qaytaradi."""
    from pptx import Presentation
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]  # bo'sh layout

    def add_bg(slide):
        rect = slide.shapes.add_shape(
            1,  # MSO_SHAPE.RECTANGLE
            Inches(0), Inches(0), prs.slide_width, prs.slide_height,
        )
        rect.fill.solid()
        rect.fill.fore_color.rgb = _rgb(_BG)
        rect.line.fill.background()
        rect.shadow.inherit = False
        # Orqaga surish
        slide.shapes._spTree.remove(rect._element)
        slide.shapes._spTree.insert(2, rect._element)
        return rect

    def add_accent_bar(slide):
        bar = slide.shapes.add_shape(
            1, Inches(0.6), Inches(1.6), Inches(2.2), Inches(0.12),
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = _rgb(_ACCENT)
        bar.line.fill.background()
        bar.shadow.inherit = False

    # --- Title slayd ---
    title_text = str(data.get("title", "Prezentatsiya"))
    subtitle_text = str(data.get("subtitle", ""))

    slide = prs.slides.add_slide(blank)
    add_bg(slide)
    tb = slide.shapes.add_textbox(Inches(0.9), Inches(2.6), Inches(11.5), Inches(2.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(46)
    p.font.bold = True
    p.font.color.rgb = _rgb(_TEXT)
    if subtitle_text:
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.size = Pt(22)
        p2.font.color.rgb = _rgb(_ACCENT)

    brand = slide.shapes.add_textbox(Inches(0.9), Inches(6.7), Inches(8), Inches(0.5))
    bp = brand.text_frame.paragraphs[0]
    bp.text = "BilimAI"
    bp.font.size = Pt(14)
    bp.font.color.rgb = _rgb(_MUTED)

    # --- Kontent slaydlar ---
    for item in data.get("slides", []):
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading", "")).strip()
        bullets = item.get("bullets", []) or []
        # Title slaydni qayta yaratmaymiz (agar AI uni ham qo'shsa)
        if not heading and not bullets:
            continue

        slide = prs.slides.add_slide(blank)
        add_bg(slide)
        add_accent_bar(slide)

        # Sarlavha
        head_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(0.55), Inches(12.1), Inches(1.0)
        )
        hp = head_box.text_frame.paragraphs[0]
        hp.text = heading
        hp.font.size = Pt(32)
        hp.font.bold = True
        hp.font.color.rgb = _rgb(_TEXT)

        # Punktlar
        body = slide.shapes.add_textbox(
            Inches(0.8), Inches(2.0), Inches(11.6), Inches(4.8)
        )
        bf = body.text_frame
        bf.word_wrap = True
        first = True
        for b in bullets:
            text = str(b).strip()
            if not text:
                continue
            para = bf.paragraphs[0] if first else bf.add_paragraph()
            para.text = f"•  {text}"
            para.font.size = Pt(20)
            para.font.color.rgb = _rgb(_TEXT)
            para.space_after = Pt(14)
            para.alignment = PP_ALIGN.LEFT
            first = False

    if out_path is None:
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".pptx", prefix="bilimai_"
        )
        out_path = tmp.name
        tmp.close()

    prs.save(out_path)
    return out_path


def create_presentation(topic: str, slides: int = 8, out_path: str | None = None) -> str:
    """Mavzu bo'yicha to'liq prezentatsiya yaratadi. .pptx fayl yo'lini qaytaradi."""
    topic = (topic or "").strip()
    if not topic:
        raise PresentationError("Prezentatsiya uchun mavzu bo'sh bo'lishi mumkin emas.")
    slides = max(3, min(slides, 15))
    outline = generate_outline(topic, slides=slides)
    return build_pptx(outline, out_path=out_path)
