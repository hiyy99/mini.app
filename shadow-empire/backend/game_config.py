"""
Game configuration — businesses, robberies, casino, items, cases, weapons, balance.
"""

LEGAL_BUSINESSES = [
    {
        "id": "car_wash", "name": "Автомойка", "emoji": "🚗",
        "base_cost": 800, "base_income": 3, "suspicion_reduce": 0.8,
        "cost_multiplier": 2.0, "income_multiplier": 1.10,
        "manager_cost": 5000, "unlock_level": 0,
    },
    {
        "id": "cafe", "name": "Кафе", "emoji": "☕",
        "base_cost": 5000, "base_income": 15, "suspicion_reduce": 1.5,
        "cost_multiplier": 2.1, "income_multiplier": 1.10,
        "manager_cost": 25000, "unlock_level": 0,
    },
    {
        "id": "restaurant", "name": "Ресторан", "emoji": "🍽",
        "base_cost": 25000, "base_income": 60, "suspicion_reduce": 3.0,
        "cost_multiplier": 2.15, "income_multiplier": 1.12,
        "manager_cost": 120000, "unlock_level": 3,
    },
    {
        "id": "hotel", "name": "Отель", "emoji": "🏨",
        "base_cost": 150000, "base_income": 250, "suspicion_reduce": 5.0,
        "cost_multiplier": 2.3, "income_multiplier": 1.12,
        "manager_cost": 600000, "unlock_level": 5,
    },
    {
        "id": "bank", "name": "Банк", "emoji": "🏦",
        "base_cost": 800000, "base_income": 1200, "suspicion_reduce": 10.0,
        "cost_multiplier": 2.5, "income_multiplier": 1.14,
        "manager_cost": 4000000, "unlock_level": 8,
    },
]

SHADOW_BUSINESSES = [
    {
        "id": "street_dealer", "name": "Точка на районе", "emoji": "🌿",
        "base_cost": 1200, "base_income": 7, "suspicion_add": 0.5,
        "cost_multiplier": 2.0, "income_multiplier": 1.12,
        "manager_cost": 8000, "unlock_level": 0,
    },
    {
        "id": "speakeasy", "name": "Подпольный бар", "emoji": "🥃",
        "base_cost": 8000, "base_income": 30, "suspicion_add": 1.0,
        "cost_multiplier": 2.1, "income_multiplier": 1.12,
        "manager_cost": 45000, "unlock_level": 0,
    },
    {
        "id": "casino", "name": "Подпольное казино", "emoji": "🎰",
        "base_cost": 45000, "base_income": 120, "suspicion_add": 2.0,
        "cost_multiplier": 2.15, "income_multiplier": 1.14,
        "manager_cost": 200000, "unlock_level": 3,
    },
    {
        "id": "laundering", "name": "Отмывочная", "emoji": "🧺",
        "base_cost": 200000, "base_income": 500, "suspicion_add": 3.5,
        "cost_multiplier": 2.3, "income_multiplier": 1.14,
        "manager_cost": 900000, "unlock_level": 6,
    },
    {
        "id": "syndicate", "name": "Синдикат", "emoji": "🕴",
        "base_cost": 1200000, "base_income": 2500, "suspicion_add": 6.0,
        "cost_multiplier": 2.5, "income_multiplier": 1.15,
        "manager_cost": 6000000, "unlock_level": 9,
    },
]

ROBBERIES = [
    {
        "id": "pickpocket", "name": "Карманная кража", "emoji": "👛",
        "min_reward": 200, "max_reward": 1000, "success_chance": 0.75,
        "suspicion_gain": 5.0, "cooldown_seconds": 120, "unlock_level": 0,
    },
    {
        "id": "shop_robbery", "name": "Ограбление магазина", "emoji": "🏪",
        "min_reward": 2000, "max_reward": 8000, "success_chance": 0.55,
        "suspicion_gain": 12.0, "cooldown_seconds": 600, "unlock_level": 2,
    },
    {
        "id": "warehouse", "name": "Налёт на склад", "emoji": "📦",
        "min_reward": 15000, "max_reward": 50000, "success_chance": 0.45,
        "suspicion_gain": 20.0, "cooldown_seconds": 1800, "unlock_level": 5,
    },
    {
        "id": "bank_heist", "name": "Ограбление банка", "emoji": "🏦",
        "min_reward": 80000, "max_reward": 300000, "success_chance": 0.28,
        "suspicion_gain": 40.0, "cooldown_seconds": 7200, "unlock_level": 8,
    },
]

# ── Casino ──
CASINO_GAMES = {
    "coinflip": {"name": "Монетка", "emoji": "🪙", "min_bet": 10, "max_bet": 500000},
    "dice": {"name": "Кости", "emoji": "🎲", "min_bet": 10, "max_bet": 500000},
    "slots": {"name": "Слоты", "emoji": "🎰", "min_bet": 50, "max_bet": 1000000},
    "roulette": {"name": "Рулетка", "emoji": "🎡", "min_bet": 20, "max_bet": 1000000},
}

# ── Upgrades / Money Sinks ──
UPGRADES = {
    "bribe_police": {
        "name": "Взятка полиции", "emoji": "👮", "base_cost": 10000,
        "cost_multiplier": 3.0, "effect": "suspicion_reset",
        "description": "Обнулить подозрение",
    },
    "safe_house": {
        "name": "Конспиративная квартира", "emoji": "🏠", "base_cost": 100000,
        "cost_multiplier": 3.5, "effect": "raid_protection",
        "description": "Защита от следующего рейда",
    },
    "laundering_boost": {
        "name": "Схема отмывания", "emoji": "💸", "base_cost": 200000,
        "cost_multiplier": 2.5, "effect": "income_boost_10",
        "description": "+10% к доходу навсегда",
    },
    "territory": {
        "name": "Купить территорию", "emoji": "🗺", "base_cost": 400000,
        "cost_multiplier": 3.0, "effect": "territory",
        "description": "Новый район = больше дохода",
    },
    "bodyguards": {
        "name": "Охрана", "emoji": "🛡", "base_cost": 150000,
        "cost_multiplier": 2.5, "effect": "pvp_defense",
        "description": "+10 к силе защиты в PvP",
    },
}

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "💎", "7️⃣", "🍀"]
SLOT_PAYOUTS = {
    "🍒🍒🍒": 5, "🍋🍋🍋": 8, "🔔🔔🔔": 12,
    "💎💎💎": 25, "7️⃣7️⃣7️⃣": 50, "🍀🍀🍀": 100,
}
SLOT_TWO_MATCH_PAYOUT = 2

ROULETTE_NUMBERS = list(range(0, 37))
ROULETTE_RED = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
ROULETTE_BLACK = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

# ── Rarities ──
RARITIES = {
    "common":    {"name": "Обычный",      "color": "#9e9e9e", "order": 0},
    "uncommon":  {"name": "Необычный",    "color": "#4caf50", "order": 1},
    "rare":      {"name": "Редкий",       "color": "#2196f3", "order": 2},
    "epic":      {"name": "Эпический",    "color": "#9c27b0", "order": 3},
    "legendary": {"name": "Легендарный",  "color": "#ff9800", "order": 4},
}

