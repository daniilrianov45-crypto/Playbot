"""Математика игр: краш, слоты, мины, кейсы.

Все исходы детерминированно выводятся из сидов (см. fair.py).
HOUSE_EDGE — преимущество площадки, честно указано в интерфейсе.
"""
import math

HOUSE_EDGE = 0.04          # краш и мины: возврат игроку 96%
CRASH_GROWTH = 0.12        # множитель краша: m(t) = e^(0.12 * t_сек)

MIN_BET = 10
MAX_BET = 100_000

# ---------------------------------------------------------------- краш

def crash_point(r: float) -> float:
    """Точка взрыва: P(взрыв >= x) = (1 - edge) / x."""
    point = (1 - HOUSE_EDGE) / (1 - r)
    return max(1.0, math.floor(point * 100) / 100)


def crash_multiplier_at(elapsed_sec: float) -> float:
    return math.floor(math.exp(CRASH_GROWTH * elapsed_sec) * 100) / 100


def crash_time_of(point: float) -> float:
    """Через сколько секунд после старта множитель достигнет точки взрыва."""
    return math.log(point) / CRASH_GROWTH

# ---------------------------------------------------------------- слоты

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 18, 12, 10, 5]
# выплаты за три одинаковых (множитель ставки)
SLOT_TRIPLE_PAY = {"🍒": 5, "🍋": 8, "🔔": 15, "⭐": 40, "💎": 80, "7️⃣": 500}
SLOT_TWO_CHERRIES_PAY = 2  # ровно две вишни
# итоговый RTP ~93.7%


def _weighted_pick(r: float, symbols: list, weights: list):
    total = sum(weights)
    point = r * total
    acc = 0
    for sym, w in zip(symbols, weights):
        acc += w
        if point < acc:
            return sym
    return symbols[-1]


def slots_spin(rolls: list[float]) -> tuple[list[str], int]:
    """Возвращает (барабаны, множитель_выплаты_x100).

    Множитель в сотых, чтобы выплата 2x считалась в целых числах.
    """
    reels = [_weighted_pick(r, SLOT_SYMBOLS, SLOT_WEIGHTS) for r in rolls[:3]]
    if reels[0] == reels[1] == reels[2]:
        return reels, SLOT_TRIPLE_PAY[reels[0]] * 100
    if reels.count("🍒") == 2:
        return reels, SLOT_TWO_CHERRIES_PAY * 100
    return reels, 0

# ---------------------------------------------------------------- мины

MINES_GRID = 25  # 5x5


def mines_layout(rolls: list[float], mines_count: int) -> list[int]:
    """Fisher–Yates на 25 ячейках, первые mines_count — мины."""
    cells = list(range(MINES_GRID))
    for i in range(MINES_GRID - 1, 0, -1):
        j = int(rolls[MINES_GRID - 1 - i] * (i + 1))
        cells[i], cells[j] = cells[j], cells[i]
    return sorted(cells[:mines_count])


def mines_multiplier(mines_count: int, revealed: int) -> float:
    """(1-edge) / P(открыть revealed безопасных ячеек подряд)."""
    if revealed == 0:
        return 1.0
    fair = math.comb(MINES_GRID, revealed) / math.comb(MINES_GRID - mines_count, revealed)
    return math.floor((1 - HOUSE_EDGE) * fair * 100) / 100

# ---------------------------------------------------------------- кейсы

CASES = {
    "bronze": {
        "title": "Бронзовый",
        "emoji": "📦",
        "price": 100,
        "items": [
            {"name": "Мишка", "emoji": "🧸", "value": 25, "weight": 35},
            {"name": "Роза", "emoji": "🌹", "value": 50, "weight": 25},
            {"name": "Сердце", "emoji": "❤️", "value": 100, "weight": 20},
            {"name": "Торт", "emoji": "🎂", "value": 150, "weight": 12},
            {"name": "Ракета", "emoji": "🚀", "value": 300, "weight": 6},
            {"name": "Кольцо", "emoji": "💍", "value": 500, "weight": 2},
        ],
    },
    "silver": {
        "title": "Серебряный",
        "emoji": "🎁",
        "price": 500,
        "items": [
            {"name": "Мишка", "emoji": "🧸", "value": 100, "weight": 35},
            {"name": "Сердце", "emoji": "❤️", "value": 250, "weight": 28},
            {"name": "Подарок", "emoji": "🎁", "value": 500, "weight": 20},
            {"name": "Ракета", "emoji": "🚀", "value": 1000, "weight": 12},
            {"name": "Алмаз", "emoji": "💎", "value": 2000, "weight": 4},
            {"name": "Корона", "emoji": "👑", "value": 5000, "weight": 1},
        ],
    },
    "gold": {
        "title": "Золотой",
        "emoji": "🏆",
        "price": 2000,
        "items": [
            {"name": "Подарок", "emoji": "🎁", "value": 400, "weight": 34},
            {"name": "Ракета", "emoji": "🚀", "value": 800, "weight": 28},
            {"name": "Алмаз", "emoji": "💎", "value": 2000, "weight": 20},
            {"name": "Спорткар", "emoji": "🏎", "value": 4000, "weight": 12},
            {"name": "Корона", "emoji": "👑", "value": 8000, "weight": 5},
            {"name": "Звезда", "emoji": "🌟", "value": 20000, "weight": 1},
        ],
    },
}
# RTP кейсов: bronze ~87%, silver ~91%, gold ~92%


def case_open(case_id: str, r: float) -> dict:
    case = CASES[case_id]
    items = case["items"]
    weights = [it["weight"] for it in items]
    total = sum(weights)
    point = r * total
    acc = 0
    for it in items:
        acc += it["weight"]
        if point < acc:
            return it
    return items[-1]
