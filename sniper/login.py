"""Однократный вход под личным Telegram-аккаунтом для MRKT-вотчера.

Запускать вручную в терминале на сервере (номер и код вводятся только
здесь, никуда кроме Telegram не уходят):

    python -m sniper.login

Сессия сохранится в файл <MRKT_SESSION_NAME>.session рядом с этим
модулем — дальше watcher.py использует её без повторного входа.
"""
import asyncio
import os

from pyrogram import Client

from .tgproxy import pyrogram_proxy

API_ID = int(os.environ.get("MRKT_API_ID", "0"))
API_HASH = os.environ.get("MRKT_API_HASH", "")
SESSION_NAME = os.environ.get("MRKT_SESSION_NAME", "mrkt_session")
SESSION_DIR = os.path.dirname(__file__)


async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Укажите MRKT_API_ID и MRKT_API_HASH в .env")
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, workdir=SESSION_DIR,
                 proxy=pyrogram_proxy())
    async with app:
        me = await app.get_me()
        print(f"Успешный вход: {me.first_name} (id {me.id}).")
        print(f"Сессия сохранена в {os.path.join(SESSION_DIR, SESSION_NAME)}.session — больше вход не понадобится.")


if __name__ == "__main__":
    asyncio.run(main())
