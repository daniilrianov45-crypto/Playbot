"""Telegram-бот: кнопка для открытия мини-аппа PlayBot.

Запуск:  python -m bot.main
"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
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
# Прокси для доступа к api.telegram.org, если хостинг блокирует прямое
# подключение (напр. http://user:pass@host:port или socks5://host:port).
BOT_PROXY = os.environ.get("BOT_PROXY", "").strip()

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.first_name or "друг"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Играть", web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton(
                text="🎁 Как заработать звёзды",
                web_app=WebAppInfo(url=WEBAPP_URL + "?screen=tasks"),
            )],
        ]
    )
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        "🚀 <b>PlayBot</b> — мини-игры с честной механикой!\n\n"
        "🎯 Краш, слоты, мины и кейсы с подарками Telegram\n"
        "🔍 Каждый результат можно проверить (provably fair)\n"
        "🎁 Открой бесплатный кейс и выполняй задания — звёзды за это начисляются сразу\n\n"
        "Жми «Играть»!",
        reply_markup=kb,
        parse_mode="HTML",
    )


def _is_owner(message: Message) -> bool:
    """Владелец из .env — только он назначает/снимает остальных админов."""
    return message.from_user.id == ADMIN_ID


def _is_admin(message: Message) -> bool:
    uid = message.from_user.id
    return uid == ADMIN_ID or db.is_extra_admin(uid)


async def _resolve(message: Message, who: str) -> dict | None:
    user = db.find_user(who)
    if user is None:
        await message.answer("Игрок не найден в базе")
    return user


@dp.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    """Назначить админа: /addadmin <id или @username>.

    Только владелец (ADMIN_ID из .env) может назначать — чтобы назначенный
    админ не мог тайно добавить себе сообщников.
    """
    if not _is_owner(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /addadmin @username или /addadmin 12345678")
        return
    who = parts[1].lstrip("@")
    if who.isdigit():
        new_id, username = int(who), ""
        known = db.find_user(who)
        if known:
            username = known["username"]
    else:
        known = await _resolve(message, who)
        if known is None:
            return
        new_id, username = known["id"], known["username"]
    if new_id == ADMIN_ID:
        await message.answer("Вы и так главный админ")
        return
    if db.add_admin(new_id, username, message.from_user.id):
        await message.answer(
            f"✅ Назначен админом: id {new_id}" + (f" (@{username})" if username else ""),
        )
    else:
        await message.answer("Этот пользователь уже админ")


@dp.message(Command("deladmin"))
async def cmd_deladmin(message: Message):
    """Снять админа: /deladmin <id или @username>. Только владелец."""
    if not _is_owner(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /deladmin @username или /deladmin 12345678")
        return
    who = parts[1].lstrip("@")
    if who.isdigit():
        target_id = int(who)
    else:
        known = await _resolve(message, who)
        if known is None:
            return
        target_id = known["id"]
    if db.remove_admin(target_id):
        await message.answer(f"✅ Админ id {target_id} снят")
    else:
        await message.answer("Этот пользователь не в списке назначенных админов")


@dp.message(Command("admins"))
async def cmd_admins(message: Message):
    """Список назначенных админов: /admins. Доступно любому админу."""
    if not _is_admin(message):
        return
    admins = db.list_admins()
    lines = [f"👑 Главный админ: id {ADMIN_ID} (владелец)"]
    if admins:
        lines.append("\n🛡 Назначенные админы:")
        lines += [
            f"  id {a['user_id']}" + (f" (@{a['username']})" if a["username"] else "")
            for a in admins
        ]
    else:
        lines.append("\nНазначенных админов пока нет")
    await message.answer("\n".join(lines))


@dp.message(Command("addpromo"))
async def cmd_addpromo(message: Message):
    """Добавление промокода на лету: /addpromo КОД НАГРАДА АКТИВАЦИИ"""
    if not _is_admin(message):
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
            f"⭐ {reward} звёзд · {uses} активаций",
            parse_mode="HTML",
        )
    else:
        await message.answer("Такой код уже существует")


@dp.message(Command("give"))
async def cmd_give(message: Message):
    """Начислить звёзды: /give <id или @username> <кол-во>"""
    if not _is_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[2].lstrip("-").isdigit():
        await message.answer("Формат: /give @username 100")
        return
    user = await _resolve(message, parts[1])
    if user is None:
        return
    bal = db.credit(user["id"], int(parts[2]))
    await message.answer(
        f"✅ Начислено <b>{parts[2]}</b> ⭐ игроку {user['first_name']}\n"
        f"Баланс: <b>{bal}</b> ⭐", parse_mode="HTML",
    )


@dp.message(Command("take"))
async def cmd_take(message: Message):
    """Списать звёзды: /take <id или @username> <кол-во>"""
    if not _is_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[2].isdigit():
        await message.answer("Формат: /take @username 50")
        return
    user = await _resolve(message, parts[1])
    if user is None:
        return
    bal = db.take_balance(user["id"], int(parts[2]))
    await message.answer(
        f"✅ Списано <b>{parts[2]}</b> ⭐ у игрока {user['first_name']}\n"
        f"Баланс: <b>{bal}</b> ⭐", parse_mode="HTML",
    )


@dp.message(Command("gift"))
async def cmd_gift(message: Message):
    """Выдать подарок в инвентарь: /gift <id или @username> <emoji> <название> <цена>
    Пример: /gift @user 🐸 Kissed Frog 500"""
    if not _is_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 5 or not parts[-1].isdigit():
        await message.answer("Формат: /gift @user 🐸 Kissed Frog 500")
        return
    user = await _resolve(message, parts[1])
    if user is None:
        return
    emoji, value = parts[2], int(parts[-1])
    name = " ".join(parts[3:-1])
    db.add_inventory_item(user["id"], {"name": name, "emoji": emoji, "value": value}, "admin")
    await message.answer(
        f"✅ Выдан подарок {emoji} <b>{name}</b> ({value}⭐) игроку {user['first_name']}",
        parse_mode="HTML",
    )


@dp.message(Command("takegift"))
async def cmd_takegift(message: Message):
    """Забрать подарок из инвентаря (после выдачи приза): /takegift <id/@user> <название>"""
    if not _is_admin(message):
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Формат: /takegift @user Kissed Frog")
        return
    user = await _resolve(message, parts[1])
    if user is None:
        return
    item = db.remove_inventory_by_name(user["id"], parts[2])
    if item is None:
        await message.answer("У игрока нет такого подарка в инвентаре")
        return
    await message.answer(
        f"✅ Подарок {item['emoji']} <b>{item['name']}</b> убран из инвентаря "
        f"{user['first_name']} (отмечен как выданный)", parse_mode="HTML",
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика бота: /stats"""
    if not _is_admin(message):
        return
    s = db.bot_stats()
    await message.answer(
        "📊 <b>Статистика PlayBot</b>\n\n"
        f"👥 Игроков всего: <b>{s['users']}</b>\n"
        f"🆕 Новых за сутки: <b>{s['new_today']}</b>\n"
        f"⭐ Звёзд на балансах: <b>{s['balance']}</b>\n"
        f"🎒 Подарков в инвентарях: <b>{s['gifts']}</b>\n"
        f"🎲 Ставок за сутки: <b>{s['bets_today']}</b>\n"
        f"💰 Прибыль за сутки: <b>{s['profit_today']}</b> ⭐",
        parse_mode="HTML",
    )


