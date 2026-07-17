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
# Список расширен известными коллекциями подарков Telegram, но Telegram
# выпускает новые постоянно — держать его идеально полным нереально.
# Цены — базовый (самый частый) вариант коллекции; редкие "улучшенные"
# NFT-варианты (особая модель/фон/символ) стоят на рынке кратно дороже —
# для них фиксированного курса нет, игрок подаёт заявку "Другой подарок",
# и админ сам назначает цену при подтверждении (см. /confirmtrade в боте).
BUYBACK_CATALOG = {
    "Lol Pop": {"emoji": "🍭", "points": 25},
    "Candy Cane": {"emoji": "🍬", "points": 30},
    "B-Day Candle": {"emoji": "🕯", "points": 35},
    "Homemade Cake": {"emoji": "🍰", "points": 50},
    "Jelly Bunny": {"emoji": "🐰", "points": 60},
    "Cookie Heart": {"emoji": "🍪", "points": 60},
    "Desk Calendar": {"emoji": "📅", "points": 65},
    "Spiced Wine": {"emoji": "🍷", "points": 70},
    "Ice Cream": {"emoji": "🍨", "points": 75},
    "Bunny Muffin": {"emoji": "🧁", "points": 80},
    "Party Sparkler": {"emoji": "🎇", "points": 85},
    "Snoop Dogg": {"emoji": "🐶", "points": 100},
    "Holiday Drink": {"emoji": "🥤", "points": 110},
    "Snow Globe": {"emoji": "❄️", "points": 125},
    "Hypno Lollipop": {"emoji": "🍭", "points": 130},
    "Snoop Cigar": {"emoji": "🚬", "points": 160},
    "Star Notepad": {"emoji": "📓", "points": 165},
    "Evil Eye": {"emoji": "🧿", "points": 175},
    "Berry Box": {"emoji": "🍓", "points": 195},
    "Sakura Flower": {"emoji": "🌸", "points": 195},
    "Lush Bouquet": {"emoji": "💐", "points": 210},
    "Flying Broom": {"emoji": "🧹", "points": 220},
    "Sleigh Bell": {"emoji": "🔔", "points": 230},
    "Low Rider": {"emoji": "🚗", "points": 260},
    "Winter Wreath": {"emoji": "🎄", "points": 270},
    "Magic Potion": {"emoji": "🧪", "points": 290},
    "Top Hat": {"emoji": "🎩", "points": 300},
    "Kissed Frog": {"emoji": "🐸", "points": 325},
    "Jester Hat": {"emoji": "🃏", "points": 340},
    "Restless Jar": {"emoji": "🫙", "points": 350},
    "Mad Pumpkin": {"emoji": "🎃", "points": 380},
    "Xmas Stocking": {"emoji": "🧦", "points": 400},
    "Westside Sign": {"emoji": "🤟", "points": 455},
    "Electric Skull": {"emoji": "💀", "points": 455},
    "Hex Pot": {"emoji": "🍯", "points": 470},
    "Pet Snake": {"emoji": "🐍", "points": 520},
    "Witch Hat": {"emoji": "🎩", "points": 540},
    "Voodoo Doll": {"emoji": "🪆", "points": 560},
    "Light Sword": {"emoji": "⚔️", "points": 600},
    "Signet Ring": {"emoji": "💍", "points": 650},
    "Nail Bracelet": {"emoji": "📿", "points": 700},
    "Skull Flower": {"emoji": "💀", "points": 720},
    "Sharp Tongue": {"emoji": "👅", "points": 740},
    "Genie Lamp": {"emoji": "🪔", "points": 780},
    "Tama Gadget": {"emoji": "🎮", "points": 800},
    "Neko Helmet": {"emoji": "🐱", "points": 845},
    "Berry Bracelet": {"emoji": "📿", "points": 880},
    "Eternal Rose": {"emoji": "🌹", "points": 920},
    "Swiss Watch": {"emoji": "⌚", "points": 975},
    "Trapped Heart": {"emoji": "💔", "points": 1050},
    "Perfume Bottle": {"emoji": "🧴", "points": 1150},
    "Diamond Ring": {"emoji": "💍", "points": 1250},
    "Scared Cat": {"emoji": "🙀", "points": 1300},
    "Jack-in-the-Box": {"emoji": "🎁", "points": 1400},
    "Loot Bag": {"emoji": "💰", "points": 1625},
    "Vintage Cigar": {"emoji": "🚬", "points": 1800},
    "Ion Gem": {"emoji": "💎", "points": 1950},
    "Astral Shard": {"emoji": "🔷", "points": 2600},
    "Plush Pepe": {"emoji": "🐸", "points": 2900},
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