# ── Shop Items — all wearable items ──
# case_only=True means item only drops from cases, not buyable directly
SHOP_ITEMS = {
    # ═══════════ HATS ═══════════
    "hat_cap": {
        "name": "Кепка", "emoji": "🧢", "slot": "hat", "price": 500,
        "rarity": "common", "description": "Простая уличная кепка",
        "bonus_type": "none", "bonus": 0, "case_only": False,
    },
    "hat_bandana": {
        "name": "Бандана", "emoji": "🟥", "slot": "hat", "price": 1500,
        "rarity": "common", "description": "Красная бандана — знак района",
        "bonus_type": "fear", "bonus": 1, "case_only": False,
    },
    "hat_mask": {
        "name": "Балаклава", "emoji": "🥷", "slot": "hat", "price": 3000,
        "rarity": "uncommon", "description": "Чёрная маска — идеальна для дела",
        "bonus_type": "fear", "bonus": 3, "case_only": False,
    },
    "hat_fedora": {
        "name": "Федора", "emoji": "🎩", "slot": "hat", "price": 8000,
        "rarity": "rare", "description": "Элегантная фетровая шляпа в стиле мафии",
        "bonus_type": "respect", "bonus": 3, "case_only": False,
    },
    "hat_military": {
        "name": "Армейский берет", "emoji": "🪖", "slot": "hat", "price": 0,
        "rarity": "rare", "description": "Краповый берет — знак боевого опыта",
        "bonus_type": "fear", "bonus": 5, "case_only": True,
    },
    "hat_crown": {
        "name": "Корона", "emoji": "👑", "slot": "hat", "price": 100000,
        "rarity": "epic", "description": "Тяжела голова, что носит корону",
        "bonus_type": "respect", "bonus": 10, "case_only": False,
    },
    "hat_neon": {
        "name": "Неоновый визор", "emoji": "🔮", "slot": "hat", "price": 0,
        "rarity": "epic", "description": "Футуристический визор с RGB подсветкой",
        "bonus_type": "income", "bonus": 5, "case_only": True,
    },
    "hat_demon": {
        "name": "Рога Демона", "emoji": "😈", "slot": "hat", "price": 0,
        "rarity": "legendary", "description": "Рога из чистого обсидиана — знак Тьмы",
        "bonus_type": "fear", "bonus": 15, "case_only": True,
    },

    # ═══════════ JACKETS ═══════════
    "jacket_hoodie": {
        "name": "Чёрное худи", "emoji": "👕", "slot": "jacket", "price": 800,
        "rarity": "common", "description": "Чёрное худи с глубоким капюшоном",
        "bonus_type": "none", "bonus": 0, "case_only": False,
    },
    "jacket_denim": {
        "name": "Джинсовка", "emoji": "🧥", "slot": "jacket", "price": 3000,
        "rarity": "common", "description": "Классическая джинсовая куртка",
        "bonus_type": "respect", "bonus": 1, "case_only": False,
    },
    "jacket_leather": {
        "name": "Кожаная куртка", "emoji": "🧥", "slot": "jacket", "price": 8000,
        "rarity": "uncommon", "description": "Тяжёлая кожанка — символ улицы",
        "bonus_type": "fear", "bonus": 3, "case_only": False,
    },
    "jacket_suit": {
        "name": "Костюм-тройка", "emoji": "👔", "slot": "jacket", "price": 25000,
        "rarity": "rare", "description": "Итальянский костюм ручной работы",
        "bonus_type": "respect", "bonus": 5, "case_only": False,
    },
    "jacket_neon": {
        "name": "Неоновый бомбер", "emoji": "💜", "slot": "jacket", "price": 0,
        "rarity": "rare", "description": "Бомбер с неоновыми LED-полосами",
        "bonus_type": "income", "bonus": 3, "case_only": True,
    },
    "jacket_military": {
        "name": "Бронежилет IV класса", "emoji": "🦺", "slot": "jacket", "price": 0,
        "rarity": "epic", "description": "Военный бронежилет — выдерживает автоматную очередь",
        "bonus_type": "fear", "bonus": 8, "case_only": True,
    },
    "jacket_dragon": {
        "name": "Куртка «Дракон»", "emoji": "🐉", "slot": "jacket", "price": 0,
        "rarity": "epic", "description": "Кожаная куртка с вышитым золотым драконом",
        "bonus_type": "income", "bonus": 7, "case_only": True,
    },
    "jacket_gold": {
        "name": "Золотой пиджак", "emoji": "✨", "slot": "jacket", "price": 200000,
        "rarity": "legendary", "description": "Пиджак из золотых нитей — для королей",
        "bonus_type": "income", "bonus": 10, "case_only": False,
    },

    # ═══════════ ACCESSORIES ═══════════
    "acc_chain": {
        "name": "Серебряная цепь", "emoji": "⛓", "slot": "accessory", "price": 2000,
        "rarity": "common", "description": "Толстая серебряная цепь на шею",
        "bonus_type": "fear", "bonus": 2, "case_only": False,
    },
    "acc_glasses": {
        "name": "Тёмные очки", "emoji": "🕶", "slot": "accessory", "price": 3000,
        "rarity": "uncommon", "description": "Авиаторы Ray-Ban — скрывают намерения",
        "bonus_type": "suspicion_reduce", "bonus": 2, "case_only": False,
    },
    "acc_watch": {
        "name": "Rolex Submariner", "emoji": "⌚", "slot": "accessory", "price": 15000,
        "rarity": "rare", "description": "Золотые часы — знак статуса",
        "bonus_type": "respect", "bonus": 4, "case_only": False,
    },
    "acc_skull": {
        "name": "Кольцо «Череп»", "emoji": "💀", "slot": "accessory", "price": 0,
        "rarity": "rare", "description": "Серебряный перстень с черепом",
        "bonus_type": "fear", "bonus": 5, "case_only": True,
    },
    "acc_rings": {
        "name": "Золотые перстни", "emoji": "💍", "slot": "accessory", "price": 50000,
        "rarity": "epic", "description": "Три массивных перстня с камнями",
        "bonus_type": "income", "bonus": 5, "case_only": False,
    },
    "acc_diamond": {
        "name": "Бриллиантовое колье", "emoji": "💎", "slot": "accessory", "price": 0,
        "rarity": "legendary", "description": "24 бриллианта чистой воды — бесценно",
        "bonus_type": "income", "bonus": 12, "case_only": True,
    },

    # ═══════════ CARS ═══════════
    "car_old": {
        "name": "ВАЗ-2107 «Семёрка»", "emoji": "🚗", "slot": "car", "price": 1000,
        "rarity": "common", "description": "Классика отечественного автопрома",
        "bonus_type": "none", "bonus": 0, "case_only": False,
    },
    "car_bmw": {
        "name": "BMW M5 F90", "emoji": "🚙", "slot": "car", "price": 30000,
        "rarity": "uncommon", "description": "Быстрый и агрессивный — 625 л.с.",
        "bonus_type": "respect", "bonus": 5, "case_only": False,
    },
    "car_mercedes": {
        "name": "Mercedes-AMG G63", "emoji": "🚐", "slot": "car", "price": 0,
        "rarity": "rare", "description": "Внедорожник для серьёзных людей",
        "bonus_type": "respect", "bonus": 7, "case_only": True,
    },
    "car_lambo": {
        "name": "Lamborghini Urus", "emoji": "🏎", "slot": "car", "price": 250000,
        "rarity": "epic", "description": "Суперкар на каждый день — 650 л.с.",
        "bonus_type": "income", "bonus": 8, "case_only": False,
    },
    "car_ferrari": {
        "name": "Ferrari F40", "emoji": "🏎", "slot": "car", "price": 0,
        "rarity": "epic", "description": "Легенда суперкаров — только 1315 штук в мире",
        "bonus_type": "income", "bonus": 10, "case_only": True,
    },
    "car_tank": {
        "name": "Бронемобиль «Тигр»", "emoji": "🛡", "slot": "car", "price": 500000,
        "rarity": "legendary", "description": "Полностью бронированный — не пробить",
        "bonus_type": "fear", "bonus": 15, "case_only": False,
    },
    "car_gold_rolls": {
        "name": "Золотой Rolls-Royce Phantom", "emoji": "👑", "slot": "car", "price": 0,
        "rarity": "legendary", "description": "Phantom в золотой обёртке — вершина роскоши",
        "bonus_type": "income", "bonus": 15, "case_only": True,
    },

    # ═══════════ WEAPONS (Black Market) ═══════════
    "weapon_knife": {
        "name": "Нож-бабочка", "emoji": "🔪", "slot": "weapon", "price": 2000,
        "rarity": "common", "description": "Складной нож — тихо и эффективно",
        "bonus_type": "fear", "bonus": 2, "case_only": False,
    },
    "weapon_bat": {
        "name": "Бейсбольная бита", "emoji": "🏏", "slot": "weapon", "price": 3500,
        "rarity": "common", "description": "Алюминиевая бита — классика разборок",
        "bonus_type": "fear", "bonus": 3, "case_only": False,
    },
    "weapon_brass": {
        "name": "Кастет", "emoji": "🤜", "slot": "weapon", "price": 5000,
        "rarity": "uncommon", "description": "Стальной кастет — для ближнего боя",
        "bonus_type": "fear", "bonus": 4, "case_only": False,
    },
    "weapon_pistol": {
        "name": "Пистолет Макарова", "emoji": "🔫", "slot": "weapon", "price": 15000,
        "rarity": "uncommon", "description": "Надёжный ПМ — проверен временем",
        "bonus_type": "fear", "bonus": 6, "case_only": False,
    },
    "weapon_shotgun": {
        "name": "Дробовик Remington 870", "emoji": "🔫", "slot": "weapon", "price": 40000,
        "rarity": "rare", "description": "Помповый дробовик — для серьёзных разговоров",
        "bonus_type": "fear", "bonus": 9, "case_only": False,
    },
    "weapon_katana": {
        "name": "Катана «Ветер смерти»", "emoji": "⚔️", "slot": "weapon", "price": 0,
        "rarity": "epic", "description": "Японский меч XVI века — путь воина",
        "bonus_type": "fear", "bonus": 12, "case_only": True,
    },
    "weapon_ak": {
        "name": "АК-47", "emoji": "🔫", "slot": "weapon", "price": 120000,
        "rarity": "epic", "description": "Легендарный автомат Калашникова",
        "bonus_type": "fear", "bonus": 15, "case_only": False,
    },
    "weapon_gold_deagle": {
        "name": "Золотой Desert Eagle", "emoji": "🔫", "slot": "weapon", "price": 0,
        "rarity": "legendary", "description": "Позолоченный .50 AE — для особых случаев",
        "bonus_type": "fear", "bonus": 20, "case_only": True,
    },
    "weapon_minigun": {
        "name": "Миниган M134", "emoji": "💥", "slot": "weapon", "price": 0,
        "rarity": "legendary", "description": "6000 выстрелов в минуту — конец дискуссии",
        "bonus_type": "fear", "bonus": 25, "case_only": True,
    },
}

