"""Прокси для Pyrogram — переиспользуем тот же BOT_PROXY, что и обычный
бот, если сервер не может напрямую достучаться до Telegram."""
import os
from urllib.parse import urlparse


def pyrogram_proxy() -> dict | None:
    url = os.environ.get("BOT_PROXY", "").strip()
    if not url:
        return None
    p = urlparse(url)
    return {
        "scheme": p.scheme,
        "hostname": p.hostname,
        "port": p.port,
        "username": p.username,
        "password": p.password,
    }
