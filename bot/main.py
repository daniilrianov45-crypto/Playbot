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
        "⭐ Новичкам — 100 звёзд на старт\n\n"
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


@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    """Проверка инвентаря игрока поддержкой: /inv <id или @username>.

    Показывает НАСТОЯЩИЙ инвентарь из базы — скриншоты игрока подделать можно,
    эту команду нельзя.
    """
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /inv 12345678 или /inv @username")
        return
    user = db.find_user(parts[1])
    if user is None:
        await message.answer("Игрок не найден в базе")
        return
    items = db.get_inventory(user["id"])
    lines = [
        f"👤 <b>{user['first_name']}</b>"
        + (f" (@{user['username']})" if user["username"] else "")
        + f" · id {user['id']}",
        f"⭐ Баланс: <b>{user['balance']}</b>",
        "",
        f"🎒 Инвентарь ({len(items)}):",
    ]
    if items:
        lines += [f"  {it['emoji']} {it['name']} — {it['value']}⭐" for it in items]
    else:
        lines.append("  пусто")
    await message.answer("\n".join(lines), parse_mode="HTML")


async def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise SystemExit("Укажите BOT_TOKEN в переменных окружения (.env)")
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