# ── Cases / Lootboxes ──
CASES = {
    "case_basic": {
        "name": "Базовый кейс", "emoji": "📦", "price": 8000,
        "rarity": "common",
        "description": "В основном обычные предметы, но бывает везёт",
        "loot": [
            {"item_id": "hat_cap", "weight": 20},
            {"item_id": "hat_bandana", "weight": 20},
            {"item_id": "jacket_hoodie", "weight": 20},
            {"item_id": "jacket_denim", "weight": 20},
            {"item_id": "acc_chain", "weight": 15},
            {"item_id": "car_old", "weight": 15},
            {"item_id": "weapon_knife", "weight": 15},
            {"item_id": "weapon_bat", "weight": 12},
            {"item_id": "hat_mask", "weight": 5},
            {"item_id": "acc_glasses", "weight": 5},
            {"item_id": "jacket_leather", "weight": 3},
            {"item_id": "weapon_brass", "weight": 3},
        ],
    },
    "case_premium": {
        "name": "Премиум кейс", "emoji": "🎁", "price": 40000,
        "rarity": "rare",
        "description": "Качественный набор — высокий шанс редких предметов",
        "loot": [
            {"item_id": "hat_mask", "weight": 15},
            {"item_id": "hat_fedora", "weight": 12},
            {"item_id": "jacket_leather", "weight": 15},
            {"item_id": "jacket_suit", "weight": 10},
            {"item_id": "acc_glasses", "weight": 12},
            {"item_id": "acc_watch", "weight": 10},
            {"item_id": "car_bmw", "weight": 10},
            {"item_id": "weapon_pistol", "weight": 10},
            {"item_id": "hat_military", "weight": 5},
            {"item_id": "jacket_neon", "weight": 5},
            {"item_id": "acc_skull", "weight": 5},
            {"item_id": "car_mercedes", "weight": 5},
            {"item_id": "weapon_shotgun", "weight": 5},
            {"item_id": "hat_neon", "weight": 2},
            {"item_id": "jacket_dragon", "weight": 2},
        ],
    },
    "case_legendary": {
        "name": "Легендарный кейс", "emoji": "💀", "price": 180000,
        "rarity": "legendary",
        "description": "Элитный набор — реальный шанс на легендарку",
        "loot": [
            {"item_id": "hat_fedora", "weight": 10},
            {"item_id": "jacket_suit", "weight": 10},
            {"item_id": "acc_watch", "weight": 10},
            {"item_id": "hat_military", "weight": 8},
            {"item_id": "jacket_neon", "weight": 8},
            {"item_id": "acc_skull", "weight": 8},
            {"item_id": "car_mercedes", "weight": 8},
            {"item_id": "hat_crown", "weight": 5},
            {"item_id": "hat_neon", "weight": 5},
            {"item_id": "jacket_military", "weight": 5},
            {"item_id": "jacket_dragon", "weight": 5},
            {"item_id": "acc_rings", "weight": 5},
            {"item_id": "car_lambo", "weight": 3},
            {"item_id": "car_ferrari", "weight": 3},
            {"item_id": "weapon_katana", "weight": 3},
            {"item_id": "weapon_ak", "weight": 3},
            {"item_id": "hat_demon", "weight": 1},
            {"item_id": "jacket_gold", "weight": 1},
            {"item_id": "acc_diamond", "weight": 1},
            {"item_id": "car_gold_rolls", "weight": 1},
            {"item_id": "car_tank", "weight": 1},
            {"item_id": "weapon_gold_deagle", "weight": 1},
            {"item_id": "weapon_minigun", "weight": 1},
        ],
    },
    "case_weapon": {
        "name": "Оружейный кейс", "emoji": "⚔️", "price": 75000,
        "rarity": "epic",
        "description": "Только оружие — от ножа до минигана",
        "loot": [
            {"item_id": "weapon_knife", "weight": 25},
            {"item_id": "weapon_bat", "weight": 22},
            {"item_id": "weapon_brass", "weight": 18},
            {"item_id": "weapon_pistol", "weight": 14},
            {"item_id": "weapon_shotgun", "weight": 8},
            {"item_id": "weapon_katana", "weight": 5},
            {"item_id": "weapon_ak", "weight": 4},
            {"item_id": "weapon_gold_deagle", "weight": 2},
            {"item_id": "weapon_minigun", "weight": 1},
        ],
    },
}

# Market commission (10%)
MARKET_COMMISSION = 0.10

# Suspicion thresholds
RAID_THRESHOLD = 80.0
SUSPICION_DECAY_PER_SEC = 0.08
MAX_SUSPICION = 100.0
RAID_CASH_PENALTY = 0.3

# Reputation bonuses
FEAR_SHADOW_DISCOUNT = 0.01
RESPECT_LEGAL_DISCOUNT = 0.01
FEAR_INCOME_BONUS = 0.005
RESPECT_SUSPICION_REDUCE = 0.005

# Referral bonus
REFERRAL_BONUS = 1000

# PvP
PVP_COOLDOWN_SECONDS = 600
PVP_STEAL_PERCENT = 0.15
PVP_MIN_CASH_TO_ATTACK = 2000

# ── Daily Missions ──
MISSION_TEMPLATES = [
    {"id": "robbery", "name": "Совершить ограбление", "emoji": "🔫", "type": "robbery", "target": 3, "reward": 1000},
    {"id": "robbery_success", "name": "Успешное ограбление", "emoji": "💰", "type": "robbery_success", "target": 2, "reward": 1500},
    {"id": "casino_play", "name": "Сыграть в казино", "emoji": "🎰", "type": "casino_play", "target": 5, "reward": 800},
    {"id": "casino_win", "name": "Выиграть в казино", "emoji": "🎲", "type": "casino_win", "target": 2, "reward": 1500},
    {"id": "buy_business", "name": "Купить/улучшить бизнес", "emoji": "🏢", "type": "buy_business", "target": 2, "reward": 1200},
    {"id": "earn_cash_10k", "name": "Заработать $10,000", "emoji": "💵", "type": "earn_cash", "target": 10000, "reward": 1500},
    {"id": "earn_cash_50k", "name": "Заработать $50,000", "emoji": "💵", "type": "earn_cash", "target": 50000, "reward": 4000},
    {"id": "pvp_attack", "name": "Напасть на игрока", "emoji": "⚔️", "type": "pvp_attack", "target": 2, "reward": 1000},
    {"id": "pvp_win", "name": "Победить в PvP", "emoji": "🏆", "type": "pvp_win", "target": 1, "reward": 2000},
    {"id": "shop_buy", "name": "Купить предмет", "emoji": "🛒", "type": "shop_buy", "target": 1, "reward": 800},
    {"id": "case_open", "name": "Открыть кейс", "emoji": "📦", "type": "case_open", "target": 2, "reward": 1500},
    {"id": "case_open_1", "name": "Открыть кейс", "emoji": "📦", "type": "case_open", "target": 1, "reward": 800},
]

