"""PlayBot API: краш, слоты, мины, кейсы + provably fair.

Запуск:  uvicorn server.main:app --host 0.0.0.0 --port 8080
"""
import math
import os
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, fair, games
from .auth import validate_init_data

app = FastAPI(title="PlayBot")

WEBAPP_DIR = os.path.join(os.path.dirname(__file__), "..", "webapp")


# ------------------------------------------------------------------ auth

def current_user(x_init_data: str = Header(default="")) -> dict:
    tg_user = validate_init_data(x_init_data)
    if tg_user is None:
        raise HTTPException(401, "Невалидные данные Telegram")
    return db.get_or_create_user(
        tg_user["id"], tg_user.get("username", ""), tg_user.get("first_name", "")
    )


def _seeds(user_id: int) -> dict:
    return db.get_seeds(user_id, fair.new_server_seed, fair.new_client_seed)


def _roll(user_id: int, count: int) -> tuple[list[float], int]:
    """Числа для очередной игры + использованный nonce (nonce инкрементируется)."""
    seeds = _seeds(user_id)
    rolls = fair.roll_floats(seeds["server_seed"], seeds["client_seed"], seeds["nonce"], count)
    db.bump_nonce(user_id)
    return rolls, seeds["nonce"]


def _check_bet(bet: int, balance_debited: bool = False) -> None:
    if not isinstance(bet, int) or bet < games.MIN_BET or bet > games.MAX_BET:
        raise HTTPException(400, f"Ставка от {games.MIN_BET} до {games.MAX_BET}")


# ------------------------------------------------------------------ общее

class BetBody(BaseModel):
    bet: int


@app.post("/api/init")
def api_init(user: dict = Depends(current_user)):
    seeds = _seeds(user["id"])
    return {
        "user": {"id": user["id"], "name": user["first_name"] or user["username"]},
        "balance": db.get_balance(user["id"]),
        "fair": {
            "server_seed_hash": fair.seed_hash(seeds["server_seed"]),
            "client_seed": seeds["client_seed"],
            "nonce": seeds["nonce"],
        },
        "config": {
            "min_bet": games.MIN_BET,
            "max_bet": games.MAX_BET,
            "house_edge": games.HOUSE_EDGE,
            "crash_growth": games.CRASH_GROWTH,
        },
    }


@app.post("/api/fair/rotate")
def api_fair_rotate(user: dict = Depends(current_user)):
    """Раскрывает текущий server seed и выдаёт новый."""
    if db.get_active_game(user["id"], "crash") or db.get_active_game(user["id"], "mines"):
        raise HTTPException(400, "Завершите активные игры перед сменой сида")
    old = db.rotate_seed(user["id"], fair.new_server_seed(), fair.new_client_seed())
    seeds = _seeds(user["id"])
    return {
        "revealed": {
            "server_seed": old["server_seed"],
            "server_seed_hash": fair.seed_hash(old["server_seed"]),
            "client_seed": old["client_seed"],
            "last_nonce": old["nonce"],
        },
        "fair": {
            "server_seed_hash": fair.seed_hash(seeds["server_seed"]),
            "client_seed": seeds["client_seed"],
            "nonce": seeds["nonce"],
        },
    }


# ------------------------------------------------------------------ краш

@app.post("/api/crash/start")
def api_crash_start(body: BetBody, user: dict = Depends(current_user)):
    _check_bet(body.bet)
    if db.get_active_game(user["id"], "crash"):
        raise HTTPException(400, "Раунд уже идёт")
    if not db.try_debit(user["id"], body.bet):
        raise HTTPException(400, "Недостаточно монет")
    rolls, nonce = _roll(user["id"], 1)
    point = games.crash_point(rolls[0])
    state = {"bet": body.bet, "point": point, "start": time.time(), "nonce": nonce}
    db.set_active_game(user["id"], "crash", state)
    return {"status": "active", "balance": db.get_balance(user["id"])}


