"""Пункт обмена: приём реальных подарков Telegram за баллы (не звёзды).

Баллы обмена — отдельная валюта от игровых звёзд. Их нельзя поставить в
краш/слоты/кейсы — только потратить в магазине по фиксированной цене
(без элемента случайности). Так вход в игры остаётся полностью бесплатным,
а обмен подарками не превращается в скрытую ставку.

Курс выкупа — единый процент BUYBACK_RATE от справочной стоимости подарка;
запас идёт в вашу маржу при перепродаже на реальном рынке
(Portals/Fragment/Tonnel) или на выдачу как приз в кейсах.
"""

BUYBACK_RATE = 0.65  # доля от справочной стоимости, которую отдаём игроку

# name -> {emoji, value}  — справочная стоимость подарка (звёзд-эквивалент),
# та же шкала, что и в кейсах (server/games.py). Список расширен известными
# коллекциями подарков Telegram, но Telegram выпускает новые постоянно —
# держать его идеально полным нереально. Цены — базовый (самый частый)
# вариант коллекции; редкие "улучшенные" NFT-варианты (особая модель/фон/
# символ) стоят на рынке кратно дороже — для них фиксированного курса нет,
# игрок подаёт заявку "Другой подарок", и админ сам назначает цену при
# подтверждении (см. /confirmtrade в боте).
GIFT_VALUES = {
    "Lol Pop": {"emoji": "🍭", "value": 40},
    "Candy Cane": {"emoji": "🍬", "value": 45},
    "B-Day Candle": {"emoji": "🕯", "value": 55},
    "Homemade Cake": {"emoji": "🍰", "value": 75},
    "Jelly Bunny": {"emoji": "🐰", "value": 90},
    "Cookie Heart": {"emoji": "🍪", "value": 90},
    "Desk Calendar": {"emoji": "📅", "value": 100},
    "Spiced Wine": {"emoji": "🍷", "value": 110},
    "Ice Cream": {"emoji": "🍨", "value": 115},
    "Bunny Muffin": {"emoji": "🧁", "value": 125},
    "Party Sparkler": {"emoji": "🎇", "value": 130},
    "Snoop Dogg": {"emoji": "🐶", "value": 150},
    "Holiday Drink": {"emoji": "🥤", "value": 170},
    "Snow Globe": {"emoji": "❄️", "value": 190},
    "Hypno Lollipop": {"emoji": "🍭", "value": 200},
    "Snoop Cigar": {"emoji": "🚬", "value": 250},
    "Star Notepad": {"emoji": "📓", "value": 255},
    "Evil Eye": {"emoji": "🧿", "value": 270},
    "Berry Box": {"emoji": "🍓", "value": 300},
    "Sakura Flower": {"emoji": "🌸", "value": 300},
    "Lush Bouquet": {"emoji": "💐", "value": 325},
    "Flying Broom": {"emoji": "🧹", "value": 340},
    "Sleigh Bell": {"emoji": "🔔", "value": 355},
    "Low Rider": {"emoji": "🚗", "value": 400},
    "Winter Wreath": {"emoji": "🎄", "value": 415},
    "Magic Potion": {"emoji": "🧪", "value": 445},
    "Top Hat": {"emoji": "🎩", "value": 460},
    "Kissed Frog": {"emoji": "🐸", "value": 500},
    "Jester Hat": {"emoji": "🃏", "value": 525},
    "Restless Jar": {"emoji": "🫙", "value": 540},
    "Mad Pumpkin": {"emoji": "🎃", "value": 585},
    "Xmas Stocking": {"emoji": "🧦", "value": 615},
    "Westside Sign": {"emoji": "🤟", "value": 700},
    "Electric Skull": {"emoji": "💀", "value": 700},
    "Hex Pot": {"emoji": "🍯", "value": 725},
    "Pet Snake": {"emoji": "🐍", "value": 800},
    "Witch Hat": {"emoji": "🎩", "value": 830},
    "Voodoo Doll": {"emoji": "🪆", "value": 860},
    "Light Sword": {"emoji": "⚔️", "value": 925},
    "Signet Ring": {"emoji": "💍", "value": 1000},
    "Nail Bracelet": {"emoji": "📿", "value": 1075},
    "Skull Flower": {"emoji": "💀", "value": 1110},
    "Sharp Tongue": {"emoji": "👅", "value": 1140},
    "Genie Lamp": {"emoji": "🪔", "value": 1200},
    "Tama Gadget": {"emoji": "🎮", "value": 1230},
    "Neko Helmet": {"emoji": "🐱", "value": 1300},
    "Berry Bracelet": {"emoji": "📿", "value": 1355},
    "Eternal Rose": {"emoji": "🌹", "value": 1415},
    "Swiss Watch": {"emoji": "⌚", "value": 1500},
    "Trapped Heart": {"emoji": "💔", "value": 1615},
    "Perfume Bottle": {"emoji": "🧴", "value": 1770},
    "Diamond Ring": {"emoji": "💍", "value": 1925},
    "Scared Cat": {"emoji": "🙀", "value": 2000},
    "Jack-in-the-Box": {"emoji": "🎁", "value": 2155},
    "Loot Bag": {"emoji": "💰", "value": 2500},
    "Vintage Cigar": {"emoji": "🚬", "value": 2770},
    "Ion Gem": {"emoji": "💎", "value": 3000},
    "Astral Shard": {"emoji": "🔷", "value": 4000},
    "Plush Pepe": {"emoji": "🐸", "value": 4460},
    "Mini Oscar": {"emoji": "🏆", "value": 5000},
    "Precious Peach": {"emoji": "🍑", "value": 7000},
    "Durov's Cap": {"emoji": "🧢", "value": 20000},
    "Heart Locket": {"emoji": "💝", "value": 30000},
}

# name -> {emoji, points}  (сколько баллов даём за подарок = value * BUYBACK_RATE)
BUYBACK_CATALOG = {
    name: {"emoji": d["emoji"], "points": round(d["value"] * BUYBACK_RATE / 5) * 5}
    for name, d in GIFT_VALUES.items()
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
