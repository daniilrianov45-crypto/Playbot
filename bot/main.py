"""Telegram-бот: кнопка для открытия мини-аппа PlayBot.

Запуск:  python -m bot.main
"""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com")

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🎮 Играть", web_app=WebAppInfo(url=WEBAPP_URL))
        ]]
    )
    await message.answer(
        "🚀 <b>PlayBot</b> — мини-игры с честной механикой!\n\n"
        "🎯 Краш, слоты, мины и кейсы\n"
        "🔍 Каждый результат можно проверить (provably fair)\n"
        "🪙 Новичкам — 5000 монет на старт\n\n"
        "Жми «Играть»!",
        reply_markup=kb,
        parse_mode="HTML",
    )


async def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise SystemExit("Укажите BOT_TOKEN в переменных окружения (.env)")
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