# ── Daily Login Rewards (30-day cycle) ──
LOGIN_REWARDS = [
    {"day": 1, "type": "cash", "amount": 200, "label": "$200"},
    {"day": 2, "type": "cash", "amount": 500, "label": "$500"},
    {"day": 3, "type": "cash", "amount": 1000, "label": "$1,000"},
    {"day": 4, "type": "cash", "amount": 2000, "label": "$2,000"},
    {"day": 5, "type": "cash", "amount": 4000, "label": "$4,000"},
    {"day": 6, "type": "case", "case_id": "case_basic", "label": "📦 Базовый кейс"},
    {"day": 7, "type": "cash", "amount": 8000, "label": "$8,000"},
    {"day": 8, "type": "cash", "amount": 5000, "label": "$5,000"},
    {"day": 9, "type": "cash", "amount": 5000, "label": "$5,000"},
    {"day": 10, "type": "cash", "amount": 7000, "label": "$7,000"},
    {"day": 11, "type": "cash", "amount": 10000, "label": "$10,000"},
    {"day": 12, "type": "case", "case_id": "case_basic", "label": "📦 Базовый кейс"},
    {"day": 13, "type": "cash", "amount": 12000, "label": "$12,000"},
    {"day": 14, "type": "case", "case_id": "case_premium", "label": "🎁 Премиум кейс"},
    {"day": 15, "type": "cash", "amount": 15000, "label": "$15,000"},
    {"day": 16, "type": "cash", "amount": 8000, "label": "$8,000"},
    {"day": 17, "type": "cash", "amount": 12000, "label": "$12,000"},
    {"day": 18, "type": "cash", "amount": 18000, "label": "$18,000"},
    {"day": 19, "type": "case", "case_id": "case_basic", "label": "📦 Базовый кейс"},
    {"day": 20, "type": "cash", "amount": 20000, "label": "$20,000"},
    {"day": 21, "type": "case", "case_id": "case_legendary", "label": "💀 Легендарный кейс"},
    {"day": 22, "type": "cash", "amount": 15000, "label": "$15,000"},
    {"day": 23, "type": "cash", "amount": 20000, "label": "$20,000"},
    {"day": 24, "type": "cash", "amount": 25000, "label": "$25,000"},
    {"day": 25, "type": "case", "case_id": "case_premium", "label": "🎁 Премиум кейс"},
    {"day": 26, "type": "cash", "amount": 30000, "label": "$30,000"},
    {"day": 27, "type": "cash", "amount": 35000, "label": "$35,000"},
    {"day": 28, "type": "case", "case_id": "case_weapon", "label": "⚔️ Оружейный кейс"},
    {"day": 29, "type": "cash", "amount": 40000, "label": "$40,000"},
    {"day": 30, "type": "cash_and_case", "amount": 100000, "case_id": "case_legendary", "label": "💀 $100K + Легендарный кейс"},
]

# ── Prestige ──
PRESTIGE_CONFIG = {
    "base_level_required": 15,
    "level_increment": 5,  # +5 per prestige
    "multiplier_bonus": 0.12,  # +12% income per prestige level
}

# ── Talent Tree (Prestige Perks) ──
TALENT_TREE = {
    "business": {
        "name": "Бизнес", "emoji": "💼",
        "talents": [
            {"id": "trade_grip", "name": "Торговая хватка", "emoji": "🤝", "description": "-3% стоимость бизнесов", "max_level": 3, "effect_per_level": 3},
            {"id": "passive_income", "name": "Пассивный доход", "emoji": "📈", "description": "+3% общий доход", "max_level": 3, "effect_per_level": 3},
            {"id": "quick_start", "name": "Быстрый старт", "emoji": "🚀", "description": "+$2K стартовый кэш", "max_level": 3, "effect_per_level": 2000},
            {"id": "efficiency", "name": "Эффективность", "emoji": "⏰", "description": "+1ч офлайн лимит", "max_level": 3, "effect_per_level": 1},
        ],
    },
    "criminal": {
        "name": "Криминал", "emoji": "🔫",
        "talents": [
            {"id": "robbery_master", "name": "Мастер ограблений", "emoji": "⏱", "description": "-8% КД ограблений", "max_level": 3, "effect_per_level": 8},
            {"id": "big_loot", "name": "Крупная добыча", "emoji": "💎", "description": "+5% награда ограблений", "max_level": 3, "effect_per_level": 5},
            {"id": "intimidation", "name": "Запугивание", "emoji": "😨", "description": "+2 страха при престиже", "max_level": 3, "effect_per_level": 2},
            {"id": "street_fighter", "name": "Уличный боец", "emoji": "🥊", "description": "+5 атака в PvP", "max_level": 3, "effect_per_level": 5},
        ],
    },
    "luck": {
        "name": "Удача", "emoji": "🍀",
        "talents": [
            {"id": "lucky", "name": "Фартовый", "emoji": "🎰", "description": "+$5K макс ставка казино", "max_level": 3, "effect_per_level": 5000},
            {"id": "lootbox_master", "name": "Лутбокс Мастер", "emoji": "📦", "description": "+3% шанс редкости кейсов", "max_level": 3, "effect_per_level": 3},
            {"id": "evasion", "name": "Уклонение", "emoji": "🛡", "description": "-5% потерь при рейде", "max_level": 3, "effect_per_level": 5},
            {"id": "shadow_talent", "name": "Тень", "emoji": "👤", "description": "-5% подозрение от теневых", "max_level": 3, "effect_per_level": 5},
        ],
    },
}

ALL_TALENTS = {}
for _branch_id, _branch in TALENT_TREE.items():
    for _t in _branch["talents"]:
        ALL_TALENTS[_t["id"]] = {**_t, "branch": _branch_id}

# ── Territories ──
TERRITORIES = [
    {"id": 1, "name": "Порт", "emoji": "🚢", "bonus_percent": 5.0},
    {"id": 2, "name": "Промзона", "emoji": "🏭", "bonus_percent": 4.0},
    {"id": 3, "name": "Казино-квартал", "emoji": "🎰", "bonus_percent": 7.0},
    {"id": 4, "name": "Мэрия", "emoji": "🏛", "bonus_percent": 6.0},
    {"id": 5, "name": "Торговый район", "emoji": "🏬", "bonus_percent": 5.0},
    {"id": 6, "name": "Доки", "emoji": "⚓", "bonus_percent": 4.0},
    {"id": 7, "name": "Аэропорт", "emoji": "✈️", "bonus_percent": 8.0},
    {"id": 8, "name": "Старый город", "emoji": "🏚", "bonus_percent": 3.0},
    {"id": 9, "name": "Финансовый центр", "emoji": "🏦", "bonus_percent": 10.0},
    {"id": 10, "name": "Ночной квартал", "emoji": "🌙", "bonus_percent": 6.0},
]
TERRITORY_ATTACK_COOLDOWN = 3600  # 1 hour

# ── Achievement Tiers & Categories ──
ACHIEVEMENT_CATEGORIES = {
    "robbery": {"name": "Ограбления", "emoji": "🔫"},
    "earnings": {"name": "Заработок", "emoji": "💰"},
    "level": {"name": "Уровень", "emoji": "⭐"},
    "pvp": {"name": "PvP", "emoji": "⚔️"},
    "collection": {"name": "Коллекция", "emoji": "🎒"},
    "gang": {"name": "Банда", "emoji": "👥"},
    "prestige": {"name": "Престиж", "emoji": "⚡"},
    "casino": {"name": "Казино", "emoji": "🎰"},
    "skins": {"name": "Скины", "emoji": "🎨"},
    "market": {"name": "Рынок", "emoji": "🏪"},
    "tournament": {"name": "Турнир", "emoji": "🏆"},
}

TIER_INFO = {
    "bronze": {"name": "Бронза", "color": "#cd7f32"},
    "silver": {"name": "Серебро", "color": "#c0c0c0"},
    "gold": {"name": "Золото", "color": "#ffd700"},
}

