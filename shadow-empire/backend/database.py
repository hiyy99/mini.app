import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "game.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS players (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        cash REAL DEFAULT 1000.0,
        reputation_fear INTEGER DEFAULT 0,
        reputation_respect INTEGER DEFAULT 0,
        suspicion REAL DEFAULT 0.0,
        last_collect_ts REAL DEFAULT 0.0,
        robbery_cooldown_ts REAL DEFAULT 0.0,
        total_earned REAL DEFAULT 0.0,
        total_taps INTEGER DEFAULT 0,
        total_robberies INTEGER DEFAULT 0,
        gang_id INTEGER DEFAULT 0,
        referral_code TEXT DEFAULT '',
        referred_by INTEGER DEFAULT 0,
        created_at REAL DEFAULT (strftime('%s','now'))
    );

    CREATE TABLE IF NOT EXISTS player_businesses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        business_id TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        has_manager INTEGER DEFAULT 0,
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id),
        UNIQUE(telegram_id, business_id)
    );

    CREATE TABLE IF NOT EXISTS robbery_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        target TEXT NOT NULL,
        success INTEGER DEFAULT 0,
        reward REAL DEFAULT 0.0,
        suspicion_gain REAL DEFAULT 0.0,
        created_at REAL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
    );

    CREATE TABLE IF NOT EXISTS player_character (
        telegram_id INTEGER PRIMARY KEY,
        nickname TEXT DEFAULT 'Новичок',
        avatar TEXT DEFAULT 'default',
        hat TEXT DEFAULT 'none',
        jacket TEXT DEFAULT 'none',
        accessory TEXT DEFAULT 'none',
        weapon TEXT DEFAULT 'none',
        car TEXT DEFAULT 'none',
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
    );

    CREATE TABLE IF NOT EXISTS player_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        item_id TEXT NOT NULL,
        equipped INTEGER DEFAULT 0,
        purchased_at REAL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id),
        UNIQUE(telegram_id, item_id)
    );

    CREATE TABLE IF NOT EXISTS player_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        case_id TEXT NOT NULL,
        purchased_at REAL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
    );

    CREATE TABLE IF NOT EXISTS market_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        item_id TEXT NOT NULL,
        price REAL NOT NULL,
        created_at REAL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (seller_id) REFERENCES players(telegram_id)
    );

    CREATE TABLE IF NOT EXISTS gangs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        tag TEXT NOT NULL,
        leader_id INTEGER NOT NULL,
        cash_bank REAL DEFAULT 0.0,
        power INTEGER DEFAULT 0,
        territory INTEGER DEFAULT 0,
        created_at REAL DEFAULT (strftime('%s','now'))
    );

    CREATE TABLE IF NOT EXISTS gang_members (
        telegram_id INTEGER PRIMARY KEY,
        gang_id INTEGER NOT NULL,
        role TEXT DEFAULT 'member',
        joined_at REAL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (gang_id) REFERENCES gangs(id)
    );

    CREATE TABLE IF NOT EXISTS pvp_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_id INTEGER NOT NULL,
        defender_id INTEGER NOT NULL,
        winner_id INTEGER NOT NULL,
        cash_stolen REAL DEFAULT 0.0,
        created_at REAL DEFAULT (strftime('%s','now'))
    );

    CREATE TABLE IF NOT EXISTS casino_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        game TEXT NOT NULL,
        bet REAL DEFAULT 0.0,
        result TEXT DEFAULT '',
        payout REAL DEFAULT 0.0,
        created_at REAL DEFAULT (strftime('%s','now'))
    );

    CREATE TABLE IF NOT EXISTS daily_missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        mission_id TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        target INTEGER DEFAULT 1,
        reward REAL DEFAULT 0.0,
        completed INTEGER DEFAULT 0,
        claimed INTEGER DEFAULT 0,
        day TEXT NOT NULL,
        UNIQUE(telegram_id, mission_id, day)
    );

    CREATE TABLE IF NOT EXISTS player_upgrades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        upgrade_id TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id),
        UNIQUE(telegram_id, upgrade_id)
    );

    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL,
        bonus_claimed INTEGER DEFAULT 0,
        created_at REAL DEFAULT (strftime('%s','now')),
        UNIQUE(referred_id)
    );

    CREATE TABLE IF NOT EXISTS daily_login (
        telegram_id INTEGER PRIMARY KEY,
        streak INTEGER DEFAULT 0,
        last_claim_date TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS territories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        emoji TEXT DEFAULT '',
        bonus_percent REAL DEFAULT 0.0,
        owner_gang_id INTEGER DEFAULT 0,
        captured_at REAL DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS territory_wars_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        territory_id INTEGER NOT NULL,
        attacker_gang_id INTEGER NOT NULL,
        defender_gang_id INTEGER DEFAULT 0,
        winner_gang_id INTEGER NOT NULL,
        attacker_power REAL DEFAULT 0,
        defender_power REAL DEFAULT 0,
        created_at REAL DEFAULT (strftime('%s','now'))
    );

    CREATE TABLE IF NOT EXISTS player_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        achievement_id TEXT NOT NULL,
        unlocked_at REAL DEFAULT (strftime('%s','now')),
        claimed INTEGER DEFAULT 0,
        UNIQUE(telegram_id, achievement_id)
    );

    CREATE TABLE IF NOT EXISTS premium_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        package_id TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        amount TEXT DEFAULT '',
        status TEXT DEFAULT 'completed',
        created_at REAL DEFAULT (strftime('%s','now')),
        FOREIGN KEY (telegram_id) REFERENCES players(telegram_id)
    );
    """)

    # ── Migrations (safe ALTER TABLE) ──
    migrations = [
        ("players", "prestige_level", "ALTER TABLE players ADD COLUMN prestige_level INTEGER DEFAULT 0"),
        ("players", "prestige_multiplier", "ALTER TABLE players ADD COLUMN prestige_multiplier REAL DEFAULT 1.0"),
        ("players", "pvp_wins", "ALTER TABLE players ADD COLUMN pvp_wins INTEGER DEFAULT 0"),
        ("gangs", "last_territory_attack_ts", "ALTER TABLE gangs ADD COLUMN last_territory_attack_ts REAL DEFAULT 0"),
        ("players", "is_vip", "ALTER TABLE players ADD COLUMN is_vip INTEGER DEFAULT 0"),
        ("players", "vip_until", "ALTER TABLE players ADD COLUMN vip_until REAL DEFAULT 0"),
        ("players", "last_ad_ts", "ALTER TABLE players ADD COLUMN last_ad_ts REAL DEFAULT 0"),
        ("players", "ad_boost_until", "ALTER TABLE players ADD COLUMN ad_boost_until REAL DEFAULT 0"),
        ("players", "last_vip_case_claim", "ALTER TABLE players ADD COLUMN last_vip_case_claim TEXT DEFAULT ''"),
    ]
    for table, column, sql in migrations:
        try:
            await db.execute(sql)
        except Exception:
            pass  # column already exists

    # ── Seed territories ──
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM territories")
    row = await cursor.fetchone()
    if row["cnt"] == 0:
        territory_seeds = [
            ("Порт", "🚢", 5.0),
            ("Промзона", "🏭", 4.0),
            ("Казино-квартал", "🎰", 7.0),
            ("Мэрия", "🏛", 6.0),
            ("Торговый район", "🏬", 5.0),
            ("Доки", "⚓", 4.0),
            ("Аэропорт", "✈️", 8.0),
            ("Старый город", "🏚", 3.0),
            ("Финансовый центр", "🏦", 10.0),
            ("Ночной квартал", "🌙", 6.0),
        ]
        for name, emoji, bonus in territory_seeds:
            await db.execute(
                "INSERT INTO territories (name, emoji, bonus_percent) VALUES (?, ?, ?)",
                (name, emoji, bonus),
            )

    await db.commit()
    await db.close()