def _crash_settle_if_crashed(user_id: int, state: dict) -> dict | None:
    """Если время взрыва прошло — фиксирует проигрыш и возвращает итог."""
    elapsed = time.time() - state["start"]
    if elapsed >= games.crash_time_of(state["point"]):
        db.clear_active_game(user_id, "crash")
        db.add_history(user_id, "crash", state["bet"], 0,
                       {"point": state["point"], "nonce": state["nonce"]})
        return {
            "status": "crashed",
            "crash_point": state["point"],
            "nonce": state["nonce"],
            "balance": db.get_balance(user_id),
        }
    return None


@app.get("/api/crash/state")
def api_crash_state(user: dict = Depends(current_user)):
    state = db.get_active_game(user["id"], "crash")
    if state is None:
        return {"status": "none"}
    crashed = _crash_settle_if_crashed(user["id"], state)
    if crashed:
        return crashed
    return {
        "status": "active",
        "bet": state["bet"],
        "elapsed": time.time() - state["start"],
    }


@app.post("/api/crash/cashout")
def api_crash_cashout(user: dict = Depends(current_user)):
    state = db.get_active_game(user["id"], "crash")
    if state is None:
        raise HTTPException(400, "Нет активного раунда")
    crashed = _crash_settle_if_crashed(user["id"], state)
    if crashed:
        return crashed
    mult = games.crash_multiplier_at(time.time() - state["start"])
    payout = math.floor(state["bet"] * mult)
    db.clear_active_game(user["id"], "crash")
    balance = db.credit(user["id"], payout)
    db.add_history(user["id"], "crash", state["bet"], payout,
                   {"point": state["point"], "cashout": mult, "nonce": state["nonce"]})
    return {
        "status": "won",
        "multiplier": mult,
        "payout": payout,
        "crash_point": state["point"],
        "nonce": state["nonce"],
        "balance": balance,
    }


# ------------------------------------------------------------------ слоты

@app.post("/api/slots/spin")
def api_slots_spin(body: BetBody, user: dict = Depends(current_user)):
    _check_bet(body.bet)
    if not db.try_debit(user["id"], body.bet):
        raise HTTPException(400, "Недостаточно монет")
    rolls, nonce = _roll(user["id"], 3)
    reels, mult_x100 = games.slots_spin(rolls)
    payout = body.bet * mult_x100 // 100
    balance = db.credit(user["id"], payout) if payout else db.get_balance(user["id"])
    db.add_history(user["id"], "slots", body.bet, payout,
                   {"reels": reels, "nonce": nonce})
    return {
        "reels": reels,
        "payout": payout,
        "multiplier": mult_x100 / 100,
        "nonce": nonce,
        "balance": balance,
    }


# ------------------------------------------------------------------ мины

class MinesStartBody(BaseModel):
    bet: int
    mines: int


class MinesRevealBody(BaseModel):
    cell: int


@app.post("/api/mines/start")
def api_mines_start(body: MinesStartBody, user: dict = Depends(current_user)):
    _check_bet(body.bet)
    if body.mines < 1 or body.mines > 24:
        raise HTTPException(400, "Мин может быть от 1 до 24")
    if db.get_active_game(user["id"], "mines"):
        raise HTTPException(400, "Игра уже идёт")
    if not db.try_debit(user["id"], body.bet):
        raise HTTPException(400, "Недостаточно монет")
    rolls, nonce = _roll(user["id"], games.MINES_GRID - 1)
    layout = games.mines_layout(rolls, body.mines)
    state = {"bet": body.bet, "mines": body.mines, "layout": layout,
             "revealed": [], "nonce": nonce}
    db.set_active_game(user["id"], "mines", state)
    return {
        "status": "active",
        "balance": db.get_balance(user["id"]),
        "next_multiplier": games.mines_multiplier(body.mines, 1),
    }


@app.get("/api/mines/state")
def api_mines_state(user: dict = Depends(current_user)):
    state = db.get_active_game(user["id"], "mines")
    if state is None:
        return {"status": "none"}
    k = len(state["revealed"])
    return {
        "status": "active",
        "bet": state["bet"],
        "mines": state["mines"],
        "revealed": state["revealed"],
        "multiplier": games.mines_multiplier(state["mines"], k),
        "next_multiplier": games.mines_multiplier(state["mines"], k + 1),
    }