ACHIEVEMENTS = [
    # ── Robberies (5 tiers) ──
    {"id": "rob_10", "name": "Карманник", "emoji": "👛", "description": "Совершить 10 ограблений", "category": "robbery", "tier": "bronze", "field": "total_robberies", "target": 10, "reward": 2000},
    {"id": "rob_50", "name": "Взломщик", "emoji": "🔓", "description": "Совершить 50 ограблений", "category": "robbery", "tier": "silver", "field": "total_robberies", "target": 50, "reward": 10000},
    {"id": "rob_200", "name": "Мастер-вор", "emoji": "🦹", "description": "Совершить 200 ограблений", "category": "robbery", "tier": "gold", "field": "total_robberies", "target": 200, "reward": 50000},
    {"id": "rob_500", "name": "Легенда криминала", "emoji": "💀", "description": "Совершить 500 ограблений", "category": "robbery", "tier": "gold", "field": "total_robberies", "target": 500, "reward": 150000},
    {"id": "rob_1000", "name": "Неуловимый", "emoji": "🥷", "description": "Совершить 1000 ограблений", "category": "robbery", "tier": "gold", "field": "total_robberies", "target": 1000, "reward": 300000},
    # ── Earnings (5 tiers) ──
    {"id": "earn_10k", "name": "Первые деньги", "emoji": "💵", "description": "Заработать $10,000", "category": "earnings", "tier": "bronze", "field": "total_earned", "target": 10000, "reward": 1000},
    {"id": "earn_100k", "name": "На карман", "emoji": "💰", "description": "Заработать $100,000", "category": "earnings", "tier": "bronze", "field": "total_earned", "target": 100000, "reward": 5000},
    {"id": "earn_1m", "name": "Миллионер", "emoji": "🤑", "description": "Заработать $1,000,000", "category": "earnings", "tier": "silver", "field": "total_earned", "target": 1000000, "reward": 25000},
    {"id": "earn_10m", "name": "Магнат", "emoji": "👑", "description": "Заработать $10,000,000", "category": "earnings", "tier": "gold", "field": "total_earned", "target": 10000000, "reward": 100000},
    {"id": "earn_50m", "name": "Олигарх", "emoji": "💎", "description": "Заработать $50,000,000", "category": "earnings", "tier": "gold", "field": "total_earned", "target": 50000000, "reward": 500000},
    # ── Level (4 tiers) ──
    {"id": "lvl_5", "name": "Новичок района", "emoji": "⭐", "description": "Достичь уровня 5", "category": "level", "tier": "bronze", "field": "level", "target": 5, "reward": 2000},
    {"id": "lvl_10", "name": "Авторитет", "emoji": "⭐", "description": "Достичь уровня 10", "category": "level", "tier": "bronze", "field": "level", "target": 10, "reward": 5000},
    {"id": "lvl_25", "name": "Босс района", "emoji": "🌟", "description": "Достичь уровня 25", "category": "level", "tier": "silver", "field": "level", "target": 25, "reward": 20000},
    {"id": "lvl_50", "name": "Крёстный отец", "emoji": "🌟", "description": "Достичь уровня 50", "category": "level", "tier": "gold", "field": "level", "target": 50, "reward": 100000},
    # ── PvP (4 tiers) ──
    {"id": "pvp_5", "name": "Задира", "emoji": "👊", "description": "Победить 5 раз в PvP", "category": "pvp", "tier": "bronze", "field": "pvp_wins", "target": 5, "reward": 5000},
    {"id": "pvp_20", "name": "Боец", "emoji": "🥊", "description": "Победить 20 раз в PvP", "category": "pvp", "tier": "silver", "field": "pvp_wins", "target": 20, "reward": 25000},
    {"id": "pvp_50", "name": "Гладиатор", "emoji": "🗡", "description": "Победить 50 раз в PvP", "category": "pvp", "tier": "gold", "field": "pvp_wins", "target": 50, "reward": 75000},
    {"id": "pvp_100", "name": "Разрушитель", "emoji": "💥", "description": "Победить 100 раз в PvP", "category": "pvp", "tier": "gold", "field": "pvp_wins", "target": 100, "reward": 200000},
    # ── Collection (5 tiers) ──
    {"id": "items_5", "name": "Коллекционер", "emoji": "🎒", "description": "Собрать 5 предметов", "category": "collection", "tier": "bronze", "field": "inventory_count", "target": 5, "reward": 3000},
    {"id": "items_15", "name": "Барахольщик", "emoji": "🧳", "description": "Собрать 15 предметов", "category": "collection", "tier": "silver", "field": "inventory_count", "target": 15, "reward": 15000},
    {"id": "items_30", "name": "Хранитель", "emoji": "🏛", "description": "Собрать 30 предметов", "category": "collection", "tier": "gold", "field": "inventory_count", "target": 30, "reward": 50000},
    {"id": "items_50", "name": "Архивариус", "emoji": "📚", "description": "Собрать 50 предметов", "category": "collection", "tier": "gold", "field": "inventory_count", "target": 50, "reward": 100000},
    {"id": "legendary_1", "name": "Легенда", "emoji": "🔥", "description": "Получить легендарный предмет", "category": "collection", "tier": "silver", "field": "legendary_count", "target": 1, "reward": 10000},
    {"id": "legendary_3", "name": "Мифический", "emoji": "💀", "description": "Получить 3 легендарных", "category": "collection", "tier": "gold", "field": "legendary_count", "target": 3, "reward": 50000},
    {"id": "legendary_5", "name": "Хранитель Легенд", "emoji": "🏆", "description": "Получить 5 легендарных", "category": "collection", "tier": "gold", "field": "legendary_count", "target": 5, "reward": 150000},
    # ── Gang (3 tiers) ──
    {"id": "gang_join", "name": "Командный игрок", "emoji": "👥", "description": "Вступить в банду", "category": "gang", "tier": "bronze", "field": "gang_id", "target": 1, "reward": 2000},
    {"id": "gang_territory", "name": "Завоеватель", "emoji": "🗺", "description": "Захватить территорию", "category": "gang", "tier": "silver", "field": "gang_territories", "target": 1, "reward": 15000},
    {"id": "gang_territory_3", "name": "Империя", "emoji": "🌍", "description": "Захватить 3 территории", "category": "gang", "tier": "gold", "field": "gang_territories", "target": 3, "reward": 75000},
    # ── Prestige (3 tiers) ──
    {"id": "prestige_1", "name": "Перерождение", "emoji": "⚡", "description": "Совершить первый престиж", "category": "prestige", "tier": "bronze", "field": "prestige_level", "target": 1, "reward": 10000},
    {"id": "prestige_3", "name": "Ветеран", "emoji": "🏅", "description": "Достичь 3-го престижа", "category": "prestige", "tier": "silver", "field": "prestige_level", "target": 3, "reward": 50000},
    {"id": "prestige_5", "name": "Бессмертный", "emoji": "💫", "description": "Достичь 5-го престижа", "category": "prestige", "tier": "gold", "field": "prestige_level", "target": 5, "reward": 200000},
    # ── Casino (4 tiers) ──
    {"id": "casino_10", "name": "Новичок казино", "emoji": "🎰", "description": "Сыграть 10 раз", "category": "casino", "tier": "bronze", "field": "casino_plays", "target": 10, "reward": 2000},
    {"id": "casino_50", "name": "Завсегдатай", "emoji": "🎲", "description": "Сыграть 50 раз", "category": "casino", "tier": "silver", "field": "casino_plays", "target": 50, "reward": 10000},
    {"id": "casino_100", "name": "Игроман", "emoji": "🃏", "description": "Сыграть 100 раз", "category": "casino", "tier": "gold", "field": "casino_plays", "target": 100, "reward": 30000},
    {"id": "casino_win_20", "name": "Фартовый", "emoji": "🍀", "description": "Выиграть 20 раз", "category": "casino", "tier": "gold", "field": "casino_wins", "target": 20, "reward": 30000},
    {"id": "casino_win_50", "name": "Король казино", "emoji": "🎰", "description": "Выиграть 50 раз", "category": "casino", "tier": "gold", "field": "casino_wins", "target": 50, "reward": 100000},
    # ── Skins (3 tiers) ──
    {"id": "skins_5", "name": "Стилист", "emoji": "🎨", "description": "Собрать 5 скинов", "category": "skins", "tier": "bronze", "field": "skins_count", "target": 5, "reward": 5000},
    {"id": "skins_15", "name": "Модник", "emoji": "✨", "description": "Собрать 15 скинов", "category": "skins", "tier": "silver", "field": "skins_count", "target": 15, "reward": 20000},
    {"id": "skins_30", "name": "Коллекционер стиля", "emoji": "🎭", "description": "Собрать 30 скинов", "category": "skins", "tier": "gold", "field": "skins_count", "target": 30, "reward": 75000},
    # ── Market (3 tiers) ──
    {"id": "market_1", "name": "Торговец", "emoji": "🏪", "description": "Продать предмет на рынке", "category": "market", "tier": "bronze", "field": "market_sales", "target": 1, "reward": 3000},
    {"id": "market_10", "name": "Барыга", "emoji": "💼", "description": "Продать 10 предметов", "category": "market", "tier": "silver", "field": "market_sales", "target": 10, "reward": 20000},
    {"id": "market_25", "name": "Торговый Магнат", "emoji": "🏦", "description": "Продать 25 предметов", "category": "market", "tier": "gold", "field": "market_sales", "target": 25, "reward": 75000},
    # ── Tournament (2 tiers) ──
    {"id": "tourn_top10", "name": "Турнирный боец", "emoji": "🏆", "description": "Войти в топ-10 турнира", "category": "tournament", "tier": "silver", "field": "tournament_top10", "target": 1, "reward": 25000},
    {"id": "tourn_top3", "name": "Чемпион", "emoji": "🥇", "description": "Войти в топ-3 турнира", "category": "tournament", "tier": "gold", "field": "tournament_top3", "target": 1, "reward": 100000},
]

