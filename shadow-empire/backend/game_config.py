"""
Game configuration — businesses, robberies, casino, items, cases, weapons, balance.
"""

LEGAL_BUSINESSES = [
    {
        "id": "car_wash", "name": "Автомойка", "emoji": "🚗",
        "base_cost": 800, "base_income": 3, "suspicion_reduce": 0.8,
        "cost_multiplier": 1.7, "income_multiplier": 1.15,
        "manager_cost": 5000, "unlock_level": 0,
    },
    {
        "id": "cafe", "name": "Кафе", "emoji": "☕",
        "base_cost": 5000, "base_income": 15, "suspicion_reduce": 1.5,
        "cost_multiplier": 1.8, "income_multiplier": 1.15,
        "manager_cost": 25000, "unlock_level": 0,
    },
    {
        "id": "restaurant", "name": "Ресторан", "emoji": "🍽",
        "base_cost": 25000, "base_income": 60, "suspicion_reduce": 3.0,
        "cost_multiplier": 1.85, "income_multiplier": 1.18,
        "manager_cost": 120000, "unlock_level": 3,
    },
    {
        "id": "hotel", "name": "Отель", "emoji": "🏨",
        "base_cost": 150000, "base_income": 250, "suspicion_reduce": 5.0,
        "cost_multiplier": 2.0, "income_multiplier": 1.18,
        "manager_cost": 600000, "unlock_level": 5,
    },
    {
        "id": "bank", "name": "Банк", "emoji": "🏦",
        "base_cost": 800000, "base_income": 1200, "suspicion_reduce": 10.0,
        "cost_multiplier": 2.2, "income_multiplier": 1.2,
        "manager_cost": 4000000, "unlock_level": 8,
    },
]

SHADOW_BUSINESSES = [
    {
        "id": "street_dealer", "name": "Точка на районе", "emoji": "🌿",
        "base_cost": 1200, "base_income": 7, "suspicion_add": 0.5,
        "cost_multiplier": 1.7, "income_multiplier": 1.18,
        "manager_cost": 8000, "unlock_level": 0,
    },
    {
        "id": "speakeasy", "name": "Подпольный бар", "emoji": "🥃",
        "base_cost": 8000, "base_income": 30, "suspicion_add": 1.0,
        "cost_multiplier": 1.8, "income_multiplier": 1.18,
        "manager_cost": 45000, "unlock_level": 0,
    },
    {
        "id": "casino", "name": "Подпольное казино", "emoji": "🎰",
        "base_cost": 45000, "base_income": 120, "suspicion_add": 2.0,
        "cost_multiplier": 1.85, "income_multiplier": 1.2,
        "manager_cost": 200000, "unlock_level": 3,
    },
    {
        "id": "laundering", "name": "Отмывочная", "emoji": "🧺",
        "base_cost": 200000, "base_income": 500, "suspicion_add": 3.5,
        "cost_multiplier": 2.0, "income_multiplier": 1.2,
        "manager_cost": 900000, "unlock_level": 6,
    },
    {
        "id": "syndicate", "name": "Синдикат", "emoji": "🕴",
        "base_cost": 1200000, "base_income": 2500, "suspicion_add": 6.0,
        "cost_multiplier": 2.2, "income_multiplier": 1.22,
        "manager_cost": 6000000, "unlock_level": 9,
    },
]

ROBBERIES = [
    {
        "id": "pickpocket", "name": "Карманная кража", "emoji": "👛",
        "min_reward": 50, "max_reward": 250, "success_chance": 0.75,
        "suspicion_gain": 5.0, "cooldown_seconds": 120, "unlock_level": 0,
    },
    {
        "id": "shop_robbery", "name": "Ограбление магазина", "emoji": "🏪",
        "min_reward": 400, "max_reward": 1500, "success_chance": 0.55,
        "suspicion_gain": 12.0, "cooldown_seconds": 600, "unlock_level": 2,
    },
    {
        "id": "warehouse", "name": "Налёт на склад", "emoji": "📦",
        "min_reward": 2500, "max_reward": 8000, "success_chance": 0.40,
        "suspicion_gain": 20.0, "cooldown_seconds": 1800, "unlock_level": 5,
    },
    {
        "id": "bank_heist", "name": "Ограбление банка", "emoji": "🏦",
        "min_reward": 12000, "max_reward": 40000, "success_chance": 0.22,
        "suspicion_gain": 40.0, "cooldown_seconds": 7200, "unlock_level": 8,
    },
]

