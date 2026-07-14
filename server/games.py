"""Математика игр: краш, слоты, мины, кейсы.

Все исходы детерминированно выводятся из сидов (см. fair.py).
HOUSE_EDGE — преимущество площадки, честно указано в интерфейсе.
"""
import math

HOUSE_EDGE = 0.04          # краш и мины: возврат игроку 96%
CRASH_GROWTH = 0.12        # множитель краша: m(t) = e^(0.12 * t_сек)

MIN_BET = 1
MAX_BET = 10_000

# ---------------------------------------------------------------- краш

CRASH_MAX_POINT = 20.0  # потолок множителя (защита казны от хвоста распределения)


def crash_point(r: float) -> float:
    """Точка взрыва: P(взрыв >= x) = (1 - edge) / x, с потолком."""
    point = (1 - HOUSE_EDGE) / (1 - r)
    return min(CRASH_MAX_POINT, max(1.0, math.floor(point * 100) / 100))


def crash_multiplier_at(elapsed_sec: float) -> float:
    return math.floor(math.exp(CRASH_GROWTH * elapsed_sec) * 100) / 100


def crash_time_of(point: float) -> float:
    """Через сколько секунд после старта множитель достигнет точки взрыва."""
    return math.log(point) / CRASH_GROWTH

# ---------------------------------------------------------------- слоты

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣"]
SLOT_WEIGHTS = [30, 25, 18, 12, 10, 5]
# выплаты за три одинаковых (множитель ставки)
SLOT_TRIPLE_PAY = {"🍒": 5, "🍋": 7, "🔔": 12, "⭐": 15, "💎": 20, "7️⃣": 30}
SLOT_TWO_CHERRIES_PAY = 3  # ровно две вишни
# итоговый RTP ~93%, максимальный выигрыш x30


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


MINES_MAX_MULT = 30.0  # потолок множителя в минах


def mines_multiplier(mines_count: int, revealed: int) -> float:
    """(1-edge) / P(открыть revealed безопасных ячеек подряд), с потолком."""
    if revealed == 0:
        return 1.0
    fair = math.comb(MINES_GRID, revealed) / math.comb(MINES_GRID - mines_count, revealed)
    return min(MINES_MAX_MULT, math.floor((1 - HOUSE_EDGE) * fair * 100) / 100)

# ---------------------------------------------------------------- кейсы

