"""Скачивает картинки подарков Telegram в webapp/gifts/.

Мини-апп сам подхватит их: иконка предмета ищется по webapp/gifts/<Название>.png,
если файла нет — показывается эмодзи.

Два источника:
1. Публичный CDN картинок коллекционных подарков (cdn.changes.tg) —
   качаем по названиям из каталога кейсов.
2. Bot API getAvailableGifts (нужен BOT_TOKEN) — официальные стикеры
   обычных звёздных подарков, сохраняются как <star_count>-stars.webp.

Запуск:  python -m scripts.sync_gifts
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from server import games  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "webapp", "gifts")
CDN = "https://cdn.changes.tg/gifts/models/{name}/png/Original.png"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


def download(url: str, path: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  ✗ {url}: {e}")
        return False


def sync_collectibles():
    """Картинки коллекционных подарков из каталога кейсов."""
    names = {
        item["name"]
        for case in games.CASES.values()
        for item in case["items"]
        if not item.get("stars")
    }
    print(f"Коллекционные подарки из каталога: {len(names)}")
    for name in sorted(names):
        path = os.path.join(OUT_DIR, f"{name}.png")
        if os.path.exists(path):
            print(f"  = {name} (уже есть)")
            continue
        url = CDN.format(name=urllib.parse.quote(name))
        if download(url, path):
            print(f"  ✓ {name}")


def sync_star_gifts():
    """Официальные стикеры обычных подарков через Bot API."""
    if not BOT_TOKEN:
        print("BOT_TOKEN не задан — пропускаю официальные звёздные подарки")
        return
    api = f"https://api.telegram.org/bot{BOT_TOKEN}"

    def call(method, **params):
        qs = urllib.parse.urlencode(params)
        with urllib.request.urlopen(f"{api}/{method}?{qs}", timeout=15) as resp:
            data = json.load(resp)
        if not data.get("ok"):
            raise RuntimeError(data)
        return data["result"]

    gifts = call("getAvailableGifts")["gifts"]
    print(f"Официальных звёздных подарков: {len(gifts)}")
    for g in gifts:
        sticker = g["sticker"]
        thumb = sticker.get("thumbnail") or sticker
        path = os.path.join(OUT_DIR, f"{g['star_count']}-stars-{g['id']}.webp")
        if os.path.exists(path):
            continue
        file = call("getFile", file_id=thumb["file_id"])
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file['file_path']}"
        if download(url, path):
            print(f"  ✓ {g['star_count']}⭐ ({g['id']})")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    sync_collectibles()
    sync_star_gifts()
    print("Готово. Недостающие картинки можно доложить вручную:"
          " webapp/gifts/<Название подарка>.png")