# ── Tournament (Daily) ──
TOURNAMENT_SCORE_EVENTS = {
    "robbery": 10,
    "robbery_success": 15,
    "pvp_win": 50,
    "pvp_attack": 10,
    "casino_win": 15,
    "casino_play": 5,
    "buy_business": 20,
    "case_open": 10,
    "boss_attack": 25,
}

TOURNAMENT_PRIZES = [
    {"place": 1, "cash": 100000, "cases": 3, "label": "1 место"},
    {"place": 2, "cash": 60000, "cases": 2, "label": "2 место"},
    {"place": 3, "cash": 40000, "cases": 1, "label": "3 место"},
    {"place": 4, "cash": 25000, "cases": 1, "label": "4 место"},
    {"place": 5, "cash": 20000, "cases": 0, "label": "5 место"},
    {"place": 6, "cash": 15000, "cases": 0, "label": "6 место"},
    {"place": 7, "cash": 12000, "cases": 0, "label": "7 место"},
    {"place": 8, "cash": 10000, "cases": 0, "label": "8 место"},
    {"place": 9, "cash": 8000, "cases": 0, "label": "9 место"},
    {"place": 10, "cash": 5000, "cases": 0, "label": "10 место"},
]

# ── Quest Lines ──
QUEST_LINES = [
    {
        "id": "beginner",
        "name": "История Начала",
        "emoji": "📖",
        "description": "Первые шаги в мире Shadow Empire",
        "unlock_level": 0,
        "steps": [
            {"trigger": "buy_business", "target": 1, "description": "Купи первый бизнес", "reward_type": "cash", "reward_amount": 2000},
            {"trigger": "robbery", "target": 1, "description": "Соверши ограбление", "reward_type": "cash", "reward_amount": 3000},
            {"trigger": "casino_play", "target": 1, "description": "Сыграй в казино", "reward_type": "cash", "reward_amount": 2000},
            {"trigger": "shop_buy", "target": 1, "description": "Купи предмет в магазине", "reward_type": "cash", "reward_amount": 5000},
            {"trigger": "gang_join", "target": 1, "description": "Вступи в банду", "reward_type": "cash", "reward_amount": 10000},
        ],
    },
    {
        "id": "power",
        "name": "Путь к Власти",
        "emoji": "👑",
        "description": "Стань настоящим боссом",
        "unlock_level": 5,
        "steps": [
            {"trigger": "buy_business", "target": 5, "description": "Владей 5 бизнесами", "reward_type": "cash", "reward_amount": 15000},
            {"trigger": "robbery", "target": 10, "description": "Соверши 10 ограблений", "reward_type": "cash", "reward_amount": 20000},
            {"trigger": "pvp_win", "target": 5, "description": "Победи 5 раз в PvP", "reward_type": "cash", "reward_amount": 30000},
            {"trigger": "territory_capture", "target": 1, "description": "Захвати территорию", "reward_type": "cash", "reward_amount": 50000},
            {"trigger": "earn_cash", "target": 1000000, "description": "Заработай $1,000,000", "reward_type": "case", "reward_amount": "case_legendary"},
        ],
    },
    {
        "id": "rising_shadow",
        "name": "Восходящая Тень",
        "emoji": "🌑",
        "description": "Укрепи свою власть в криминальном мире",
        "unlock_level": 10,
        "steps": [
            {"trigger": "buy_business", "target": 10, "description": "Владей 10 бизнесами", "reward_type": "cash", "reward_amount": 25000},
            {"trigger": "robbery", "target": 50, "description": "Соверши 50 ограблений", "reward_type": "cash", "reward_amount": 40000},
            {"trigger": "pvp_win", "target": 10, "description": "Победи 10 раз в PvP", "reward_type": "cash", "reward_amount": 50000},
            {"trigger": "territory_capture", "target": 1, "description": "Захвати территорию", "reward_type": "cash", "reward_amount": 75000},
            {"trigger": "earn_cash", "target": 5000000, "description": "Заработай $5,000,000", "reward_type": "case", "reward_amount": "case_legendary"},
        ],
    },
    {
        "id": "shadow_lord",
        "name": "Теневой Лорд",
        "emoji": "😈",
        "description": "Достигни вершины криминального мира",
        "unlock_level": 15,
        "steps": [
            {"trigger": "buy_business", "target": 15, "description": "Владей 15 бизнесами", "reward_type": "cash", "reward_amount": 50000},
            {"trigger": "prestige", "target": 1, "description": "Соверши престиж", "reward_type": "cash", "reward_amount": 100000},
            {"trigger": "legendary_collect", "target": 3, "description": "Собери 3 легендарки", "reward_type": "cash", "reward_amount": 150000},
            {"trigger": "boss_kill", "target": 3, "description": "Убей 3 боссов", "reward_type": "cash", "reward_amount": 200000},
            {"trigger": "earn_cash", "target": 10000000, "description": "Заработай $10,000,000", "reward_type": "cash", "reward_amount": 500000},
        ],
    },
]

# ── Seasonal Events ──
SEASONAL_EVENTS = [
    {
        "id": "winter_heist",
        "name": "Зимний Куш",
        "emoji": "❄️",
        "description": "Холодное время — горячие дела",
        "active": False,
        "bonuses": {"income_multiplier": 1.25, "robbery_multiplier": 1.5, "casino_multiplier": 1.0},
        "score_events": {"robbery": 15, "robbery_success": 25, "buy_business": 10, "earn_cash_10k": 5},
        "milestones": [
            {"target": 50, "reward_type": "cash", "reward_amount": 10000, "label": "50 очков — $10K"},
            {"target": 150, "reward_type": "cash", "reward_amount": 30000, "label": "150 очков — $30K"},
            {"target": 300, "reward_type": "case", "reward_amount": "case_premium", "label": "300 очков — Премиум кейс"},
            {"target": 500, "reward_type": "item", "reward_amount": "event_winter_hood", "label": "500 очков — Зимний Капюшон"},
        ],
    },
    {
        "id": "blood_moon",
        "name": "Кровавая Луна",
        "emoji": "🌑",
        "description": "В темноте скрываются возможности",
        "active": False,
        "bonuses": {"income_multiplier": 1.0, "robbery_multiplier": 1.0, "casino_multiplier": 1.5},
        "score_events": {"pvp_win": 30, "pvp_attack": 15, "casino_win": 20, "casino_play": 8},
        "milestones": [
            {"target": 50, "reward_type": "cash", "reward_amount": 10000, "label": "50 очков — $10K"},
            {"target": 150, "reward_type": "cash", "reward_amount": 30000, "label": "150 очков — $30K"},
            {"target": 300, "reward_type": "case", "reward_amount": "case_weapon", "label": "300 очков — Оружейный кейс"},
            {"target": 500, "reward_type": "item", "reward_amount": "event_moon_amulet", "label": "500 очков — Лунный Амулет"},
        ],
    },
    {
        "id": "gold_rush",
        "name": "Золотая Лихорадка",
        "emoji": "💰",
        "description": "Деньги на каждом шагу",
        "active": False,
        "bonuses": {"income_multiplier": 1.5, "robbery_multiplier": 1.25, "casino_multiplier": 1.25},
        "score_events": {"earn_cash_10k": 10, "buy_business": 15, "robbery_success": 20, "case_open": 12},
        "milestones": [
            {"target": 50, "reward_type": "cash", "reward_amount": 15000, "label": "50 очков — $15K"},
            {"target": 150, "reward_type": "cash", "reward_amount": 40000, "label": "150 очков — $40K"},
            {"target": 300, "reward_type": "case", "reward_amount": "case_legendary", "label": "300 очков — Легендарный кейс"},
            {"target": 500, "reward_type": "item", "reward_amount": "event_gold_vest", "label": "500 очков — Золотой Жилет"},
        ],
    },
]

