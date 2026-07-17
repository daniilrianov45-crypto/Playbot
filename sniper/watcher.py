"""Вотчер лотов MRKT: раз в POLL_SECONDS проверяет свежие активные лоты,
сравнивает цену с floor-ценой (её MRKT сам присылает в каждом лоте) и шлёт
оповещение в Telegram, если лот дешевле floor на DISCOUNT_THRESHOLD% и больше.

Запуск (после одноразового `python -m sniper.login`):
    python -m sniper.watcher
"""
import asyncio
import logging
import os
import re
import sqlite3
import time

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from pyrogram import Client

from . import mrkt_client
from .tgproxy import proxy_url, pyrogram_proxy

API_ID = int(os.environ.get("MRKT_API_ID", "0"))
API_HASH = os.environ.get("MRKT_API_HASH", "")
SESSION_NAME = os.environ.get("MRKT_SESSION_NAME", "mrkt_session")
SESSION_DIR = os.path.dirname(__file__)

ALERT_BOT_TOKEN = os.environ.get("ALERT_BOT_TOKEN", "")
ALERT_CHAT_ID = int(os.environ.get("ALERT_CHAT_ID", "0"))

DISCOUNT_THRESHOLD = float(os.environ.get("DISCOUNT_THRESHOLD", "10"))  # % ниже floor
HOT_THRESHOLD = float(os.environ.get("HOT_THRESHOLD", "20"))            # % для 🔥-пометки
RESELL_MARGIN = float(os.environ.get("RESELL_MARGIN", "3"))             # % ниже floor для быстрой перепродажи
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "25"))
PAGES_PER_CYCLE = int(os.environ.get("PAGES_PER_CYCLE", "3"))
PAGE_COUNT = 20

DB_PATH = os.path.join(SESSION_DIR, "seen.db")


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS seen(gift_id TEXT PRIMARY KEY, seen_at INTEGER)")
    return conn


def _already_seen(conn: sqlite3.Connection, gift_id: str) -> bool:
    return conn.execute("SELECT 1 FROM seen WHERE gift_id=?", (gift_id,)).fetchone() is not None


def _mark_seen(conn: sqlite3.Connection, gift_id: str) -> None:
    conn.execute("INSERT OR IGNORE INTO seen(gift_id, seen_at) VALUES (?, ?)", (gift_id, int(time.time())))
    conn.commit()


def _prune_seen(conn: sqlite3.Connection, max_age: int = 7 * 86400) -> None:
    conn.execute("DELETE FROM seen WHERE seen_at < ?", (int(time.time()) - max_age,))
    conn.commit()


def _nft_link(collection_title: str, number) -> str:
    """Официальная страница подарка в Telegram — t.me/nft даёт готовое превью
    с картинкой в самом сообщении, отдельно грузить изображение не нужно."""
    slug = re.sub(r"[^a-zA-Z0-9]", "", collection_title or "")
    return f"https://t.me/nft/{slug}-{number}" if slug and number else ""


def _fmt_alert(g: dict, discount: float) -> str:
    price = (g.get("salePrice") or 0) / 1e9
    floor_nano = g.get("floorPriceNanoTONsByBackdropModel") or g.get("floorPriceNanoTONsByCollection") or 0
    floor = floor_nano / 1e9
    mark = "🔥🔥🔥" if discount >= HOT_THRESHOLD else "🎯"
    title = g.get("modelTitle") or g.get("title") or g.get("collectionTitle") or "Подарок"
    backdrop = g.get("backdropName", "")
    number = g.get("number", "")
    collection = g.get("collectionTitle", "")
    link = _nft_link(g.get("collectionTitle") or g.get("collectionName") or "", number)
    resell = floor * (1 - RESELL_MARGIN / 100)
    profit_pct = (resell - price) / price * 100 if price else 0
    lines = [
        f"{mark} <b>{discount:.0f}% ниже floor!</b>\n",
        f"{title}" + (f" · {backdrop}" if backdrop else "") + (f" #{number}" if number else ""),
        f"Коллекция: {collection}\n",
        f"Цена: <b>{price:.2f} TON</b>",
        f"Floor: {floor:.2f} TON",
        f"💡 Продать быстро: <b>~{resell:.2f} TON</b> (на {RESELL_MARGIN:.0f}% ниже floor,"
        f" всё равно ~{profit_pct:.0f}% навара)",
    ]
    if link:
        lines += ["", link]
    lines += ["", "Открыть MRKT: t.me/mrkt"]
    return "\n".join(lines)


async def _cycle(app: Client, bot: Bot, conn: sqlite3.Connection, token: str) -> str:
    """Один проход по свежим лотам. Возвращает (возможно обновлённый) токен."""
    cursor = ""
    for _ in range(PAGES_PER_CYCLE):
        try:
            data = mrkt_client.fetch_saling(token, count=PAGE_COUNT, cursor=cursor,
                                             ordering="Price", low_to_high=True)
        except Exception as e:
            if "401" in str(e):
                token = await mrkt_client.get_token(app)
                data = mrkt_client.fetch_saling(token, count=PAGE_COUNT, cursor=cursor,
                                             ordering="Price", low_to_high=True)
            else:
                raise
        gifts = data.get("gifts", [])
        if not gifts:
            break
        for g in gifts:
            gid = str(g.get("id"))
            if _already_seen(conn, gid):
                continue
            _mark_seen(conn, gid)
            price = g.get("salePrice") or 0
            floor = g.get("floorPriceNanoTONsByBackdropModel") or g.get("floorPriceNanoTONsByCollection") or 0
            if not price or not floor or price >= floor:
                continue
            discount = (floor - price) / floor * 100
            if discount >= DISCOUNT_THRESHOLD:
                try:
                    await bot.send_message(ALERT_CHAT_ID, _fmt_alert(g, discount), parse_mode="HTML")
                except Exception:
                    logging.exception("не смог отправить оповещение")
        cursor = data.get("cursor") or ""
        if not cursor:
            break
    return token


async def run():
    if not (API_ID and API_HASH and ALERT_BOT_TOKEN and ALERT_CHAT_ID):
        raise SystemExit(
            "Заполните MRKT_API_ID, MRKT_API_HASH, ALERT_BOT_TOKEN, ALERT_CHAT_ID в .env"
        )
    logging.basicConfig(level=logging.INFO)
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, workdir=SESSION_DIR,
                 proxy=pyrogram_proxy())
    bot_session = AiohttpSession(proxy=proxy_url()) if proxy_url() else None
    bot = Bot(ALERT_BOT_TOKEN, session=bot_session)
    conn = _db()

    async with app:
        token = await mrkt_client.get_token(app)
        await bot.send_message(ALERT_CHAT_ID, "👀 Вотчер MRKT запущен — слежу за лотами.")
        cycle_n = 0
        while True:
            cycle_n += 1
            try:
                token = await _cycle(app, bot, conn, token)
                if cycle_n % 500 == 0:
                    _prune_seen(conn)
            except Exception as e:
                logging.exception("сбой цикла вотчера")
                try:
                    await bot.send_message(ALERT_CHAT_ID, f"⚠️ Ошибка вотчера: {e}")
                except Exception:
                    pass
            await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
