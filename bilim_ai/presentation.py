"""Prezentatsiya (.pptx) yaratish moduli.

AI yordamida mavzu bo'yicha slaydlar tuzilishini (JSON) oladi,
keyin python-pptx orqali haqiqiy PowerPoint faylini quradi.

Foydalanish:
    from bilim_ai.presentation import create_presentation
    pptx_bytes, sarlavha = create_presentation("Suvning aylanishi", slaydlar=8)
"""

from __future__ import annotations

import json
import re
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from . import ai

# Rang sxemasi (BilimAI ko'k-yashil)
DARK = RGBColor(0x0F, 0x14, 0x19)
ACCENT = RGBColor(0x4F, 0x9C, 0xF9)
ACCENT2 = RGBColor(0x14, 0xB8, 0xA6)
LIGHT = RGBColor(0xF5, 0xF7, 0xFA)
TEXT = RGBColor(0x23, 0x2C, 0x38)

_PROMPT = """Sen prezentatsiya tuzuvchi mutaxassissan. Foydalanuvchi bergan mavzu
bo'yicha {n} ta slayddan iborat prezentatsiya rejasini tuzasan.

QAT'IY QOIDA: Faqat JSON qaytar, boshqa hech narsa yozma. Markdown ham yozma.
Til: mavzu qaysi tilda bo'lsa, o'sha tilda yoz (o'zbekcha bo'lsa o'zbekcha).

JSON tuzilishi aniq shunday bo'lsin:
{{
  "title": "Prezentatsiya sarlavhasi",
  "subtitle": "Qisqa tavsif yoki muallif joyi",
  "slides": [
    {{"heading": "Slayd sarlavhasi", "bullets": ["fikr 1", "fikr 2", "fikr 3"]}}
  ]
}}

Har bir slaydda 3-5 ta qisqa, mazmunli bullet bo'lsin. Oxirgi slayd xulosa bo'lsin.
Mavzu: {topic}
"""


def _extract_json(raw: str) -> dict:
    """AI javobidan JSON qismini ajratib oladi."""
    # ```json ... ``` bloklarini tozalash
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    # Birinchi { dan oxirgi } gacha
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def generate_outline(topic: str, slaydlar: int = 8) -> dict:
    """Mavzu bo'yicha slaydlar rejasini (dict) qaytaradi."""
    prompt = _PROMPT.format(n=slaydlar, topic=topic)
    raw = ai.ask_with_system(prompt, "Sen faqat to'g'ri JSON qaytaradigan yordamchisan.")
    try:
        data = _extract_json(raw)
    except Exception:
        # Fallback: oddiy tuzilish
        data = {
            "title": topic,
            "subtitle": "BilimAI tomonidan yaratilgan",
            "slides": [{"heading": topic, "bullets": [raw[:500]]}],
        }
    # Tuzilishni tekshirish
    data.setdefault("title", topic)
    data.setdefault("subtitle", "BilimAI tomonidan yaratilgan")
    data.setdefault("slides", [])
    return data


def _add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # bo'sh layout
    # Fon
    bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = DARK
    bg.line.fill.background()
    bg.shadow.inherit = False

    # Sarlavha
    box = slide.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.5), Inches(2))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = LIGHT

    # Subtitle
    sub = slide.shapes.add_textbox(Inches(0.8), Inches(4.3), Inches(11.5), Inches(1))
    stf = sub.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = subtitle
    sp.alignment = PP_ALIGN.CENTER
    sp.font.size = Pt(20)
    sp.font.color.rgb = ACCENT


def _add_content_slide(prs: Presentation, heading: str, bullets: list, index: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Yon chiziq (accent)
    bar = slide.shapes.add_shape(1, 0, 0, Inches(0.25), prs.slide_height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT if index % 2 == 0 else ACCENT2
    bar.line.fill.background()
    bar.shadow.inherit = False

    # Sarlavha
    head = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12), Inches(1))
    htf = head.text_frame
    htf.word_wrap = True
    hp = htf.paragraphs[0]
    hp.text = heading
    hp.font.size = Pt(32)
    hp.font.bold = True
    hp.font.color.rgb = TEXT

    # Bulletlar
    body = slide.shapes.add_textbox(Inches(0.9), Inches(1.7), Inches(11.5), Inches(5))
    btf = body.text_frame
    btf.word_wrap = True
    for i, bullet in enumerate(bullets):
        para = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
        para.text = f"•  {bullet}"
        para.font.size = Pt(20)
        para.font.color.rgb = TEXT
        para.space_after = Pt(12)


def build_pptx(outline: dict) -> bytes:
    """Slaydlar rejasidan (dict) .pptx faylini bytes ko'rinishida quradi."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9
    prs.slide_height = Inches(7.5)

    _add_title_slide(prs, outline.get("title", ""), outline.get("subtitle", ""))
    for i, slide in enumerate(outline.get("slides", [])):
        heading = slide.get("heading", f"Slayd {i + 1}")
        bullets = slide.get("bullets", [])
        if isinstance(bullets, str):
            bullets = [bullets]
        _add_content_slide(prs, heading, bullets, i)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()


def create_presentation(topic: str, slaydlar: int = 8):
    """Mavzu bo'yicha to'liq prezentatsiya yaratadi.

    Qaytaradi: (pptx_bytes, sarlavha)
    """
    outline = generate_outline(topic, slaydlar)
    pptx_bytes = build_pptx(outline)
    return pptx_bytes, outline.get("title", topic)