@app.post("/api/mines/reveal")
def api_mines_reveal(body: MinesRevealBody, user: dict = Depends(current_user)):
    state = db.get_active_game(user["id"], "mines")
    if state is None:
        raise HTTPException(400, "Нет активной игры")
    cell = body.cell
    if cell < 0 or cell >= games.MINES_GRID or cell in state["revealed"]:
        raise HTTPException(400, "Неверная ячейка")
    if cell in state["layout"]:
        db.clear_active_game(user["id"], "mines")
        db.add_history(user["id"], "mines", state["bet"], 0,
                       {"mines": state["mines"], "layout": state["layout"],
                        "nonce": state["nonce"]})
        return {
            "status": "boom",
            "layout": state["layout"],
            "nonce": state["nonce"],
            "balance": db.get_balance(user["id"]),
        }
    state["revealed"].append(cell)
    k = len(state["revealed"])
    safe_total = games.MINES_GRID - state["mines"]
    mult = games.mines_multiplier(state["mines"], k)
    if k == safe_total:  # открыты все безопасные — автовыплата
        payout = math.floor(state["bet"] * mult)
        db.clear_active_game(user["id"], "mines")
        balance = db.credit(user["id"], payout)
        db.add_history(user["id"], "mines", state["bet"], payout,
                       {"mines": state["mines"], "layout": state["layout"],
                        "revealed": k, "nonce": state["nonce"]})
        return {"status": "won", "multiplier": mult, "payout": payout,
                "layout": state["layout"], "nonce": state["nonce"], "balance": balance}
    db.set_active_game(user["id"], "mines", state)
    return {
        "status": "safe",
        "revealed": state["revealed"],
        "multiplier": mult,
        "next_multiplier": games.mines_multiplier(state["mines"], k + 1),
        "cashout_value": math.floor(state["bet"] * mult),
    }


@app.post("/api/mines/cashout")
def api_mines_cashout(user: dict = Depends(current_user)):
    state = db.get_active_game(user["id"], "mines")
    if state is None:
        raise HTTPException(400, "Нет активной игры")
    k = len(state["revealed"])
    if k == 0:
        raise HTTPException(400, "Откройте хотя бы одну ячейку")
    mult = games.mines_multiplier(state["mines"], k)
    payout = math.floor(state["bet"] * mult)
    db.clear_active_game(user["id"], "mines")
    balance = db.credit(user["id"], payout)
    db.add_history(user["id"], "mines", state["bet"], payout,
                   {"mines": state["mines"], "layout": state["layout"],
                    "revealed": k, "nonce": state["nonce"]})
    return {"status": "won", "multiplier": mult, "payout": payout,
            "layout": state["layout"], "nonce": state["nonce"], "balance": balance}


# ------------------------------------------------------------------ кейсы

class CaseOpenBody(BaseModel):
    case_id: str


@app.get("/api/cases")
def api_cases():
    return {
        "cases": [
            {"id": cid, "title": c["title"], "emoji": c["emoji"],
             "price": c["price"], "items": c["items"]}
            for cid, c in games.CASES.items()
        ]
    }


@app.post("/api/cases/open")
def api_cases_open(body: CaseOpenBody, user: dict = Depends(current_user)):
    case = games.CASES.get(body.case_id)
    if case is None:
        raise HTTPException(400, "Нет такого кейса")
    if not db.try_debit(user["id"], case["price"]):
        raise HTTPException(400, "Недостаточно монет")
    rolls, nonce = _roll(user["id"], 1)
    item = games.case_open(body.case_id, rolls[0])
    balance = db.credit(user["id"], item["value"])
    db.add_history(user["id"], "case", case["price"], item["value"],
                   {"case": body.case_id, "item": item["name"], "nonce": nonce})
    return {"item": item, "nonce": nonce, "balance": balance}


# ------------------------------------------------------------------ статика

@app.get("/")
def index():
    return FileResponse(os.path.join(WEBAPP_DIR, "index.html"))


app.mount("/", StaticFiles(directory=WEBAPP_DIR), name="webapp")
