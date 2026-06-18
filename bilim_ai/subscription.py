"""Obuna (premium) tizimi.

Premium foydalanuvchilar oddiy JSON faylda saqlanadi. Admin (config.ADMIN_USERNAME
yoki config.ADMIN_ID) doim premium hisoblanadi va boshqalarga premium bera oladi.

Eslatma: ba'zi hosting (Railway/Heroku) tizimlarida fayl tizimi vaqtinchalik
bo'lishi mumkin. Doimiy saqlash uchun keyinchalik bazaga o'tkazish mumkin.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict

from . import config

logger = logging.getLogger("BilimAI.subscription")

_LOCK = threading.Lock()
_PATH = Path(config.PREMIUM_FILE)


def _load() -> Dict[str, dict]:
    """Premium ma'lumotlarni fayldan o'qiydi. Format: {user_id: {info}}."""
    if not _PATH.exists():
        return {}
    try:
        with _PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items()}
    except Exception:  # noqa: BLE001
        logger.exception("premium faylni o'qishda xato")
    return {}


def _save(data: Dict[str, dict]) -> None:
    try:
        with _PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        logger.exception("premium faylni saqlashda xato")


def is_admin(user_id: int | str | None, username: str | None = None) -> bool:
    """Foydalanuvchi admin (egasi)mi?"""
    if user_id is not None and config.ADMIN_ID and str(user_id) == str(config.ADMIN_ID):
        return True
    if username and username.lstrip("@").lower() == config.ADMIN_USERNAME:
        return True
    return False


def is_premium(user_id: int | str | None, username: str | None = None) -> bool:
    """Foydalanuvchi premium (yoki admin)mi?"""
    if is_admin(user_id, username):
        return True
    if user_id is None:
        return False
    with _LOCK:
        data = _load()
    return str(user_id) in data


def add_premium(user_id: int | str, username: str = "", days: int = 0) -> None:
    """Foydalanuvchini premiumga qo'shadi. days=0 -> muddatsiz."""
    with _LOCK:
        data = _load()
        entry = {
            "username": (username or "").lstrip("@"),
            "since": int(time.time()),
        }
        if days and days > 0:
            entry["expires"] = int(time.time()) + days * 86400
        data[str(user_id)] = entry
        _save(data)


def remove_premium(user_id: int | str) -> bool:
    """Premiumdan o'chiradi. Topilsa True qaytaradi."""
    with _LOCK:
        data = _load()
        if str(user_id) in data:
            del data[str(user_id)]
            _save(data)
            return True
    return False


def cleanup_expired() -> None:
    """Muddati o'tgan obunalarni o'chiradi."""
    now = int(time.time())
    with _LOCK:
        data = _load()
        changed = False
        for uid in list(data.keys()):
            exp = data[uid].get("expires")
            if exp and exp < now:
                del data[uid]
                changed = True
        if changed:
            _save(data)


def list_premium() -> Dict[str, dict]:
    """Barcha premium foydalanuvchilar ro'yxati."""
    cleanup_expired()
    with _LOCK:
        return _load()
