"""SQLite-хранилище: пользователи, сиды честности, активные игры, история."""
import json
import os
import random
import sqlite3
import threading
import time

DB_PATH = os.environ.get(
    "DB_PATH", os.path.join(os.path.dirname(__file__), "..", "playbot.db")
)

START_BALANCE = 0  # новичок стартует с нуля (зарабатывает: кейсы, задания, рефералка)

_lock = threading.Lock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    photo_url TEXT DEFAULT '',
    balance INTEGER NOT NULL,
    referrer_id INTEGER,
    ref_earned INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    value INTEGER NOT NULL,
    case_id TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS case_opens(
    user_id INTEGER NOT NULL,
    case_id TEXT NOT NULL,
    last_open INTEGER NOT NULL,
    PRIMARY KEY(user_id, case_id)
);
CREATE TABLE IF NOT EXISTS task_claims(
    user_id INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    claimed_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, task_id)
);
CREATE TABLE IF NOT EXISTS promo_codes(
    code TEXT PRIMARY KEY,
    reward INTEGER NOT NULL,
    max_uses INTEGER NOT NULL,
    uses INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS promo_redemptions(
    user_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    redeemed_at INTEGER NOT NULL,
    PRIMARY KEY(user_id, code)
);
CREATE TABLE IF NOT EXISTS kv(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS admins(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    added_by INTEGER NOT NULL,
    added_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS crash_rounds(
    round_id INTEGER PRIMARY KEY,
    point REAL NOT NULL,
    crashed_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS seeds(
    user_id INTEGER PRIMARY KEY,
    server_seed TEXT NOT NULL,
    client_seed TEXT NOT NULL,
    nonce INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS seed_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    server_seed TEXT NOT NULL,
    client_seed TEXT NOT NULL,
    last_nonce INTEGER NOT NULL,
    revealed_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS active_games(
    user_id INTEGER NOT NULL,
    game TEXT NOT NULL,
    state TEXT NOT NULL,
    PRIMARY KEY(user_id, game)
);
CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game TEXT NOT NULL,
    bet INTEGER NOT NULL,
    payout INTEGER NOT NULL,
    detail TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS trade_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    gift_name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    points INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);
CREATE TABLE IF NOT EXISTS shop_orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    points INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);
"""
with _lock:
    _conn.executescript(_SCHEMA)
    for migration in (  # миграции старых баз
        "ALTER TABLE users ADD COLUMN photo_url TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN referrer_id INTEGER",
        "ALTER TABLE users ADD COLUMN ref_earned INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN exchange_balance INTEGER NOT NULL DEFAULT 0",
    ):
        try:
            _conn.execute(migration)
        except sqlite3.OperationalError:
            pass
    _conn.commit()

# уровни партнёрки: (минимум приглашённых, доля от проигрышей друзей в %)
REF_LEVELS = [(20, 20), (5, 15), (0, 10)]
REF_BONUS_FRIEND = 50    # бонус приглашённому, ⭐
REF_BONUS_INVITER = 25   # бонус пригласившему за каждого друга, ⭐


def ref_percent(invited: int) -> int:
    for need, pct in REF_LEVELS:
        if invited >= need:
            return pct
    return REF_LEVELS[-1][1]


def get_or_create_user(user_id: int, username: str, first_name: str, photo_url: str = "") -> dict:
    with _lock:
        row = _conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            _conn.execute(
                "INSERT INTO users(id, username, first_name, photo_url, balance, created_at)"
                " VALUES(?,?,?,?,?,?)",
                (user_id, username, first_name, photo_url, START_BALANCE, int(time.time())),
            )
        else:
            _conn.execute(  # имя/фото в Telegram могли поменяться
                "UPDATE users SET username=?, first_name=?, photo_url=? WHERE id=?",
                (username, first_name, photo_url or row["photo_url"], user_id),
            )
        _conn.commit()
        return dict(_conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


def get_balance(user_id: int) -> int:
    with _lock:
        row = _conn.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        return row["balance"] if row else 0


def try_debit(user_id: int, amount: int) -> bool:
    """Атомарно списывает ставку; False, если не хватает баланса."""
    with _lock:
        cur = _conn.execute(
            "UPDATE users SET balance = balance - ? WHERE id=? AND balance >= ?",
            (amount, user_id, amount),
        )
        _conn.commit()
        return cur.rowcount == 1


def credit(user_id: int, amount: int) -> int:
    with _lock:
        _conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id)
        )
        _conn.commit()
        row = _conn.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        return row["balance"]


def get_seeds(user_id: int, make_server_seed, make_client_seed) -> dict:
    with _lock:
        row = _conn.execute("SELECT * FROM seeds WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            _conn.execute(
                "INSERT INTO seeds(user_id, server_seed, client_seed, nonce) VALUES(?,?,?,0)",
                (user_id, make_server_seed(), make_client_seed()),
            )
            _conn.commit()
            row = _conn.execute("SELECT * FROM seeds WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)


def bump_nonce(user_id: int) -> None:
    with _lock:
        _conn.execute("UPDATE seeds SET nonce = nonce + 1 WHERE user_id=?", (user_id,))
        _conn.commit()


def rotate_seed(user_id: int, new_server_seed: str, new_client_seed: str) -> dict:
    """Раскрывает старый server seed (кладёт в историю) и ставит новый."""
    with _lock:
        old = _conn.execute("SELECT * FROM seeds WHERE user_id=?", (user_id,)).fetchone()
        _conn.execute(
            "INSERT INTO seed_history(user_id, server_seed, client_seed, last_nonce, revealed_at)"
            " VALUES(?,?,?,?,?)",
            (user_id, old["server_seed"], old["client_seed"], old["nonce"], int(time.time())),
        )
        _conn.execute(
            "UPDATE seeds SET server_seed=?, client_seed=?, nonce=0 WHERE user_id=?",
            (new_server_seed, new_client_seed, user_id),
        )
        _conn.commit()
        return dict(old)


def get_active_game(user_id: int, game: str) -> dict | None:
    with _lock:
        row = _conn.execute(
            "SELECT state FROM active_games WHERE user_id=? AND game=?", (user_id, game)
        ).fetchone()
        return json.loads(row["state"]) if row else None


def set_active_game(user_id: int, game: str, state: dict) -> None:
    with _lock:
        _conn.execute(
            "INSERT OR REPLACE INTO active_games(user_id, game, state) VALUES(?,?,?)",
            (user_id, game, json.dumps(state)),
        )
        _conn.commit()


def clear_active_game(user_id: int, game: str) -> None:
    with _lock:
        _conn.execute(
            "DELETE FROM active_games WHERE user_id=? AND game=?", (user_id, game)
        )
        _conn.commit()


def add_history(user_id: int, game: str, bet: int, payout: int, detail: dict) -> None:
    """Пишет раунд в историю и начисляет партнёрскую комиссию рефереру."""
    with _lock:
        _conn.execute(
            "INSERT INTO history(user_id, game, bet, payout, detail, created_at) VALUES(?,?,?,?,?,?)",
            (user_id, game, bet, payout, json.dumps(detail), int(time.time())),
        )
        net = bet - payout  # прибыль площадки с раунда
        if net > 0:
            row = _conn.execute(
                "SELECT referrer_id FROM users WHERE id=?", (user_id,)
            ).fetchone()
            ref = row["referrer_id"] if row else None
            if ref:
                invited = _conn.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE referrer_id=?", (ref,)
                ).fetchone()["c"]
                commission = net * ref_percent(invited) // 100
                if commission > 0:
                    _conn.execute(
                        "UPDATE users SET balance = balance + ?, ref_earned = ref_earned + ?"
                        " WHERE id=?",
                        (commission, commission, ref),
                    )
        _conn.commit()


def take_balance(user_id: int, amount: int) -> int | None:
    """Списывает звёзды (не ниже нуля); None, если пользователя нет."""
    with _lock:
        row = _conn.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            return None
        new_bal = max(0, row["balance"] - amount)
        _conn.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, user_id))
        _conn.commit()
        return new_bal


def remove_inventory_by_name(user_id: int, name: str) -> dict | None:
    """Удаляет один предмет по имени (для выдачи приза поддержкой)."""
    with _lock:
        row = _conn.execute(
            "SELECT * FROM inventory WHERE user_id=? AND LOWER(name)=LOWER(?)"
            " ORDER BY id LIMIT 1",
            (user_id, name),
        ).fetchone()
        if row is None:
            return None
        _conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
        _conn.commit()
        return dict(row)


def bot_stats() -> dict:
    with _lock:
        users = _conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        balance = _conn.execute("SELECT COALESCE(SUM(balance),0) AS s FROM users").fetchone()["s"]
        gifts = _conn.execute("SELECT COUNT(*) AS c FROM inventory").fetchone()["c"]
        day_ago = int(time.time()) - 86400
        new_today = _conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE created_at>=?", (day_ago,)
        ).fetchone()["c"]
        bets_today = _conn.execute(
            "SELECT COUNT(*) AS c FROM history WHERE created_at>=?", (day_ago,)
        ).fetchone()["c"]
        # прибыль площадки за сутки = ставки - выплаты
        pl = _conn.execute(
            "SELECT COALESCE(SUM(bet-payout),0) AS s FROM history WHERE created_at>=?",
            (day_ago,),
        ).fetchone()["s"]
    return {"users": users, "balance": balance, "gifts": gifts,
            "new_today": new_today, "bets_today": bets_today, "profit_today": pl}


def all_user_ids() -> list[int]:
    """Все id игроков — для рассылки."""
    with _lock:
        rows = _conn.execute("SELECT id FROM users").fetchall()
    return [r["id"] for r in rows]


# ------------------------------------------------------------- доп. админы
# ADMIN_ID из .env — главный админ (владелец), он всегда админ и не хранится
# здесь. Эта таблица — только назначенные им дополнительные админы.

def add_admin(user_id: int, username: str, added_by: int) -> bool:
    with _lock:
        try:
            _conn.execute(
                "INSERT INTO admins(user_id, username, added_by, added_at) VALUES(?,?,?,?)",
                (user_id, username, added_by, int(time.time())),
            )
            _conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_admin(user_id: int) -> bool:
    with _lock:
        cur = _conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        _conn.commit()
        return cur.rowcount > 0


def is_extra_admin(user_id: int) -> bool:
    with _lock:
        return _conn.execute(
            "SELECT 1 FROM admins WHERE user_id=?", (user_id,)
        ).fetchone() is not None


def list_admins() -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM admins ORDER BY added_at"
        ).fetchall()
        return [dict(r) for r in rows]


def find_user(query: str) -> dict | None:
    """Ищет пользователя по числовому ID или @username."""
    with _lock:
        if query.lstrip("@").isdigit():
            row = _conn.execute(
                "SELECT * FROM users WHERE id=?", (int(query.lstrip("@")),)
            ).fetchone()
        else:
            row = _conn.execute(
                "SELECT * FROM users WHERE LOWER(username)=LOWER(?)",
                (query.lstrip("@"),),
            ).fetchone()
        return dict(row) if row else None


def user_exists(user_id: int) -> bool:
    with _lock:
        return _conn.execute(
            "SELECT 1 FROM users WHERE id=?", (user_id,)
        ).fetchone() is not None


def set_referrer(user_id: int, ref_id: int) -> bool:
    """Привязывает реферера один раз; False, если нельзя (сам себя, нет такого, уже есть)."""
    if user_id == ref_id:
        return False
    with _lock:
        ref = _conn.execute("SELECT 1 FROM users WHERE id=?", (ref_id,)).fetchone()
        if ref is None:
            return False
        cur = _conn.execute(
            "UPDATE users SET referrer_id=? WHERE id=? AND referrer_id IS NULL",
            (ref_id, user_id),
        )
        _conn.commit()
        return cur.rowcount == 1


# ------------------------------------------------------------- задания

def task_metrics(user_id: int) -> dict:
    """Счётчики действий пользователя для прогресса заданий."""
    with _lock:
        rows = _conn.execute(
            "SELECT game, COUNT(*) AS n, SUM(CASE WHEN payout > 0 THEN 1 ELSE 0 END) AS wins"
            " FROM history WHERE user_id=? GROUP BY game",
            (user_id,),
        ).fetchall()
        invited = _conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referrer_id=?", (user_id,)
        ).fetchone()["c"]
    by_game = {r["game"]: r for r in rows}

    def count(game):
        return by_game[game]["n"] if game in by_game else 0

    return {
        "crash_rounds": count("crash"),
        "slots_spins": count("slots"),
        "mines_wins": by_game["mines"]["wins"] if "mines" in by_game else 0,
        "cases_opened": count("case"),
        "invited": invited,
    }


def claimed_tasks(user_id: int) -> set:
    with _lock:
        rows = _conn.execute(
            "SELECT task_id FROM task_claims WHERE user_id=?", (user_id,)
        ).fetchall()
        return {r["task_id"] for r in rows}


def claim_task(user_id: int, task_id: str, reward: int) -> bool:
    """Отмечает задание полученным и зачисляет награду; False, если уже забрано."""
    with _lock:
        try:
            _conn.execute(
                "INSERT INTO task_claims(user_id, task_id, claimed_at) VALUES(?,?,?)",
                (user_id, task_id, int(time.time())),
            )
        except sqlite3.IntegrityError:
            return False
        _conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id=?", (reward, user_id)
        )
        _conn.commit()
        return True


# ------------------------------------------------------------- промокоды

def add_promo(code: str, reward: int, max_uses: int) -> bool:
    with _lock:
        try:
            _conn.execute(
                "INSERT INTO promo_codes(code, reward, max_uses, created_at) VALUES(?,?,?,?)",
                (code.upper(), reward, max_uses, int(time.time())),
            )
            _conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def redeem_promo(user_id: int, code: str) -> int | str:
    """Возвращает награду или строку с причиной отказа."""
    code = code.strip().upper()
    with _lock:
        promo = _conn.execute(
            "SELECT * FROM promo_codes WHERE code=?", (code,)
        ).fetchone()
        if promo is None:
            return "Такого промокода нет"
        if promo["uses"] >= promo["max_uses"]:
            return "Промокод уже разобрали"
        try:
            _conn.execute(
                "INSERT INTO promo_redemptions(user_id, code, redeemed_at) VALUES(?,?,?)",
                (user_id, code, int(time.time())),
            )
        except sqlite3.IntegrityError:
            return "Вы уже активировали этот код"
        _conn.execute("UPDATE promo_codes SET uses = uses + 1 WHERE code=?", (code,))
        _conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id=?",
            (promo["reward"], user_id),
        )
        _conn.commit()
        return promo["reward"]


def referral_stats(user_id: int) -> dict:
    with _lock:
        invited = _conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE referrer_id=?", (user_id,)
        ).fetchone()["c"]
        earned = _conn.execute(
            "SELECT ref_earned FROM users WHERE id=?", (user_id,)
        ).fetchone()["ref_earned"]
    pct = ref_percent(invited)
    next_level = None
    for need, next_pct in sorted(REF_LEVELS):
        if invited < need:
            next_level = {"at": need, "percent": next_pct}
            break
    return {"invited": invited, "earned": earned, "percent": pct, "next_level": next_level}


def get_kv(key: str, default: str = "") -> str:
    with _lock:
        row = _conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_kv(key: str, value: str) -> None:
    with _lock:
        _conn.execute("INSERT OR REPLACE INTO kv(key, value) VALUES(?,?)", (key, value))
        _conn.commit()


def add_crash_round(round_id: int, point: float) -> None:
    with _lock:
        _conn.execute(
            "INSERT OR REPLACE INTO crash_rounds(round_id, point, crashed_at) VALUES(?,?,?)",
            (round_id, point, int(time.time())),
        )
        _conn.commit()


def last_crash_points(limit: int = 10) -> list[float]:
    """Точки взрыва последних общих раундов (новые первыми)."""
    with _lock:
        rows = _conn.execute(
            "SELECT point FROM crash_rounds ORDER BY round_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [r["point"] for r in rows]


# ------------------------------------------------------------- инвентарь

def add_inventory_item(user_id: int, item: dict, case_id: str) -> int:
    with _lock:
        cur = _conn.execute(
            "INSERT INTO inventory(user_id, name, emoji, value, case_id, created_at)"
            " VALUES(?,?,?,?,?,?)",
            (user_id, item["name"], item["emoji"], item["value"], case_id, int(time.time())),
        )
        _conn.commit()
        return cur.lastrowid


def get_inventory(user_id: int) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT id, name, emoji, value, case_id, created_at FROM inventory"
            " WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def sell_inventory_item(user_id: int, item_id: int) -> int | None:
    """Удаляет предмет и зачисляет его стоимость; None, если предмета нет."""
    with _lock:
        row = _conn.execute(
            "SELECT value FROM inventory WHERE id=? AND user_id=?", (item_id, user_id)
        ).fetchone()
        if row is None:
            return None
        _conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        _conn.execute(
            "UPDATE users SET balance = balance + ? WHERE id=?", (row["value"], user_id)
        )
        _conn.commit()
        return row["value"]


# ------------------------------------------------------------- кулдауны кейсов

def case_last_open(user_id: int, case_id: str) -> int:
    with _lock:
        row = _conn.execute(
            "SELECT last_open FROM case_opens WHERE user_id=? AND case_id=?",
            (user_id, case_id),
        ).fetchone()
        return row["last_open"] if row else 0


def case_mark_open(user_id: int, case_id: str) -> None:
    with _lock:
        _conn.execute(
            "INSERT OR REPLACE INTO case_opens(user_id, case_id, last_open) VALUES(?,?,?)",
            (user_id, case_id, int(time.time())),
        )
        _conn.commit()


# ------------------------------------------------------------- лайв-лента

_FEED_FAKE_NAMES = [
    "Александр", "Дмитрий", "Иван", "Максим", "Артём", "Данил", "Кирилл",
    "Никита", "Егор", "Владислав", "Матвей", "Роман", "Тимур", "Богдан",
    "София", "Анна", "Мария", "Полина", "Алина", "Ксения", "Виктория",
    "Дарья", "Елизавета", "Милана", "Арина", "Camila", "Alex", "Ivan",
]

# кладём сюда только «нескучные» призы — мелкие звёзды в ленте не нужны
_FEED_FAKE_POOL = [
    {"item": "50 звёзд", "emoji": "✨", "value": 50},
    {"item": "100 звёзд", "emoji": "✨", "value": 100},
    {"item": "150 звёзд", "emoji": "💫", "value": 150},
    {"item": "Jelly Bunny", "emoji": "🐰", "value": 90},
    {"item": "Berry Box", "emoji": "🍓", "value": 300},
    {"item": "Snoop Dogg", "emoji": "🐶", "value": 150},
    {"item": "Sakura Flower", "emoji": "🌸", "value": 300},
    {"item": "Kissed Frog", "emoji": "🐸", "value": 500},
    {"item": "Premium 1 месяц", "emoji": "🌟", "value": 400},
    {"item": "Premium 3 месяца", "emoji": "🌟", "value": 1000},
    {"item": "300 звёзд", "emoji": "⭐", "value": 300},
    {"item": "600 звёзд", "emoji": "✨", "value": 600},
    {"item": "Signet Ring", "emoji": "💍", "value": 1000},
    {"item": "Genie Lamp", "emoji": "🪔", "value": 1200},
    {"item": "Swiss Watch", "emoji": "⌚", "value": 1500},
]


def _fake_feed_entry() -> dict:
    return {"name": random.choice(_FEED_FAKE_NAMES), **random.choice(_FEED_FAKE_POOL)}


def get_feed(limit: int = 30) -> list[dict]:
    """Последние выигрыши из кейсов по всем игрокам.

    Пока реальных открытий кейсов меньше limit, лента дополняется
    сгенерированными записями (чтобы бегущая строка не выглядела пустой) —
    настоящие выигрыши идут первыми и постепенно вытесняют фейковые по мере
    роста активности.
    """
    with _lock:
        rows = _conn.execute(
            "SELECT h.detail, u.first_name, u.username FROM history h"
            " JOIN users u ON u.id = h.user_id"
            " WHERE h.game='case' ORDER BY h.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        d = json.loads(r["detail"])
        out.append({
            "name": r["first_name"] or r["username"] or "Игрок",
            "item": d.get("item", ""),
            "emoji": d.get("emoji", "🎁"),
            "value": d.get("value", 0),
        })
    while len(out) < limit:
        out.append(_fake_feed_entry())
    return out


# ------------------------------------------------------------ пункт обмена
# Баллы обмена — отдельная валюта от игровых звёзд (users.balance).
# Начисляются только за реально принятые подарки, тратятся только в
# магазине по фиксированной цене — в игры их поставить нельзя.

def get_exchange_balance(user_id: int) -> int:
    with _lock:
        row = _conn.execute(
            "SELECT exchange_balance FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return row["exchange_balance"] if row else 0


def credit_exchange(user_id: int, amount: int) -> int:
    with _lock:
        _conn.execute(
            "UPDATE users SET exchange_balance = exchange_balance + ? WHERE id=?",
            (amount, user_id),
        )
        _conn.commit()
        row = _conn.execute(
            "SELECT exchange_balance FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return row["exchange_balance"]


def take_exchange(user_id: int, amount: int) -> int | None:
    """Списывает баллы обмена (не ниже нуля); None, если пользователя нет."""
    with _lock:
        row = _conn.execute(
            "SELECT exchange_balance FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        new_bal = max(0, row["exchange_balance"] - amount)
        _conn.execute("UPDATE users SET exchange_balance=? WHERE id=?", (new_bal, user_id))
        _conn.commit()
        return new_bal


def try_debit_exchange(user_id: int, amount: int) -> bool:
    with _lock:
        row = _conn.execute(
            "SELECT exchange_balance FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if row is None or row["exchange_balance"] < amount:
            return False
        _conn.execute(
            "UPDATE users SET exchange_balance = exchange_balance - ? WHERE id=?",
            (amount, user_id),
        )
        _conn.commit()
    return True


def create_trade_request(user_id: int, gift_name: str, emoji: str, points: int) -> int:
    with _lock:
        cur = _conn.execute(
            "INSERT INTO trade_requests(user_id, gift_name, emoji, points, created_at)"
            " VALUES (?,?,?,?,?)",
            (user_id, gift_name, emoji, points, int(time.time())),
        )
        _conn.commit()
    return cur.lastrowid


def list_my_trades(user_id: int, limit: int = 20) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM trade_requests WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_pending_trades() -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT t.*, u.first_name, u.username FROM trade_requests t"
            " JOIN users u ON u.id = t.user_id"
            " WHERE t.status='pending' ORDER BY t.id"
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_trade(trade_id: int, status: str) -> dict | None:
    """status: 'confirmed' или 'rejected'. При confirmed баллы зачисляются."""
    with _lock:
        row = _conn.execute(
            "SELECT * FROM trade_requests WHERE id=? AND status='pending'", (trade_id,)
        ).fetchone()
        if row is None:
            return None
        _conn.execute(
            "UPDATE trade_requests SET status=?, resolved_at=? WHERE id=?",
            (status, int(time.time()), trade_id),
        )
        if status == "confirmed":
            _conn.execute(
                "UPDATE users SET exchange_balance = exchange_balance + ? WHERE id=?",
                (row["points"], row["user_id"]),
            )
        _conn.commit()
    return dict(row)


def create_shop_order(user_id: int, item_name: str, emoji: str, points: int) -> int:
    with _lock:
        cur = _conn.execute(
            "INSERT INTO shop_orders(user_id, item_name, emoji, points, created_at)"
            " VALUES (?,?,?,?,?)",
            (user_id, item_name, emoji, points, int(time.time())),
        )
        _conn.commit()
    return cur.lastrowid


def list_my_shop_orders(user_id: int, limit: int = 20) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM shop_orders WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_pending_shop_orders() -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT o.*, u.first_name, u.username FROM shop_orders o"
            " JOIN users u ON u.id = o.user_id"
            " WHERE o.status='pending' ORDER BY o.id"
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_shop_order(order_id: int) -> dict | None:
    """Отмечает заказ выполненным (админ вручную выдал приз)."""
    with _lock:
        row = _conn.execute(
            "SELECT * FROM shop_orders WHERE id=? AND status='pending'", (order_id,)
        ).fetchone()
        if row is None:
            return None
        _conn.execute(
            "UPDATE shop_orders SET status='fulfilled', resolved_at=? WHERE id=?",
            (int(time.time()), order_id),
        )
        _conn.commit()
    return dict(row)