CASES = {
    # value везде в звёздах; item с "stars": True падает сразу на баланс,
    # подарки (реальные подарки Telegram) — в инвентарь.
    # Цены подарков — примерные рыночные (floor на маркетплейсах), правятся здесь.
    "free": {
        "title": "Бесплатный",
        "emoji": "🎉",
        "glow": "#4cd964",
        "price": 0,
        "cooldown": 4 * 3600,  # раз в 4 часа
        "items": [
            {"name": "1 звезда", "emoji": "⭐", "value": 1, "weight": 40, "stars": True},
            {"name": "2 звезды", "emoji": "⭐", "value": 2, "weight": 30, "stars": True},
            {"name": "3 звезды", "emoji": "⭐", "value": 3, "weight": 15, "stars": True},
            {"name": "5 звёзд", "emoji": "✨", "value": 5, "weight": 10, "stars": True},
            {"name": "10 звёзд", "emoji": "✨", "value": 10, "weight": 4, "stars": True},
            {"name": "25 звёзд", "emoji": "💫", "value": 25, "weight": 1, "stars": True},
        ],
    },
    "daily": {
        "title": "Ежедневный",
        "emoji": "📅",
        "glow": "#ffd24d",
        "price": 0,
        "cooldown": 24 * 3600,
        "items": [
            {"name": "5 звёзд", "emoji": "⭐", "value": 5, "weight": 35, "stars": True},
            {"name": "10 звёзд", "emoji": "⭐", "value": 10, "weight": 30, "stars": True},
            {"name": "15 звёзд", "emoji": "✨", "value": 15, "weight": 15, "stars": True},
            {"name": "25 звёзд", "emoji": "✨", "value": 25, "weight": 12, "stars": True},
            {"name": "50 звёзд", "emoji": "💫", "value": 50, "weight": 6, "stars": True},
            {"name": "100 звёзд", "emoji": "💫", "value": 100, "weight": 2, "stars": True},
        ],
    },
    "light": {
        "title": "Лайт",
        "emoji": "🐰",  # топ-подарок кейса — Jelly Bunny
        "glow": "#8ab6ff",
        "price": 25,
        "items": [
            {"name": "10 звёзд", "emoji": "⭐", "value": 10, "weight": 45, "stars": True},
            {"name": "15 звёзд", "emoji": "⭐", "value": 15, "weight": 26, "stars": True},
            {"name": "25 звёзд", "emoji": "✨", "value": 25, "weight": 14, "stars": True},
            {"name": "Lol Pop", "emoji": "🍭", "value": 40, "weight": 9},
            {"name": "B-Day Candle", "emoji": "🕯", "value": 55, "weight": 3},
            {"name": "Jelly Bunny", "emoji": "🐰", "value": 90, "weight": 3},
        ],
    },
    "sweet": {
        "title": "Сладкий",
        "emoji": "🍓",  # топ — Berry Box
        "glow": "#ff8ab6",
        "price": 60,
        "items": [
            {"name": "25 звёзд", "emoji": "⭐", "value": 25, "weight": 40, "stars": True},
            {"name": "50 звёзд", "emoji": "✨", "value": 50, "weight": 46, "stars": True},
            {"name": "Candy Cane", "emoji": "🍬", "value": 45, "weight": 5},
            {"name": "Homemade Cake", "emoji": "🍰", "value": 75, "weight": 4},
            {"name": "Spiced Wine", "emoji": "🍷", "value": 110, "weight": 2},
            {"name": "Snow Globe", "emoji": "❄️", "value": 190, "weight": 1},
            {"name": "Berry Box", "emoji": "🍓", "value": 300, "weight": 2},
        ],
    },
    "snoop": {
        "title": "Снуп Дог",
        "emoji": "🤟",  # топ — Westside Sign
        "glow": "#ffe066",
        "price": 150,
        "items": [
            {"name": "60 звёзд", "emoji": "⭐", "value": 60, "weight": 40, "stars": True},
            {"name": "100 звёзд", "emoji": "✨", "value": 100, "weight": 30, "stars": True},
            {"name": "150 звёзд", "emoji": "💫", "value": 150, "weight": 19, "stars": True},
            {"name": "Snoop Dogg", "emoji": "🐶", "value": 150, "weight": 5},
            {"name": "Snoop Cigar", "emoji": "🚬", "value": 250, "weight": 2},
            {"name": "Low Rider", "emoji": "🚗", "value": 400, "weight": 1},
            {"name": "Westside Sign", "emoji": "🤟", "value": 700, "weight": 3},
        ],
    },
    "frog": {
        "title": "Поцелуй фрога",
        "emoji": "⌚",  # топ — Swiss Watch
        "glow": "#7cf5a0",
        "price": 300,
        "items": [
            {"name": "100 звёзд", "emoji": "⭐", "value": 100, "weight": 36, "stars": True},
            {"name": "200 звёзд", "emoji": "✨", "value": 200, "weight": 35, "stars": True},
            {"name": "350 звёзд", "emoji": "💫", "value": 350, "weight": 22, "stars": True},
            {"name": "Sakura Flower", "emoji": "🌸", "value": 300, "weight": 3},
            {"name": "Kissed Frog", "emoji": "🐸", "value": 500, "weight": 2},
            {"name": "Electric Skull", "emoji": "💀", "value": 700, "weight": 1},
            {"name": "Genie Lamp", "emoji": "🪔", "value": 1200, "weight": 1},
            {"name": "Swiss Watch", "emoji": "⌚", "value": 1500, "weight": 1},
        ],
    },
    "cat": {
        "title": "Кот в шоке",
        "emoji": "💎",  # топ — Ion Gem
        "glow": "#c86bff",
        "price": 800,
        "items": [
            {"name": "300 звёзд", "emoji": "⭐", "value": 300, "weight": 38, "stars": True},
            {"name": "600 звёзд", "emoji": "✨", "value": 600, "weight": 34, "stars": True},
            {"name": "1000 звёзд", "emoji": "💫", "value": 1000, "weight": 22, "stars": True},
            {"name": "Signet Ring", "emoji": "💍", "value": 1000, "weight": 2},
            {"name": "Neko Helmet", "emoji": "🐱", "value": 1300, "weight": 1},
            {"name": "Scared Cat", "emoji": "🙀", "value": 2000, "weight": 1},
            {"name": "Loot Bag", "emoji": "💰", "value": 2500, "weight": 1},
            {"name": "Ion Gem", "emoji": "💎", "value": 3000, "weight": 1},
        ],
    },
    "legend": {
        "title": "Легендарный",
        "emoji": "💝",  # топ — Heart Locket
        "glow": "#ff6b6b",
        "price": 3000,
        "items": [
            {"name": "1200 звёзд", "emoji": "💫", "value": 1200, "weight": 80, "stars": True},
            {"name": "2200 звёзд", "emoji": "💫", "value": 2200, "weight": 70, "stars": True},
            {"name": "4000 звёзд", "emoji": "🌟", "value": 4000, "weight": 45, "stars": True},
            {"name": "Astral Shard", "emoji": "🔷", "value": 4000, "weight": 1},
            {"name": "Mini Oscar", "emoji": "🏆", "value": 5000, "weight": 1},
            {"name": "Precious Peach", "emoji": "🍑", "value": 7000, "weight": 1},
            {"name": "Durov's Cap", "emoji": "🧢", "value": 20000, "weight": 1},
            {"name": "Heart Locket", "emoji": "💝", "value": 30000, "weight": 1},
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
