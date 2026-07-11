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
    balance INTEGER NOT NULL,
    created_at INTEGER NOT NULL
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
    _conn.commit()


def get_or_create_user(user_id: int, username: str, first_name: str) -> dict:
    with _lock:
        row = _conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            _conn.execute(
                "INSERT INTO users(id, username, first_name, balance, created_at) VALUES(?,?,?,?,?)",
                (user_id, username, first_name, START_BALANCE, int(time.time())),
            )
            _conn.commit()
            row = _conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row)


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