# Event exclusive items (added to SHOP_ITEMS)
EVENT_ITEMS = {
    "event_winter_hood": {
        "name": "Зимний Капюшон", "emoji": "❄️", "slot": "hat", "price": 0,
        "rarity": "epic", "description": "Эксклюзив зимнего ивента",
        "bonus_type": "income", "bonus": 8, "case_only": True,
    },
    "event_moon_amulet": {
        "name": "Лунный Амулет", "emoji": "🌑", "slot": "accessory", "price": 0,
        "rarity": "epic", "description": "Эксклюзив ивента Кровавая Луна",
        "bonus_type": "fear", "bonus": 10, "case_only": True,
    },
    "event_gold_vest": {
        "name": "Золотой Жилет", "emoji": "💰", "slot": "jacket", "price": 0,
        "rarity": "epic", "description": "Эксклюзив Золотой Лихорадки",
        "bonus_type": "income", "bonus": 10, "case_only": True,
    },
}
SHOP_ITEMS.update(EVENT_ITEMS)

# ── Bosses (for gangs) ──
BOSSES = [
    {
        "id": "thug_boss",
        "name": "Главарь головорезов",
        "emoji": "👊",
        "base_hp": 5000,
        "reward_pool": 50000,
        "hp_per_gang_level": 100,
    },
    {
        "id": "cartel_lord",
        "name": "Лорд Картеля",
        "emoji": "🦹",
        "base_hp": 15000,
        "reward_pool": 150000,
        "hp_per_gang_level": 200,
    },
    {
        "id": "shadow_king",
        "name": "Теневой Король",
        "emoji": "👑",
        "base_hp": 50000,
        "reward_pool": 500000,
        "hp_per_gang_level": 500,
    },
    {
        "id": "cyber_demon",
        "name": "Кибер-Демон",
        "emoji": "🤖",
        "base_hp": 100000,
        "reward_pool": 1000000,
        "hp_per_gang_level": 1000,
    },
]

BOSS_ATTACK_COOLDOWN = 1800  # 30 minutes

# ── VIP & Monetization ──

AD_COOLDOWN = 180  # 3 minutes between ads

VIP_PACKAGES = {
    "vip_week":  {"stars": 100, "days": 7,  "label": "VIP на неделю"},
    "vip_month": {"stars": 350, "days": 30, "label": "VIP на месяц"},
}

CASH_PACKAGES = {
    "cash_small":  {"stars": 10,  "cash": 50000,   "label": "$50K"},
    "cash_medium": {"stars": 25,  "cash": 150000,  "label": "$150K"},
    "cash_large":  {"stars": 50,  "cash": 500000,  "label": "$500K"},
    "cash_mega":   {"stars": 100, "cash": 1500000, "label": "$1.5M"},
}

CASE_PACKAGES = {
    "case_premium_x3": {"stars": 30, "cases": [("case_premium", 3)],   "label": "3x Премиум кейса"},
    "case_legend_x1":  {"stars": 50, "cases": [("case_legendary", 1)], "label": "1x Легендарный кейс"},
}

TON_PRICES = {
    "vip_week":     0.5,
    "vip_month":    1.5,
    "cash_small":   0.05,
    "cash_medium":  0.12,
    "cash_large":   0.25,
    "cash_mega":    0.5,
    "case_premium_x3": 0.15,
    "case_legend_x1":  0.25,
    "season_1_premium": 2.5,
}

TON_WALLET_ADDRESS = "UQACgXUC3WxvB1ykvD_ah3f1qpsCkZLHLovExKBYKxzvVOu2"

VIP_ITEMS = {
    "hat_vip_crown": {
        "name": "Золотая корона", "emoji": "👑", "slot": "hat", "price": 0,
        "rarity": "legendary", "description": "Эксклюзивная корона для VIP",
        "bonus_type": "income", "bonus": 15, "case_only": False, "vip_only": True,
    },
    "car_vip_limo": {
        "name": "Лимузин VIP", "emoji": "🚙", "slot": "car", "price": 0,
        "rarity": "legendary", "description": "Роскошный лимузин для VIP-персон",
        "bonus_type": "respect", "bonus": 20, "case_only": False, "vip_only": True,
    },
    "acc_vip_diamond": {
        "name": "Алмазная цепь", "emoji": "💎", "slot": "accessory", "price": 0,
        "rarity": "legendary", "description": "Цепь из чистых алмазов — только для VIP",
        "bonus_type": "fear", "bonus": 15, "case_only": False, "vip_only": True,
    },
}

VIP_MARKET_COMMISSION = 0.05  # 5% for VIP instead of 10%

# Merge VIP items into SHOP_ITEMS so inventory/equip system recognizes them
SHOP_ITEMS.update(VIP_ITEMS)

# ── Gang Upgrades (paid from gang bank) ──
GANG_UPGRADES = {
    "gang_hq": {
        "name": "Штаб банды", "emoji": "🏚",
        "description": "+доход всем участникам",
        "max_level": 7,
        "costs": [50_000, 250_000, 1_000_000, 5_000_000, 25_000_000, 100_000_000, 500_000_000],
        "bonuses": [2, 4, 6, 8, 10, 13, 16],
        "bonus_type": "income_percent",
    },
    "gang_armory": {
        "name": "Арсенал", "emoji": "⚔️",
        "description": "+сила в войнах за территории",
        "max_level": 5,
        "costs": [100_000, 500_000, 3_000_000, 15_000_000, 80_000_000],
        "bonuses": [10, 25, 50, 80, 120],
        "bonus_type": "attack_power",
    },
    "gang_vault": {
        "name": "Хранилище", "emoji": "🏦",
        "description": "меньше потерь при рейде полиции",
        "max_level": 5,
        "costs": [75_000, 400_000, 2_000_000, 10_000_000, 60_000_000],
        "bonuses": [5, 10, 15, 20, 25],
        "bonus_type": "raid_reduction",
    },
}

GANG_CREATE_COST = 50_000
GANG_MAX_MEMBERS = 20

# ── Weekly Mini-Events (auto-rotating by day of week) ──
WEEKLY_EVENTS = {
    0: {"id": "monday_grind", "name": "Рабочий Понедельник", "emoji": "💼", "description": "Бизнес приносит больше", "bonus_type": "income", "multiplier": 1.20},
    1: {"id": "tuesday_heist", "name": "Вторник Ограблений", "emoji": "🔫", "description": "Награды за ограбления увеличены", "bonus_type": "robbery", "multiplier": 1.25},
    2: {"id": "wednesday_trade", "name": "Среда Торговли", "emoji": "🏪", "description": "Комиссия рынка снижена", "bonus_type": "market", "multiplier": 0.5},
    3: {"id": "thursday_luck", "name": "Четверг Удачи", "emoji": "🍀", "description": "Бонус казино", "bonus_type": "casino", "multiplier": 1.15},
    4: {"id": "friday_war", "name": "Пятница Войны", "emoji": "⚔️", "description": "PvP награды увеличены", "bonus_type": "pvp", "multiplier": 1.30},
    5: {"id": "saturday_loot", "name": "Субботний Лут", "emoji": "📦", "description": "Шанс редкого дропа выше", "bonus_type": "loot", "multiplier": 1.20},
    6: {"id": "sunday_rest", "name": "Воскресный Отдых", "emoji": "💰", "description": "Общий доход увеличен", "bonus_type": "income", "multiplier": 1.25},
}

# ── Gang Heists ──
GANG_HEISTS = {
    "warehouse_heist": {
        "name": "Ограбление склада", "emoji": "📦",
        "description": "Банда захватывает склад с товаром",
        "min_members": 2, "min_gang_level": 0,
        "cooldown": 3600,  # 1 hour
        "min_reward": 20000, "max_reward": 80000,
        "reward_per_member": 5000,
    },
    "vault_heist": {
        "name": "Взлом хранилища", "emoji": "🏦",
        "description": "Проникновение в банковское хранилище",
        "min_members": 3, "min_gang_level": 3,
        "cooldown": 7200,  # 2 hours
        "min_reward": 100000, "max_reward": 300000,
        "reward_per_member": 15000,
    },
    "casino_heist": {
        "name": "Казино ограбление", "emoji": "🎰",
        "description": "Дерзкий налёт на казино",
        "min_members": 4, "min_gang_level": 5,
        "cooldown": 14400,  # 4 hours
        "min_reward": 300000, "max_reward": 1000000,
        "reward_per_member": 40000,
    },
}

