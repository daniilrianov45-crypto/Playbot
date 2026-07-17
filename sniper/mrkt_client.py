"""Лёгкий клиент MRKT (api.tgmrkt.io) — своя реализация по задокументированной
(реверс-инжиниринг сообщества) схеме, без сторонней библиотеки.

Auth: обмениваем текущую Telegram-сессию (Pyrogram) на токен MRKT через
RequestAppWebView -> tgWebAppData -> POST /auth. Токен живёт больше суток,
но пере-авторизуемся при 401.
"""
import random
from urllib.parse import unquote

from curl_cffi import requests as cffi_requests
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName

API_BASE = "https://api.tgmrkt.io/api/v1"

_UAS = [
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
]


async def get_token(app: Client) -> str:
    """Меняет текущую Telegram-сессию (Pyrogram) на токен MRKT."""
    peer = await app.resolve_peer("mrkt")
    bot_app = InputBotAppShortName(bot_id=peer, short_name="app")
    web_view = await app.invoke(RequestAppWebView(peer=peer, app=bot_app, platform="android"))
    init_data = unquote(web_view.url.split("tgWebAppData=", 1)[1].split("&tgWebAppVersion", 1)[0])
    r = cffi_requests.post(f"{API_BASE}/auth", json={"data": init_data}, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


def _headers(token: str) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://cdn.tgmrkt.io",
        "Referer": "https://cdn.tgmrkt.io/",
        "User-Agent": random.choice(_UAS),
        "Authorization": token,
        "Cookie": f"access_token={token}",
    }


def fetch_saling(token: str, count: int = 20, cursor: str = "",
                  ordering: str = "Price", low_to_high: bool = True) -> dict:
    """Одна страница активных лотов, по умолчанию сортировка по цене (дешёвые
    сверху) — единственный вариант, подтверждённый рабочим примером в
    документации реверс-инжиниринга. "ordering": null (сортировка по
    времени) на практике возвращает 400 — не используем.
    Поднимает исключение (в т.ч. с "401" в тексте) при ошибке HTTP.
    """
    body = {
        "collectionNames": [], "modelNames": [], "backdropNames": [], "symbolNames": [],
        "ordering": ordering, "lowToHigh": low_to_high,
        "maxPrice": None, "minPrice": None, "mintable": None, "number": None,
        "count": count, "cursor": cursor,
    }
    r = cffi_requests.post(f"{API_BASE}/gifts/saling", json=body, headers=_headers(token), timeout=15)
    if r.status_code == 401:
        raise RuntimeError("401 Unauthorized (токен MRKT истёк)")
    r.raise_for_status()
    return r.json()
