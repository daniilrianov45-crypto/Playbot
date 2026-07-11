"""Проверка подписи Telegram WebApp initData."""
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DEV_MODE = os.environ.get("DEV_MODE", "0") == "1"

AUTH_TTL = 24 * 3600  # initData старше суток не принимаем


def validate_init_data(init_data: str) -> dict | None:
    """Возвращает объект user из initData или None, если подпись неверна."""
    if not init_data:
        if DEV_MODE:
            return {"id": 1, "username": "dev", "first_name": "Dev"}
        return None
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = pairs.pop("hash")
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, received_hash):
            return None
        if time.time() - int(pairs.get("auth_date", 0)) > AUTH_TTL:
            return None
        return json.loads(pairs["user"])
    except (KeyError, ValueError):
        return None