# ── Casino ──
CASINO_GAMES = {
    "coinflip": {"name": "Монетка", "emoji": "🪙", "min_bet": 10, "max_bet": 50000},
    "dice": {"name": "Кости", "emoji": "🎲", "min_bet": 10, "max_bet": 50000},
    "slots": {"name": "Слоты", "emoji": "🎰", "min_bet": 50, "max_bet": 100000},
    "roulette": {"name": "Рулетка", "emoji": "🎡", "min_bet": 20, "max_bet": 100000},
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
RAID_THRESHOLD = 70.0
SUSPICION_DECAY_PER_SEC = 0.03
MAX_SUSPICION = 100.0
RAID_CASH_PENALTY = 0.5

# Reputation bonuses
FEAR_SHADOW_DISCOUNT = 0.01
RESPECT_LEGAL_DISCOUNT = 0.01
FEAR_INCOME_BONUS = 0.005
RESPECT_SUSPICION_REDUCE = 0.005

# Referral bonus
REFERRAL_BONUS = 1000

# PvP
PVP_COOLDOWN_SECONDS = 900
PVP_STEAL_PERCENT = 0.08
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

# ── Daily Login Rewards (7-day cycle) ──
LOGIN_REWARDS = [
    {"day": 1, "type": "cash", "amount": 200, "label": "$200"},
    {"day": 2, "type": "cash", "amount": 500, "label": "$500"},
    {"day": 3, "type": "cash", "amount": 1000, "label": "$1,000"},
    {"day": 4, "type": "cash", "amount": 2000, "label": "$2,000"},
    {"day": 5, "type": "cash", "amount": 4000, "label": "$4,000"},
    {"day": 6, "type": "case", "case_id": "case_basic", "label": "📦 Базовый кейс"},
    {"day": 7, "type": "cash", "amount": 8000, "label": "$8,000"},
]

# ── Prestige ──
PRESTIGE_CONFIG = {
    "base_level_required": 15,
    "level_increment": 5,  # +5 per prestige
    "multiplier_bonus": 0.12,  # +12% income per prestige level
}

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

# ── Achievements ──
ACHIEVEMENTS = [
    # Robberies
    {"id": "rob_10", "name": "Карманник", "emoji": "👛", "description": "Совершить 10 ограблений", "category": "robbery", "field": "total_robberies", "target": 10, "reward": 2000},
    {"id": "rob_50", "name": "Взломщик", "emoji": "🔓", "description": "Совершить 50 ограблений", "category": "robbery", "field": "total_robberies", "target": 50, "reward": 10000},
    {"id": "rob_200", "name": "Мастер-вор", "emoji": "🦹", "description": "Совершить 200 ограблений", "category": "robbery", "field": "total_robberies", "target": 200, "reward": 50000},
    # Earnings
    {"id": "earn_10k", "name": "Первые деньги", "emoji": "💵", "description": "Заработать $10,000", "category": "earnings", "field": "total_earned", "target": 10000, "reward": 1000},
    {"id": "earn_100k", "name": "На карман", "emoji": "💰", "description": "Заработать $100,000", "category": "earnings", "field": "total_earned", "target": 100000, "reward": 5000},
    {"id": "earn_1m", "name": "Миллионер", "emoji": "🤑", "description": "Заработать $1,000,000", "category": "earnings", "field": "total_earned", "target": 1000000, "reward": 25000},
    {"id": "earn_10m", "name": "Магнат", "emoji": "👑", "description": "Заработать $10,000,000", "category": "earnings", "field": "total_earned", "target": 10000000, "reward": 100000},
    # Level
    {"id": "lvl_5", "name": "Новичок района", "emoji": "⭐", "description": "Достичь уровня 5", "category": "level", "field": "level", "target": 5, "reward": 2000},
    {"id": "lvl_10", "name": "Авторитет", "emoji": "⭐", "description": "Достичь уровня 10", "category": "level", "field": "level", "target": 10, "reward": 5000},
    {"id": "lvl_25", "name": "Босс района", "emoji": "🌟", "description": "Достичь уровня 25", "category": "level", "field": "level", "target": 25, "reward": 20000},
    {"id": "lvl_50", "name": "Крёстный отец", "emoji": "🌟", "description": "Достичь уровня 50", "category": "level", "field": "level", "target": 50, "reward": 100000},
    # Collection
    {"id": "items_5", "name": "Коллекционер", "emoji": "🎒", "description": "Собрать 5 предметов", "category": "collection", "field": "inventory_count", "target": 5, "reward": 3000},
    {"id": "items_15", "name": "Барахольщик", "emoji": "🧳", "description": "Собрать 15 предметов", "category": "collection", "field": "inventory_count", "target": 15, "reward": 15000},
    {"id": "items_30", "name": "Хранитель", "emoji": "🏛", "description": "Собрать 30 предметов", "category": "collection", "field": "inventory_count", "target": 30, "reward": 50000},
    # Legendary
    {"id": "legendary_1", "name": "Легенда", "emoji": "🔥", "description": "Получить легендарный предмет", "category": "legendary", "field": "legendary_count", "target": 1, "reward": 10000},
    {"id": "legendary_3", "name": "Мифический", "emoji": "💀", "description": "Получить 3 легендарных предмета", "category": "legendary", "field": "legendary_count", "target": 3, "reward": 50000},
    # Gang
    {"id": "gang_join", "name": "Командный игрок", "emoji": "👥", "description": "Вступить в банду", "category": "gang", "field": "gang_id", "target": 1, "reward": 2000},
    # Prestige
    {"id": "prestige_1", "name": "Перерождение", "emoji": "⚡", "description": "Совершить первый престиж", "category": "prestige", "field": "prestige_level", "target": 1, "reward": 10000},
    {"id": "prestige_3", "name": "Ветеран", "emoji": "🏅", "description": "Достичь 3-го престижа", "category": "prestige", "field": "prestige_level", "target": 3, "reward": 50000},
    # PvP
    {"id": "pvp_5", "name": "Задира", "emoji": "👊", "description": "Победить 5 раз в PvP", "category": "pvp", "field": "pvp_wins", "target": 5, "reward": 5000},
    {"id": "pvp_20", "name": "Боец", "emoji": "🥊", "description": "Победить 20 раз в PvP", "category": "pvp", "field": "pvp_wins", "target": 20, "reward": 25000},
]

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
}

TON_WALLET_ADDRESS = "UQD...your_wallet_address..."  # Replace with real wallet

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

ALL_BUSINESSES = {b["id"]: {**b, "type": "legal"} for b in LEGAL_BUSINESSES}
ALL_BUSINESSES.update({b["id"]: {**b, "type": "shadow"} for b in SHADOW_BUSINESSES})

ALL_ROBBERIES = {r["id"]: r for r in ROBBERIES}
