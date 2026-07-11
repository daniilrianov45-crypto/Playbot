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
    for migration in (  # миграции старых баз
        "ALTER TABLE users ADD COLUMN photo_url TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN referrer_id INTEGER",
        "ALTER TABLE users ADD COLUMN ref_earned INTEGER NOT NULL DEFAULT 0",
    ):
        try:
            _conn.execute(migration)
        except sqlite3.OperationalError:
            pass
    _conn.commit()

# уровни партнёрки: (минимум приглашённых, доля от проигрышей друзей в %)
REF_LEVELS = [(20, 20), (5, 15), (0, 10)]
REF_BONUS_FRIEND = 1000   # бонус приглашённому
REF_BONUS_INVITER = 500   # бонус пригласившему за каждого друга


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