# ── Gang Wars ──
GANG_WAR_CONFIG = {
    "duration": 86400,  # 24 hours
    "declare_cost": 50000,  # from gang bank
    "min_gang_level": 3,  # minimum total gang power
    "score_per_pvp_win": 10,
    "score_per_territory_capture": 25,
    "winner_reward": 10000000,
    "loser_reward": 1000000,
}

# ── PvP Equipment Bonuses ──
PVP_WEAPON_RARITY_BONUS = {
    "common": 0.01,
    "uncommon": 0.015,
    "rare": 0.02,
    "epic": 0.025,
    "legendary": 0.03,
}

PVP_DEFENSE_RARITY_BONUS = {
    "common": 0.01,
    "uncommon": 0.02,
    "rare": 0.03,
    "epic": 0.04,
    "legendary": 0.05,
}

# ── Season Pass ──
SEASON_PASS_XP_EVENTS = {
    "robbery": 10, "robbery_success": 20,
    "pvp_win": 50, "pvp_attack": 15,
    "casino_win": 20, "casino_play": 5,
    "buy_business": 25, "case_open": 15,
    "boss_attack": 30, "territory_capture": 40,
    "shop_buy": 10, "gang_join": 20,
}

SEASON_PASS_CONFIG = {
    "id": "season_1",
    "name": "Сезон 1: Тёмный Путь",
    "emoji": "🏴",
    "xp_per_level": 100,
    "max_level": 30,
    "premium_stars": 500,
    "premium_ton": 2.5,
}

SEASON_PASS_REWARDS = {
    1:  {"free": {"type": "cash", "amount": 500},   "premium": {"type": "cash", "amount": 1500}},
    2:  {"free": {"type": "cash", "amount": 800},   "premium": {"type": "cash", "amount": 2000}},
    3:  {"free": {"type": "cash", "amount": 1000},  "premium": {"type": "cash", "amount": 3000}},
    4:  {"free": {"type": "cash", "amount": 1500},  "premium": {"type": "cash", "amount": 4000}},
    5:  {"free": {"type": "case", "case_id": "case_basic"}, "premium": {"type": "cash_and_case", "amount": 5000, "case_id": "case_premium"}},
    6:  {"free": {"type": "cash", "amount": 2000},  "premium": {"type": "cash", "amount": 6000}},
    7:  {"free": {"type": "cash", "amount": 2500},  "premium": {"type": "cash", "amount": 7000}},
    8:  {"free": {"type": "cash", "amount": 3000},  "premium": {"type": "case", "case_id": "case_premium"}},
    9:  {"free": {"type": "cash", "amount": 3500},  "premium": {"type": "cash", "amount": 9000}},
    10: {"free": {"type": "case", "case_id": "case_basic"}, "premium": {"type": "cash_and_case", "amount": 10000, "case_id": "case_premium"}},
    11: {"free": {"type": "cash", "amount": 4000},  "premium": {"type": "cash", "amount": 12000}},
    12: {"free": {"type": "cash", "amount": 4500},  "premium": {"type": "cash", "amount": 14000}},
    13: {"free": {"type": "cash", "amount": 5000},  "premium": {"type": "case", "case_id": "case_premium"}},
    14: {"free": {"type": "cash", "amount": 5500},  "premium": {"type": "cash", "amount": 16000}},
    15: {"free": {"type": "case", "case_id": "case_premium"}, "premium": {"type": "cash_and_case", "amount": 18000, "case_id": "case_legendary"}},
    16: {"free": {"type": "cash", "amount": 6000},  "premium": {"type": "cash", "amount": 20000}},
    17: {"free": {"type": "cash", "amount": 7000},  "premium": {"type": "cash", "amount": 22000}},
    18: {"free": {"type": "cash", "amount": 8000},  "premium": {"type": "case", "case_id": "case_premium"}},
    19: {"free": {"type": "cash", "amount": 9000},  "premium": {"type": "cash", "amount": 25000}},
    20: {"free": {"type": "case", "case_id": "case_premium"}, "premium": {"type": "cash_and_case", "amount": 30000, "case_id": "case_legendary"}},
    21: {"free": {"type": "cash", "amount": 10000}, "premium": {"type": "cash", "amount": 35000}},
    22: {"free": {"type": "cash", "amount": 12000}, "premium": {"type": "cash", "amount": 40000}},
    23: {"free": {"type": "cash", "amount": 14000}, "premium": {"type": "case", "case_id": "case_weapon"}},
    24: {"free": {"type": "cash", "amount": 16000}, "premium": {"type": "cash", "amount": 45000}},
    25: {"free": {"type": "case", "case_id": "case_premium"}, "premium": {"type": "cash_and_case", "amount": 50000, "case_id": "case_legendary"}},
    26: {"free": {"type": "cash", "amount": 20000}, "premium": {"type": "cash", "amount": 60000}},
    27: {"free": {"type": "cash", "amount": 25000}, "premium": {"type": "cash_and_case", "amount": 70000, "case_id": "case_legendary"}},
    28: {"free": {"type": "cash", "amount": 30000}, "premium": {"type": "cash", "amount": 80000}},
    29: {"free": {"type": "cash", "amount": 40000}, "premium": {"type": "cash", "amount": 100000}},
    30: {"free": {"type": "cash_and_case", "amount": 50000, "case_id": "case_premium"}, "premium": {"type": "cash_and_case", "amount": 200000, "case_id": "case_legendary"}},
}

ALL_BUSINESSES = {b["id"]: {**b, "type": "legal"} for b in LEGAL_BUSINESSES}
ALL_BUSINESSES.update({b["id"]: {**b, "type": "shadow"} for b in SHADOW_BUSINESSES})

ALL_ROBBERIES = {r["id"]: r for r in ROBBERIES}

# ── Business Skins ──

BUSINESS_SKINS = {
    # Common (50%)
    "midnight": {"name": "Полночь", "rarity": "common", "css": "skin-midnight", "emoji": "🌑"},
    "forest": {"name": "Лес", "rarity": "common", "css": "skin-forest", "emoji": "🌲"},
    "smoke": {"name": "Дым", "rarity": "common", "css": "skin-smoke", "emoji": "💨"},
    "rust": {"name": "Ржавчина", "rarity": "common", "css": "skin-rust", "emoji": "🔩"},
    "ocean": {"name": "Океан", "rarity": "common", "css": "skin-ocean", "emoji": "🌊"},
    # Rare (30%)
    "neon": {"name": "Неон", "rarity": "rare", "css": "skin-neon", "emoji": "💡"},
    "retro": {"name": "Ретро", "rarity": "rare", "css": "skin-retro", "emoji": "📼"},
    "arctic": {"name": "Арктика", "rarity": "rare", "css": "skin-arctic", "emoji": "❄️"},
    "crimson": {"name": "Кримсон", "rarity": "rare", "css": "skin-crimson", "emoji": "🩸"},
    # Epic (15%)
    "gold": {"name": "Золото", "rarity": "epic", "css": "skin-gold", "emoji": "👑"},
    "cyber": {"name": "Кибер", "rarity": "epic", "css": "skin-cyber", "emoji": "🤖"},
    "toxic": {"name": "Токсик", "rarity": "epic", "css": "skin-toxic", "emoji": "☢️"},
    # Legendary (4%)
    "dragon": {"name": "Дракон", "rarity": "legendary", "css": "skin-dragon", "emoji": "🐉"},
    "void": {"name": "Бездна", "rarity": "legendary", "css": "skin-void", "emoji": "🕳"},
    # Mythic (1%)
    "shadow_lord": {"name": "Shadow Lord", "rarity": "mythic", "css": "skin-shadowlord", "emoji": "👿"},
}

SKIN_RARITIES = {
    "common": {"name": "Обычный", "color": "#9e9e9e", "chance": 0.50},
    "rare": {"name": "Редкий", "color": "#3498db", "chance": 0.30},
    "epic": {"name": "Эпический", "color": "#9b59b6", "chance": 0.15},
    "legendary": {"name": "Легендарный", "color": "#f39c12", "chance": 0.04},
    "mythic": {"name": "Мифический", "color": "#e74c3c", "chance": 0.01},
}

SKIN_CASE = {
    "id": "skin_case",
    "name": "Кейс скинов",
    "emoji": "🎨",
    "description": "Скин для бизнеса — меняет внешний вид карточки",
    "stars_price": 50,
    "ton_price": 0.5,
}

SKIN_CASE_VIP = {
    "id": "skin_case_vip",
    "name": "VIP Кейс скинов",
    "emoji": "💎",
    "description": "Повышенный шанс редких скинов",
    "stars_price": 0,
    "ton_price": 0,
}
