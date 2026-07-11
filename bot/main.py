"""Telegram-бот: кнопка для открытия мини-аппа PlayBot.

Запуск:  python -m bot.main
"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import db  # noqa: E402  (общая база с API)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

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


@dp.message(Command("addpromo"))
async def cmd_addpromo(message: Message):
    """Добавление промокода на лету: /addpromo КОД НАГРАДА АКТИВАЦИИ"""
    if message.from_user.id != ADMIN_ID:
        return  # молча игнорируем не-админов
    parts = (message.text or "").split()
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].isdigit():
        await message.answer(
            "Формат: /addpromo КОД НАГРАДА АКТИВАЦИИ\n"
            "Например: /addpromo BONUS500 500 100"
        )
        return
    code, reward, uses = parts[1], int(parts[2]), int(parts[3])
    if db.add_promo(code, reward, uses):
        await message.answer(
            f"✅ Промокод <b>{code.upper()}</b> создан:\n"
            f"🪙 {reward} монет · {uses} активаций",
            parse_mode="HTML",
        )
    else:
        await message.answer("Такой код уже существует")


async def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise SystemExit("Укажите BOT_TOKEN в переменных окружения (.env)")
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
