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
    "free": {
        "title": "Бесплатный",
        "emoji": "🎉",
        "glow": "#4cd964",
        "price": 0,
        "cooldown": 4 * 3600,  # раз в 4 часа
        "items": [
            {"name": "Клевер", "emoji": "🍀", "value": 5, "weight": 30},
            {"name": "Конфета", "emoji": "🍬", "value": 10, "weight": 25},
            {"name": "Печенье", "emoji": "🍪", "value": 20, "weight": 20},
            {"name": "Роза", "emoji": "🌹", "value": 40, "weight": 15},
            {"name": "Сердце", "emoji": "❤️", "value": 60, "weight": 8},
            {"name": "Ракета", "emoji": "🚀", "value": 150, "weight": 2},
        ],
    },
    "daily": {
        "title": "Ежедневный",
        "emoji": "📅",
        "glow": "#ffd24d",
        "price": 0,
        "cooldown": 24 * 3600,
        "items": [
            {"name": "Мишка", "emoji": "🧸", "value": 50, "weight": 30},
            {"name": "Торт", "emoji": "🎂", "value": 100, "weight": 25},
            {"name": "Подарок", "emoji": "🎁", "value": 150, "weight": 20},
            {"name": "Ракета", "emoji": "🚀", "value": 300, "weight": 15},
            {"name": "Алмаз", "emoji": "💎", "value": 600, "weight": 8},
            {"name": "Корона", "emoji": "👑", "value": 1500, "weight": 2},
        ],
    },
    "stardust": {
        "title": "Звёздная пыль",
        "emoji": "✨",
        "glow": "#8ab6ff",
        "price": 150,
        "items": [
            {"name": "Звёздочка", "emoji": "🌟", "value": 30, "weight": 30},
            {"name": "Леденец", "emoji": "🍭", "value": 60, "weight": 25},
            {"name": "Шарик", "emoji": "🎈", "value": 100, "weight": 18},
            {"name": "Капкейк", "emoji": "🧁", "value": 180, "weight": 14},
            {"name": "Тарелка", "emoji": "🛸", "value": 400, "weight": 10},
            {"name": "Комета", "emoji": "💫", "value": 1200, "weight": 3},
        ],
    },
    "duck": {
        "title": "Утиный бунт",
        "emoji": "🦆",
        "glow": "#ffe066",
        "price": 300,
        "items": [
            {"name": "Носки", "emoji": "🧦", "value": 50, "weight": 32},
            {"name": "Утка", "emoji": "🦆", "value": 150, "weight": 26},
            {"name": "Сочок", "emoji": "🧃", "value": 250, "weight": 18},
            {"name": "Диско-шар", "emoji": "🪩", "value": 500, "weight": 14},
            {"name": "Наушники", "emoji": "🎧", "value": 900, "weight": 8},
            {"name": "Кроссы", "emoji": "👟", "value": 2000, "weight": 2},
        ],
    },
    "robo": {
        "title": "Робо-бокс",
        "emoji": "🤖",
        "glow": "#7cf5ff",
        "price": 500,
        "items": [
            {"name": "Шестерёнка", "emoji": "⚙️", "value": 100, "weight": 33},
            {"name": "Батарейка", "emoji": "🔋", "value": 200, "weight": 26},
            {"name": "Джойстик", "emoji": "🕹", "value": 400, "weight": 18},
            {"name": "Робот", "emoji": "🤖", "value": 800, "weight": 13},
            {"name": "Дрон", "emoji": "🚁", "value": 1500, "weight": 8},
            {"name": "Спутник", "emoji": "🛰", "value": 3000, "weight": 2},
        ],
    },
    "moon": {
        "title": "Лунный лут",
        "emoji": "🌙",
        "glow": "#b39dff",
        "price": 1000,
        "items": [
            {"name": "Новолуние", "emoji": "🌑", "value": 200, "weight": 33},
            {"name": "Полумесяц", "emoji": "🌗", "value": 400, "weight": 25},
            {"name": "Полнолуние", "emoji": "🌕", "value": 800, "weight": 18},
            {"name": "Ракета", "emoji": "🚀", "value": 1500, "weight": 14},
            {"name": "Космонавт", "emoji": "👨‍🚀", "value": 3000, "weight": 8},
            {"name": "Галактика", "emoji": "🌌", "value": 6000, "weight": 2},
        ],
    },
    "plasma": {
        "title": "Плазма",
        "emoji": "🔮",
        "glow": "#c86bff",
        "price": 2000,
        "items": [
            {"name": "Кристалл", "emoji": "💠", "value": 400, "weight": 34},
            {"name": "Молния", "emoji": "⚡", "value": 800, "weight": 25},
            {"name": "Сфера", "emoji": "🔮", "value": 1600, "weight": 18},
            {"name": "Оберег", "emoji": "🧿", "value": 3000, "weight": 13},
            {"name": "Комета", "emoji": "☄️", "value": 6000, "weight": 7},
            {"name": "Сверхновая", "emoji": "🌠", "value": 15000, "weight": 3},
        ],
    },
    "blackhole": {
        "title": "Чёрная дыра",
        "emoji": "🕳",
        "glow": "#ff6b6b",
        "price": 5000,
        "items": [
            {"name": "Туман", "emoji": "🌫", "value": 1000, "weight": 34},
            {"name": "Вихрь", "emoji": "🌪", "value": 2000, "weight": 25},
            {"name": "Дыра", "emoji": "🕳", "value": 4000, "weight": 18},
            {"name": "Планета", "emoji": "🪐", "value": 8000, "weight": 13},
            {"name": "Портал", "emoji": "🌀", "value": 15000, "weight": 8},
            {"name": "Большой взрыв", "emoji": "💥", "value": 40000, "weight": 2},
        ],
    },
}
# RTP платных кейсов ~88–95%


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
