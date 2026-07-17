"""Прокси для sniper — свой отдельный (MRKT_PROXY), чтобы не делить
соединение с основным ботом. Если MRKT_PROXY не задан, используем
BOT_PROXY как запасной вариант."""
import os
from urllib.parse import urlparse


def proxy_url() -> str:
    return (os.environ.get("MRKT_PROXY") or os.environ.get("BOT_PROXY") or "").strip()


def pyrogram_proxy() -> dict | None:
    url = proxy_url()
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