@dp.message(Command("admin", "help"))
async def cmd_admin(message: Message):
    """Список админ-команд: /admin"""
    if not _is_admin(message):
        return
    lines = [
        "🛠 <b>Админ-команды</b>\n",
        "<code>/give @user 100</code> — начислить звёзды",
        "<code>/take @user 50</code> — списать звёзды",
        "<code>/gift @user 🐸 Kissed Frog 500</code> — выдать подарок",
        "<code>/takegift @user Kissed Frog</code> — убрать подарок (после выдачи)",
        "<code>/inv @user</code> — инвентарь и баланс игрока",
        "<code>/addpromo КОД 500 100</code> — создать промокод",
        "<code>/stats</code> — статистика бота",
        "<code>/admins</code> — список назначенных админов",
    ]
    if _is_owner(message):
        lines += [
            "\n👑 <b>Только для владельца:</b>",
            "<code>/addadmin @user</code> — назначить админа",
            "<code>/deladmin @user</code> — снять админа",
        ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("inv"))
async def cmd_inv(message: Message):
    """Проверка инвентаря игрока поддержкой: /inv <id или @username>.

    Показывает НАСТОЯЩИЙ инвентарь из базы — скриншоты игрока подделать можно,
    эту команду нельзя.
    """
    if not _is_admin(message):
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
    session = AiohttpSession(proxy=BOT_PROXY) if BOT_PROXY else None
    bot = Bot(BOT_TOKEN, session=session)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
