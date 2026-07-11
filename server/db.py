"""SQLite-хранилище: пользователи, сиды честности, активные игры, история."""
import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get(
    "DB_PATH", os.path.join(os.path.dirname(__file__), "..", "playbot.db")
)

START_BALANCE = 5000

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
"""
with _lock:
    _conn.executescript(_SCHEMA)
    try:  # миграция старых баз без photo_url
        _conn.execute("ALTER TABLE users ADD COLUMN photo_url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    _conn.commit()


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
    with _lock:
        _conn.execute(
            "INSERT INTO history(user_id, game, bet, payout, detail, created_at) VALUES(?,?,?,?,?,?)",
            (user_id, game, bet, payout, json.dumps(detail), int(time.time())),
        )
        _conn.commit()


def crash_history(user_id: int, limit: int = 10) -> list[float]:
    """Точки взрыва последних раундов краша пользователя (новые первыми)."""
    with _lock:
        rows = _conn.execute(
            "SELECT detail FROM history WHERE user_id=? AND game='crash'"
            " ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [json.loads(r["detail"])["point"] for r in rows]


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

def get_feed(limit: int = 10) -> list[dict]:
    """Последние выигрыши из кейсов по всем игрокам."""
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
    return out
