"""Пункт обмена: приём реальных подарков Telegram за баллы (не звёзды).

Баллы обмена — отдельная валюта от игровых звёзд. Их нельзя поставить в
краш/слоты/кейсы — только потратить в магазине по фиксированной цене
(без элемента случайности). Так вход в игры остаётся полностью бесплатным,
а обмен подарками не превращается в скрытую ставку.

Курс выкупа — ~65% от справочной стоимости подарка (той же, что используется
в кейсах), запас идёт в вашу маржу при перепродаже на реальном рынке
(Portals/Fragment/Tonnel) или на выдачу как приз в кейсах.
"""

# name -> {emoji, points}  (сколько баллов даём за подарок)
BUYBACK_CATALOG = {
    "Lol Pop": {"emoji": "🍭", "points": 25},
    "Candy Cane": {"emoji": "🍬", "points": 30},
    "B-Day Candle": {"emoji": "🕯", "points": 35},
    "Homemade Cake": {"emoji": "🍰", "points": 50},
    "Jelly Bunny": {"emoji": "🐰", "points": 60},
    "Spiced Wine": {"emoji": "🍷", "points": 70},
    "Snoop Dogg": {"emoji": "🐶", "points": 100},
    "Snow Globe": {"emoji": "❄️", "points": 125},
    "Snoop Cigar": {"emoji": "🚬", "points": 160},
    "Berry Box": {"emoji": "🍓", "points": 195},
    "Sakura Flower": {"emoji": "🌸", "points": 195},
    "Low Rider": {"emoji": "🚗", "points": 260},
    "Kissed Frog": {"emoji": "🐸", "points": 325},
    "Westside Sign": {"emoji": "🤟", "points": 455},
    "Electric Skull": {"emoji": "💀", "points": 455},
    "Signet Ring": {"emoji": "💍", "points": 650},
    "Genie Lamp": {"emoji": "🪔", "points": 780},
    "Neko Helmet": {"emoji": "🐱", "points": 845},
    "Swiss Watch": {"emoji": "⌚", "points": 975},
    "Scared Cat": {"emoji": "🙀", "points": 1300},
    "Loot Bag": {"emoji": "💰", "points": 1625},
    "Ion Gem": {"emoji": "💎", "points": 1950},
    "Astral Shard": {"emoji": "🔷", "points": 2600},
    "Mini Oscar": {"emoji": "🏆", "points": 3250},
    "Precious Peach": {"emoji": "🍑", "points": 4550},
    "Durov's Cap": {"emoji": "🧢", "points": 13000},
    "Heart Locket": {"emoji": "💝", "points": 19500},
}

# фиксированные покупки за баллы — без всякой случайности
SHOP_CATALOG = {
    "100 звёзд Telegram": {"emoji": "⭐", "points": 150},
    "300 звёзд Telegram": {"emoji": "✨", "points": 430},
    "500 звёзд Telegram": {"emoji": "💫", "points": 700},
    "Telegram Premium 1 месяц": {"emoji": "🌟", "points": 600},
    "Telegram Premium 3 месяца": {"emoji": "🌟", "points": 1550},
    "Telegram Premium 12 месяцев": {"emoji": "🌟", "points": 4900},
}
