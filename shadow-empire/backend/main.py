"""
FastAPI backend for Shadow Empire game.
"""

import os
import json
import time
import random
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx

from backend.database import init_db, get_db
from backend.game_config import (
    ALL_BUSINESSES, ALL_ROBBERIES,
    LEGAL_BUSINESSES, SHADOW_BUSINESSES, ROBBERIES,
    CASINO_GAMES, SLOT_SYMBOLS, SLOT_PAYOUTS, SLOT_TWO_MATCH_PAYOUT,
    ROULETTE_RED, ROULETTE_BLACK, ROULETTE_NUMBERS,
    SHOP_ITEMS, MAX_SUSPICION, REFERRAL_BONUS, UPGRADES,
    PVP_COOLDOWN_SECONDS, PVP_STEAL_PERCENT, PVP_MIN_CASH_TO_ATTACK,
    CASES, RARITIES, MARKET_COMMISSION,
    MISSION_TEMPLATES, LOGIN_REWARDS, PRESTIGE_CONFIG,
    ACHIEVEMENTS, TERRITORY_ATTACK_COOLDOWN,
    VIP_PACKAGES, CASH_PACKAGES, CASE_PACKAGES, TON_PRICES,
    TON_WALLET_ADDRESS, VIP_ITEMS, VIP_MARKET_COMMISSION, AD_COOLDOWN,
)
from backend.game_logic import (
    calc_total_income, calc_offline_earnings, attempt_robbery,
    get_buy_cost, calc_manager_cost, get_player_level,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8553722467:AAFWR7NJUVtDveeSezAoOuuLoM8GssB3l8w")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Shadow Empire", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/index.html")


# ── Request Models ──

class PlayerInit(BaseModel):
    telegram_id: int
    username: str = ""
    referral_code: str = ""

class BuyRequest(BaseModel):
    telegram_id: int
    business_id: str

class ManagerRequest(BaseModel):
    telegram_id: int
    business_id: str

class CollectRequest(BaseModel):
    telegram_id: int

class RobberyRequest(BaseModel):
    telegram_id: int
    robbery_id: str

class CasinoBetRequest(BaseModel):
    telegram_id: int
    game: str
    bet: float
    choice: str = ""

class ShopBuyRequest(BaseModel):
    telegram_id: int
    item_id: str

class EquipRequest(BaseModel):
    telegram_id: int
    item_id: str

class GangCreateRequest(BaseModel):
    telegram_id: int
    name: str
    tag: str

class GangJoinRequest(BaseModel):
    telegram_id: int
    gang_id: int

class UpgradeRequest(BaseModel):
    telegram_id: int
    upgrade_id: str

class PvpAttackRequest(BaseModel):
    telegram_id: int
    target_id: int

class CaseBuyRequest(BaseModel):
    telegram_id: int
    case_id: str

class CaseOpenRequest(BaseModel):
    telegram_id: int
    player_case_id: int

class CaseSpinRequest(BaseModel):
    telegram_id: int
    case_id: str

class MarketListRequest(BaseModel):
    telegram_id: int
    item_id: str
    price: float

class MarketBuyRequest(BaseModel):
    telegram_id: int
    listing_id: int

class MissionClaimRequest(BaseModel):
    telegram_id: int
    mission_id: int

class LoginClaimRequest(BaseModel):
    telegram_id: int

class PrestigeRequest(BaseModel):
    telegram_id: int

class TerritoryAttackRequest(BaseModel):
    telegram_id: int
    territory_id: int

class AchievementClaimRequest(BaseModel):
    telegram_id: int
    achievement_id: str

class AdRewardRequest(BaseModel):
    telegram_id: int
    reward_type: str  # income_boost | free_bet | reset_cooldown

class StarsInvoiceRequest(BaseModel):
    telegram_id: int
    package_id: str

class VipDailyCaseRequest(BaseModel):
    telegram_id: int

class TonCreateRequest(BaseModel):
    telegram_id: int
    package_id: str

class TonVerifyRequest(BaseModel):
    telegram_id: int
    tx_hash: str

class VipItemClaimRequest(BaseModel):
    telegram_id: int
    item_id: str


# ── Helpers ──

async def get_player(db, telegram_id):
    cursor = await db.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None

async def get_owned_businesses(db, telegram_id):
    cursor = await db.execute("SELECT * FROM player_businesses WHERE telegram_id = ?", (telegram_id,))
    return [dict(r) for r in await cursor.fetchall()]

async def get_character(db, telegram_id):
    cursor = await db.execute("SELECT * FROM player_character WHERE telegram_id = ?", (telegram_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None

async def get_inventory(db, telegram_id):
    cursor = await db.execute("SELECT * FROM player_inventory WHERE telegram_id = ?", (telegram_id,))
    return [dict(r) for r in await cursor.fetchall()]

async def get_upgrades(db, telegram_id):
    cursor = await db.execute("SELECT * FROM player_upgrades WHERE telegram_id = ?", (telegram_id,))
    return [dict(r) for r in await cursor.fetchall()]

async def get_player_cases(db, telegram_id):
    cursor = await db.execute("SELECT * FROM player_cases WHERE telegram_id = ?", (telegram_id,))
    return [dict(r) for r in await cursor.fetchall()]

async def get_territory_bonus(db, gang_id):
    """Get total territory bonus % for a gang."""
    if not gang_id:
        return 0.0
    cursor = await db.execute("SELECT bonus_percent FROM territories WHERE owner_gang_id = ?", (gang_id,))
    rows = await cursor.fetchall()
    return sum(r["bonus_percent"] for r in rows)

def is_vip_active(player):
    """Check if player has active VIP status."""
    return bool(player.get("is_vip") and player.get("vip_until", 0) > time.time())

def has_ad_boost(player):
    """Check if player currently has ad income boost."""
    return player.get("ad_boost_until", 0) > time.time()

async def sync_earnings(db, player, owned):
    """Sync accumulated earnings before any action — fixes balance bug."""
    now = time.time()
    territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))
    vip = is_vip_active(player)
    equip_inc = await get_equip_income_bonus(db, player["telegram_id"])
    upgrade_inc = await get_upgrade_income_bonus(db, player["telegram_id"])
    earnings, new_suspicion, was_raided = calc_offline_earnings(
        owned, player["last_collect_ts"], player["suspicion"],
        player["reputation_fear"], player["reputation_respect"],
        player.get("prestige_multiplier", 1.0), territory_bonus,
        is_vip=vip, equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
    )
    new_cash = player["cash"] + earnings
    await db.execute(
        "UPDATE players SET cash = ?, suspicion = ?, last_collect_ts = ?, total_earned = total_earned + ? WHERE telegram_id = ?",
        (new_cash, new_suspicion, now, earnings, player["telegram_id"]),
    )
    await db.commit()
    player["cash"] = new_cash
    player["suspicion"] = new_suspicion
    player["last_collect_ts"] = now
    return player, was_raided

def make_referral_code(telegram_id):
    return hashlib.md5(f"shadow_{telegram_id}".encode()).hexdigest()[:8]

async def get_equip_income_bonus(db, telegram_id):
    """Sum of income % bonuses from equipped items."""
    character = await get_character(db, telegram_id)
    if not character:
        return 0
    total = 0
    for slot in ["hat", "jacket", "accessory", "car", "weapon"]:
        item_id = character.get(f"equipped_{slot}")
        if item_id and item_id in SHOP_ITEMS:
            item = SHOP_ITEMS[item_id]
            if item.get("bonus_type") == "income":
                total += item.get("bonus", 0)
    return total

async def get_upgrade_income_bonus(db, telegram_id):
    """Total income % bonus from laundering_boost upgrades (10% each level)."""
    cursor = await db.execute("SELECT level FROM player_upgrades WHERE telegram_id=? AND upgrade_id='laundering_boost'", (telegram_id,))
    row = await cursor.fetchone()
    if row:
        return row["level"] * 10
    return 0

def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def yesterday_utc():
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


# ── Daily Missions ──

async def generate_daily_missions(db, tid):
    """Generate 3 random missions for today if not already generated."""
    day = today_utc()
    cursor = await db.execute("SELECT id FROM daily_missions WHERE telegram_id=? AND day=?", (tid, day))
    if await cursor.fetchone():
        return  # already generated
    chosen = random.sample(MISSION_TEMPLATES, min(3, len(MISSION_TEMPLATES)))
    for m in chosen:
        await db.execute(
            "INSERT OR IGNORE INTO daily_missions (telegram_id, mission_id, target, reward, day) VALUES (?,?,?,?,?)",
            (tid, m["id"], m["target"], m["reward"], day),
        )
    await db.commit()

async def get_daily_missions(db, tid):
    day = today_utc()
    cursor = await db.execute("SELECT * FROM daily_missions WHERE telegram_id=? AND day=?", (tid, day))
    return [dict(r) for r in await cursor.fetchall()]

async def advance_mission(db, tid, mission_type, amount=1):
    """Advance progress on matching missions for today."""
    day = today_utc()
    cursor = await db.execute(
        "SELECT * FROM daily_missions WHERE telegram_id=? AND day=? AND completed=0",
        (tid, day),
    )
    missions = [dict(r) for r in await cursor.fetchall()]
    for m in missions:
        tmpl = next((t for t in MISSION_TEMPLATES if t["id"] == m["mission_id"]), None)
        if not tmpl or tmpl["type"] != mission_type:
            continue
        new_progress = min(m["progress"] + amount, m["target"])
        completed = 1 if new_progress >= m["target"] else 0
        await db.execute(
            "UPDATE daily_missions SET progress=?, completed=? WHERE id=?",
            (new_progress, completed, m["id"]),
        )
    await db.commit()


# ── Daily Login ──

async def check_login_streak(db, tid):
    """Check login streak and return login_data."""
    day = today_utc()
    yest = yesterday_utc()
    cursor = await db.execute("SELECT * FROM daily_login WHERE telegram_id=?", (tid,))
    row = await cursor.fetchone()
    if not row:
        await db.execute("INSERT INTO daily_login (telegram_id, streak, last_claim_date) VALUES (?,0,'')", (tid,))
        await db.commit()
        return {"can_claim": True, "streak": 0, "reward_day": 1}

    row = dict(row)
    last_claim = row["last_claim_date"]
    streak = row["streak"]

    if last_claim == day:
        reward_day = ((streak - 1) % 7) + 1
        return {"can_claim": False, "streak": streak, "reward_day": reward_day}

    if last_claim == yest:
        new_streak = streak + 1
    else:
        new_streak = 1

    reward_day = ((new_streak - 1) % 7) + 1
    return {"can_claim": True, "streak": new_streak, "reward_day": reward_day}


# ── Achievements ──

async def check_achievements(db, tid):
    """Check and unlock new achievements."""
    player = await get_player(db, tid)
    if not player:
        return
    owned = await get_owned_businesses(db, tid)
    inventory = await get_inventory(db, tid)
    player_level = get_player_level(owned)

    inventory_count = len(inventory)
    legendary_count = sum(1 for i in inventory if SHOP_ITEMS.get(i["item_id"], {}).get("rarity") == "legendary")

    values = {
        "total_robberies": player.get("total_robberies", 0),
        "total_earned": player.get("total_earned", 0),
        "level": player_level,
        "inventory_count": inventory_count,
        "legendary_count": legendary_count,
        "gang_id": 1 if player.get("gang_id", 0) > 0 else 0,
        "prestige_level": player.get("prestige_level", 0),
        "pvp_wins": player.get("pvp_wins", 0),
    }

    for ach in ACHIEVEMENTS:
        field_val = values.get(ach["field"], 0)
        if field_val >= ach["target"]:
            await db.execute(
                "INSERT OR IGNORE INTO player_achievements (telegram_id, achievement_id) VALUES (?,?)",
                (tid, ach["id"]),
            )
    await db.commit()

async def get_player_achievements(db, tid):
    cursor = await db.execute("SELECT * FROM player_achievements WHERE telegram_id=?", (tid,))
    return [dict(r) for r in await cursor.fetchall()]


# ── Player Init ──

@app.post("/api/init")
async def player_init(req: PlayerInit):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player:
            ref_code = f"ref_{req.telegram_id}"
            await db.execute(
                "INSERT INTO players (telegram_id, username, last_collect_ts, referral_code) VALUES (?, ?, ?, ?)",
                (req.telegram_id, req.username, time.time(), ref_code),
            )
            await db.execute(
                "INSERT INTO player_character (telegram_id) VALUES (?)", (req.telegram_id,)
            )
            if req.referral_code:
                # Parse referrer telegram_id from ref code like "ref_12345"
                referrer_id = None
                rc = req.referral_code
                if rc.startswith("ref_"):
                    try: referrer_id = int(rc[4:])
                    except: pass
                else:
                    # Legacy: lookup by old hash code
                    cursor = await db.execute("SELECT telegram_id FROM players WHERE referral_code = ?", (rc,))
                    row = await cursor.fetchone()
                    if row: referrer_id = row["telegram_id"]
                if referrer_id and referrer_id != req.telegram_id:
                    # Check referrer exists
                    cursor = await db.execute("SELECT telegram_id FROM players WHERE telegram_id = ?", (referrer_id,))
                    referrer = await cursor.fetchone()
                    if referrer:
                        await db.execute(
                            "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                            (referrer_id, req.telegram_id),
                        )
                        await db.execute(
                            "UPDATE players SET cash = cash + ?, referred_by = ? WHERE telegram_id = ?",
                            (REFERRAL_BONUS, referrer_id, req.telegram_id),
                        )
                        await db.execute(
                            "UPDATE players SET cash = cash + ? WHERE telegram_id = ?",
                            (REFERRAL_BONUS, referrer_id),
                        )
            await db.commit()
            player = await get_player(db, req.telegram_id)

        owned = await get_owned_businesses(db, req.telegram_id)
        player, was_raided = await sync_earnings(db, player, owned)

        character = await get_character(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)
        upgrades = await get_upgrades(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)
        territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))

        # VIP status
        vip = is_vip_active(player)
        vip_mult = 2.0 if vip else 1.0
        ad_boost = has_ad_boost(player)

        # Auto-expire VIP
        if player.get("is_vip") and not vip:
            await db.execute("UPDATE players SET is_vip=0 WHERE telegram_id=?", (req.telegram_id,))
            await db.commit()
            player["is_vip"] = 0

        equip_inc = await get_equip_income_bonus(db, req.telegram_id)
        upgrade_inc = await get_upgrade_income_bonus(db, req.telegram_id)
        income_per_sec, suspicion_per_sec = calc_total_income(
            owned, player["reputation_fear"], player["reputation_respect"],
            player.get("prestige_multiplier", 1.0), territory_bonus,
            vip_multiplier=vip_mult, ad_boost=ad_boost,
            equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
        )

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ?", (req.telegram_id,))
        ref_row = await cursor.fetchone()
        referral_count = ref_row["cnt"] if ref_row else 0

        # Market listings from other players
        cursor = await db.execute(
            "SELECT ml.*, p.username as seller_name FROM market_listings ml JOIN players p ON p.telegram_id=ml.seller_id WHERE ml.seller_id != ? ORDER BY ml.created_at DESC LIMIT 50",
            (req.telegram_id,)
        )
        market_listings = [dict(r) for r in await cursor.fetchall()]

        # Own listings
        cursor = await db.execute(
            "SELECT * FROM market_listings WHERE seller_id = ?", (req.telegram_id,)
        )
        my_listings = [dict(r) for r in await cursor.fetchall()]

        # Daily missions
        await generate_daily_missions(db, req.telegram_id)
        daily_missions = await get_daily_missions(db, req.telegram_id)

        # Daily login
        login_data = await check_login_streak(db, req.telegram_id)

        # Achievements
        await check_achievements(db, req.telegram_id)
        achievements = await get_player_achievements(db, req.telegram_id)

        # Territories
        cursor = await db.execute(
            "SELECT t.*, g.name as gang_name, g.tag as gang_tag FROM territories t LEFT JOIN gangs g ON g.id=t.owner_gang_id"
        )
        territories = [dict(r) for r in await cursor.fetchall()]

        # VIP status info
        vip_days_left = 0
        if vip:
            vip_days_left = max(0, int((player.get("vip_until", 0) - time.time()) / 86400))

        vip_status = {
            "active": vip,
            "until": player.get("vip_until", 0),
            "days_left": vip_days_left,
        }

        return {
            "player": player,
            "businesses": owned,
            "character": character,
            "inventory": inventory,
            "upgrades": upgrades,
            "player_cases": player_cases,
            "income_per_sec": income_per_sec,
            "suspicion_per_sec": suspicion_per_sec,
            "player_level": get_player_level(owned),
            "was_raided": was_raided,
            "legal_businesses": LEGAL_BUSINESSES,
            "shadow_businesses": SHADOW_BUSINESSES,
            "robberies": ROBBERIES,
            "casino_games": CASINO_GAMES,
            "shop_items": SHOP_ITEMS,
            "upgrades_config": UPGRADES,
            "cases_config": CASES,
            "rarities": RARITIES,
            "market_listings": market_listings,
            "my_listings": my_listings,
            "referral_count": referral_count,
            "daily_missions": daily_missions,
            "login_data": login_data,
            "login_rewards": LOGIN_REWARDS,
            "achievements": achievements,
            "achievements_config": ACHIEVEMENTS,
            "prestige_config": PRESTIGE_CONFIG,
            "territories": territories,
            "territory_bonus": territory_bonus,
            "vip_status": vip_status,
            "ad_boost_until": player.get("ad_boost_until", 0),
            "vip_packages": VIP_PACKAGES,
            "cash_packages": CASH_PACKAGES,
            "case_packages": CASE_PACKAGES,
            "ton_prices": TON_PRICES,
            "vip_items": VIP_ITEMS,
        }
    finally:
        await db.close()


# ── Business ──

@app.post("/api/buy")
async def buy_business(req: BuyRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)
        owned = await get_owned_businesses(db, req.telegram_id)

        cfg = ALL_BUSINESSES.get(req.business_id)
        if not cfg: raise HTTPException(400, "Unknown business")
        player_level = get_player_level(owned)
        if player_level < cfg["unlock_level"]:
            raise HTTPException(400, f"Need level {cfg['unlock_level']}")

        existing = next((b for b in owned if b["business_id"] == req.business_id), None)
        current_level = existing["level"] if existing else 0
        cost = get_buy_cost(req.business_id, max(current_level, 1), player["reputation_fear"], player["reputation_respect"])
        if player["cash"] < cost: raise HTTPException(400, "Not enough cash")

        new_cash = player["cash"] - cost
        if existing:
            await db.execute("UPDATE player_businesses SET level = ? WHERE id = ?", (existing["level"] + 1, existing["id"]))
        else:
            await db.execute("INSERT INTO player_businesses (telegram_id, business_id, level) VALUES (?, ?, 1)", (req.telegram_id, req.business_id))

        rep_col = "reputation_fear" if cfg["type"] == "shadow" else "reputation_respect"
        await db.execute(f"UPDATE players SET cash = ?, {rep_col} = {rep_col} + 1 WHERE telegram_id = ?", (new_cash, req.telegram_id))
        await db.commit()

        # Mission hook
        await advance_mission(db, req.telegram_id, "buy_business")

        player = await get_player(db, req.telegram_id)
        owned = await get_owned_businesses(db, req.telegram_id)
        territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))
        vip_mult = 2.0 if is_vip_active(player) else 1.0
        ad_boost = has_ad_boost(player)
        equip_inc = await get_equip_income_bonus(db, req.telegram_id)
        upgrade_inc = await get_upgrade_income_bonus(db, req.telegram_id)
        income_per_sec, suspicion_per_sec = calc_total_income(
            owned, player["reputation_fear"], player["reputation_respect"],
            player.get("prestige_multiplier", 1.0), territory_bonus,
            vip_multiplier=vip_mult, ad_boost=ad_boost,
            equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
        )
        return {"player": player, "businesses": owned, "income_per_sec": income_per_sec, "suspicion_per_sec": suspicion_per_sec, "player_level": get_player_level(owned)}
    finally:
        await db.close()


@app.post("/api/manager")
async def hire_manager(req: ManagerRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        existing = next((b for b in owned if b["business_id"] == req.business_id), None)
        if not existing: raise HTTPException(400, "Not owned")
        if existing["has_manager"]: raise HTTPException(400, "Already has manager")

        cost = calc_manager_cost(ALL_BUSINESSES[req.business_id])
        if player["cash"] < cost: raise HTTPException(400, "Not enough cash")

        await db.execute("UPDATE players SET cash = cash - ? WHERE telegram_id = ?", (cost, req.telegram_id))
        await db.execute("UPDATE player_businesses SET has_manager = 1 WHERE id = ?", (existing["id"],))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        owned = await get_owned_businesses(db, req.telegram_id)
        return {"player": player, "businesses": owned}
    finally:
        await db.close()


@app.post("/api/collect")
async def collect_income(req: CollectRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        old_earned = player.get("total_earned", 0)
        player, was_raided = await sync_earnings(db, player, owned)
        new_earned = player.get("total_earned", 0)
        earnings = new_earned - old_earned

        # Mission hook: earn_cash
        if earnings > 0:
            await advance_mission(db, req.telegram_id, "earn_cash", int(earnings))

        territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))
        vip_mult = 2.0 if is_vip_active(player) else 1.0
        ad_boost = has_ad_boost(player)
        equip_inc = await get_equip_income_bonus(db, req.telegram_id)
        upgrade_inc = await get_upgrade_income_bonus(db, req.telegram_id)
        income_per_sec, suspicion_per_sec = calc_total_income(
            owned, player["reputation_fear"], player["reputation_respect"],
            player.get("prestige_multiplier", 1.0), territory_bonus,
            vip_multiplier=vip_mult, ad_boost=ad_boost,
            equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
        )
        return {"player": player, "was_raided": was_raided, "income_per_sec": income_per_sec, "suspicion_per_sec": suspicion_per_sec}
    finally:
        await db.close()


# ── Robbery ──

@app.post("/api/robbery")
async def do_robbery(req: RobberyRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        cfg = ALL_ROBBERIES.get(req.robbery_id)
        if not cfg: raise HTTPException(400, "Unknown robbery")
        if get_player_level(owned) < cfg["unlock_level"]:
            raise HTTPException(400, f"Need level {cfg['unlock_level']}")

        now = time.time()
        if player["robbery_cooldown_ts"] > now:
            raise HTTPException(400, f"Cooldown: {int(player['robbery_cooldown_ts'] - now)}s")

        success, reward, suspicion_gain = attempt_robbery(req.robbery_id, player["reputation_fear"])
        new_cash = player["cash"] + reward
        new_suspicion = min(player["suspicion"] + suspicion_gain, MAX_SUSPICION)

        await db.execute(
            "UPDATE players SET cash=?, suspicion=?, robbery_cooldown_ts=?, reputation_fear=reputation_fear+2, total_robberies=total_robberies+1 WHERE telegram_id=?",
            (new_cash, new_suspicion, now + cfg["cooldown_seconds"], req.telegram_id),
        )
        await db.execute(
            "INSERT INTO robbery_log (telegram_id, target, success, reward, suspicion_gain) VALUES (?,?,?,?,?)",
            (req.telegram_id, req.robbery_id, int(success), reward, suspicion_gain),
        )
        await db.commit()

        # Mission hooks
        await advance_mission(db, req.telegram_id, "robbery")
        if success:
            await advance_mission(db, req.telegram_id, "robbery_success")

        player = await get_player(db, req.telegram_id)
        return {"success": success, "reward": reward, "suspicion_gain": suspicion_gain, "player": player}
    finally:
        await db.close()


# ── Casino ──

@app.post("/api/casino")
async def casino_play(req: CasinoBetRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        game_cfg = CASINO_GAMES.get(req.game)
        if not game_cfg: raise HTTPException(400, "Unknown game")
        if req.bet < game_cfg["min_bet"] or req.bet > game_cfg["max_bet"]:
            raise HTTPException(400, f"Bet must be {game_cfg['min_bet']}-{game_cfg['max_bet']}")
        if player["cash"] < req.bet:
            raise HTTPException(400, "Not enough cash")

        payout = 0
        result_data = {}

        if req.game == "coinflip":
            flip = random.choice(["heads", "tails"])
            win = flip == req.choice
            payout = req.bet * 2 if win else 0
            result_data = {"flip": flip, "win": win}

        elif req.game == "dice":
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)
            total = dice1 + dice2
            if req.choice == "over":
                win = total > 7
                payout = req.bet * 2 if win else 0
            elif req.choice == "under":
                win = total < 7
                payout = req.bet * 2 if win else 0
            elif req.choice == "seven":
                win = total == 7
                payout = req.bet * 5 if win else 0
            else:
                win = False
            result_data = {"dice1": dice1, "dice2": dice2, "total": total, "win": win}

        elif req.game == "slots":
            reels = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
            combo = "".join(reels)
            if combo in SLOT_PAYOUTS:
                payout = req.bet * SLOT_PAYOUTS[combo]
            elif reels[0] == reels[1] or reels[1] == reels[2]:
                payout = req.bet * SLOT_TWO_MATCH_PAYOUT
            else:
                payout = 0
            result_data = {"reels": reels, "win": payout > 0}

        elif req.game == "roulette":
            number = random.choice(ROULETTE_NUMBERS)
            win = False
            if req.choice == "red":
                win = number in ROULETTE_RED
                payout = req.bet * 2 if win else 0
            elif req.choice == "black":
                win = number in ROULETTE_BLACK
                payout = req.bet * 2 if win else 0
            elif req.choice == "even":
                win = number != 0 and number % 2 == 0
                payout = req.bet * 2 if win else 0
            elif req.choice == "odd":
                win = number % 2 == 1
                payout = req.bet * 2 if win else 0
            else:
                try:
                    chosen_num = int(req.choice)
                    win = number == chosen_num
                    payout = req.bet * 36 if win else 0
                except ValueError:
                    pass
            result_data = {"number": number, "win": win, "color": "red" if number in ROULETTE_RED else "black" if number in ROULETTE_BLACK else "green"}

        net = payout - req.bet
        new_cash = player["cash"] + net

        await db.execute("UPDATE players SET cash = ? WHERE telegram_id = ?", (new_cash, req.telegram_id))
        await db.execute(
            "INSERT INTO casino_log (telegram_id, game, bet, result, payout) VALUES (?,?,?,?,?)",
            (req.telegram_id, req.game, req.bet, str(result_data), payout),
        )
        await db.commit()

        # Mission hooks
        await advance_mission(db, req.telegram_id, "casino_play")
        if payout > 0:
            await advance_mission(db, req.telegram_id, "casino_win")

        player = await get_player(db, req.telegram_id)

        return {"payout": payout, "net": net, "result": result_data, "player": player}
    finally:
        await db.close()


# ── Shop & Character ──

@app.post("/api/shop/buy")
async def shop_buy(req: ShopBuyRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        item = SHOP_ITEMS.get(req.item_id)
        if not item: raise HTTPException(400, "Unknown item")
        if item.get("case_only"): raise HTTPException(400, "Only from cases")
        if player["cash"] < item["price"]: raise HTTPException(400, "Not enough cash")

        cursor = await db.execute("SELECT id FROM player_inventory WHERE telegram_id=? AND item_id=?", (req.telegram_id, req.item_id))
        if await cursor.fetchone(): raise HTTPException(400, "Already owned")

        await db.execute("UPDATE players SET cash = cash - ? WHERE telegram_id = ?", (item["price"], req.telegram_id))
        await db.execute("INSERT INTO player_inventory (telegram_id, item_id) VALUES (?, ?)", (req.telegram_id, req.item_id))
        await db.commit()

        # Mission hook
        await advance_mission(db, req.telegram_id, "shop_buy")

        player = await get_player(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)
        return {"player": player, "inventory": inventory}
    finally:
        await db.close()


@app.post("/api/shop/equip")
async def equip_item(req: EquipRequest):
    db = await get_db()
    try:
        item = SHOP_ITEMS.get(req.item_id)
        if not item: raise HTTPException(400, "Unknown item")

        cursor = await db.execute(
            "SELECT id FROM player_inventory WHERE telegram_id=? AND item_id=?",
            (req.telegram_id, req.item_id)
        )
        if not await cursor.fetchone():
            raise HTTPException(400, "Item not owned")

        inv = await get_inventory(db, req.telegram_id)
        for inv_item in inv:
            inv_cfg = SHOP_ITEMS.get(inv_item["item_id"])
            if inv_cfg and inv_cfg["slot"] == item["slot"] and inv_item["equipped"]:
                await db.execute("UPDATE player_inventory SET equipped=0 WHERE id=?", (inv_item["id"],))

        await db.execute(
            "UPDATE player_inventory SET equipped=1 WHERE telegram_id=? AND item_id=?",
            (req.telegram_id, req.item_id)
        )

        allowed_slots = ("hat", "jacket", "accessory", "weapon", "car")
        slot = item["slot"]
        if slot in allowed_slots:
            await db.execute(
                f"UPDATE player_character SET {slot}=? WHERE telegram_id=?",
                (req.item_id, req.telegram_id)
            )
        await db.commit()

        character = await get_character(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)
        return {"character": character, "inventory": inventory}
    finally:
        await db.close()


@app.get("/api/character/{telegram_id}")
async def get_character_info(telegram_id: int):
    db = await get_db()
    try:
        character = await get_character(db, telegram_id)
        inventory = await get_inventory(db, telegram_id)
        return {"character": character, "inventory": inventory}
    finally:
        await db.close()


# ── Cases ──

@app.post("/api/case/buy")
async def buy_case(req: CaseBuyRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        case_cfg = CASES.get(req.case_id)
        if not case_cfg: raise HTTPException(400, "Unknown case")
        if player["cash"] < case_cfg["price"]: raise HTTPException(400, "Not enough cash")

        await db.execute("UPDATE players SET cash = cash - ? WHERE telegram_id = ?", (case_cfg["price"], req.telegram_id))
        await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?, ?)", (req.telegram_id, req.case_id))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)
        return {"player": player, "player_cases": player_cases}
    finally:
        await db.close()


@app.post("/api/case/open")
async def open_case(req: CaseOpenRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")

        # Find the case in player's inventory
        cursor = await db.execute(
            "SELECT * FROM player_cases WHERE id=? AND telegram_id=?",
            (req.player_case_id, req.telegram_id)
        )
        pc = await cursor.fetchone()
        if not pc: raise HTTPException(400, "Case not found")
        pc = dict(pc)

        case_cfg = CASES.get(pc["case_id"])
        if not case_cfg: raise HTTPException(400, "Invalid case")

        # Get owned items to avoid duplicates
        inventory = await get_inventory(db, req.telegram_id)
        owned_ids = {i["item_id"] for i in inventory}

        # Weighted random selection, re-roll on duplicate
        loot = case_cfg["loot"]
        items = [l["item_id"] for l in loot]
        weights = [l["weight"] for l in loot]

        won_item_id = None
        cash_compensation = 0

        for _ in range(20):  # max 20 re-rolls
            chosen = random.choices(items, weights=weights, k=1)[0]
            if chosen not in owned_ids:
                won_item_id = chosen
                break

        if won_item_id:
            await db.execute("INSERT INTO player_inventory (telegram_id, item_id) VALUES (?, ?)", (req.telegram_id, won_item_id))
        else:
            # All items owned — give cash compensation
            chosen = random.choices(items, weights=weights, k=1)[0]
            item_cfg = SHOP_ITEMS.get(chosen, {})
            rarity = item_cfg.get("rarity", "common")
            rarity_mult = {"common": 1, "uncommon": 2, "rare": 4, "epic": 8, "legendary": 20}
            cash_compensation = case_cfg["price"] * 0.5 * rarity_mult.get(rarity, 1)
            await db.execute("UPDATE players SET cash = cash + ? WHERE telegram_id = ?", (cash_compensation, req.telegram_id))

        # Remove the case
        await db.execute("DELETE FROM player_cases WHERE id=?", (req.player_case_id,))
        await db.commit()

        # Mission hook
        await advance_mission(db, req.telegram_id, "case_open")

        player = await get_player(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)

        won_item = SHOP_ITEMS.get(won_item_id, {}) if won_item_id else None

        return {
            "player": player,
            "inventory": inventory,
            "player_cases": player_cases,
            "won_item_id": won_item_id,
            "won_item": won_item,
            "cash_compensation": cash_compensation,
        }
    finally:
        await db.close()


@app.post("/api/case/spin")
async def spin_case(req: CaseSpinRequest):
    """Buy + open case in one action."""
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        case_cfg = CASES.get(req.case_id)
        if not case_cfg: raise HTTPException(400, "Unknown case")
        if player["cash"] < case_cfg["price"]: raise HTTPException(400, "Not enough cash")

        # Deduct cash
        await db.execute("UPDATE players SET cash = cash - ? WHERE telegram_id = ?", (case_cfg["price"], req.telegram_id))

        # Get owned items to avoid duplicates
        inventory = await get_inventory(db, req.telegram_id)
        owned_ids = {i["item_id"] for i in inventory}

        # Weighted random selection
        loot = case_cfg["loot"]
        items = [l["item_id"] for l in loot]
        weights = [l["weight"] for l in loot]

        won_item_id = None
        cash_compensation = 0

        for _ in range(20):
            chosen = random.choices(items, weights=weights, k=1)[0]
            if chosen not in owned_ids:
                won_item_id = chosen
                break

        if won_item_id:
            await db.execute("INSERT INTO player_inventory (telegram_id, item_id) VALUES (?, ?)", (req.telegram_id, won_item_id))
        else:
            chosen = random.choices(items, weights=weights, k=1)[0]
            item_cfg = SHOP_ITEMS.get(chosen, {})
            rarity = item_cfg.get("rarity", "common")
            rarity_mult = {"common": 1, "uncommon": 2, "rare": 4, "epic": 8, "legendary": 20}
            cash_compensation = case_cfg["price"] * 0.5 * rarity_mult.get(rarity, 1)
            await db.execute("UPDATE players SET cash = cash + ? WHERE telegram_id = ?", (cash_compensation, req.telegram_id))

        await db.commit()
        await advance_mission(db, req.telegram_id, "case_open")

        player = await get_player(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)
        won_item = SHOP_ITEMS.get(won_item_id, {}) if won_item_id else None

        return {
            "player": player,
            "inventory": inventory,
            "player_cases": player_cases,
            "won_item_id": won_item_id,
            "won_item": won_item,
            "cash_compensation": cash_compensation,
        }
    finally:
        await db.close()


# ── Market ──

@app.post("/api/market/sell")
async def market_sell(req: MarketListRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        if req.price < 100: raise HTTPException(400, "Min price is $100")

        # Check owns item and not equipped
        cursor = await db.execute(
            "SELECT * FROM player_inventory WHERE telegram_id=? AND item_id=?",
            (req.telegram_id, req.item_id)
        )
        inv = await cursor.fetchone()
        if not inv: raise HTTPException(400, "Item not owned")
        if inv["equipped"]: raise HTTPException(400, "Unequip first")

        # Check not already listed
        cursor = await db.execute(
            "SELECT id FROM market_listings WHERE seller_id=? AND item_id=?",
            (req.telegram_id, req.item_id)
        )
        if await cursor.fetchone(): raise HTTPException(400, "Already listed")

        # Remove from inventory, add to market
        await db.execute("DELETE FROM player_inventory WHERE telegram_id=? AND item_id=?", (req.telegram_id, req.item_id))
        await db.execute(
            "INSERT INTO market_listings (seller_id, item_id, price) VALUES (?, ?, ?)",
            (req.telegram_id, req.item_id, req.price)
        )

        # Update character if was equipped in slot
        item_cfg = SHOP_ITEMS.get(req.item_id)
        if item_cfg:
            slot = item_cfg["slot"]
            if slot in ("hat", "jacket", "accessory", "weapon", "car"):
                await db.execute(f"UPDATE player_character SET {slot}='none' WHERE telegram_id=? AND {slot}=?", (req.telegram_id, req.item_id))

        await db.commit()

        inventory = await get_inventory(db, req.telegram_id)
        cursor = await db.execute("SELECT * FROM market_listings WHERE seller_id=?", (req.telegram_id,))
        my_listings = [dict(r) for r in await cursor.fetchall()]

        return {"inventory": inventory, "my_listings": my_listings}
    finally:
        await db.close()


@app.post("/api/market/buy")
async def market_buy(req: MarketBuyRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned_biz = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned_biz)

        cursor = await db.execute("SELECT * FROM market_listings WHERE id=?", (req.listing_id,))
        listing = await cursor.fetchone()
        if not listing: raise HTTPException(400, "Listing not found")
        listing = dict(listing)

        if listing["seller_id"] == req.telegram_id: raise HTTPException(400, "Can't buy own listing")
        if player["cash"] < listing["price"]: raise HTTPException(400, "Not enough cash")

        # Check buyer doesn't already own this item
        cursor = await db.execute(
            "SELECT id FROM player_inventory WHERE telegram_id=? AND item_id=?",
            (req.telegram_id, listing["item_id"])
        )
        if await cursor.fetchone(): raise HTTPException(400, "Already own this item")

        # Transfer — VIP gets reduced commission
        seller = await get_player(db, listing["seller_id"])
        commission = VIP_MARKET_COMMISSION if (seller and is_vip_active(seller)) else MARKET_COMMISSION
        seller_gets = listing["price"] * (1 - commission)
        await db.execute("UPDATE players SET cash = cash - ? WHERE telegram_id = ?", (listing["price"], req.telegram_id))
        await db.execute("UPDATE players SET cash = cash + ? WHERE telegram_id = ?", (seller_gets, listing["seller_id"]))
        await db.execute("INSERT INTO player_inventory (telegram_id, item_id) VALUES (?, ?)", (req.telegram_id, listing["item_id"]))
        await db.execute("DELETE FROM market_listings WHERE id=?", (req.listing_id,))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)

        return {"player": player, "inventory": inventory, "bought_item_id": listing["item_id"]}
    finally:
        await db.close()


@app.post("/api/market/cancel")
async def market_cancel(req: MarketListRequest):
    """Cancel a listing — return item to inventory."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM market_listings WHERE seller_id=? AND item_id=?",
            (req.telegram_id, req.item_id)
        )
        listing = await cursor.fetchone()
        if not listing: raise HTTPException(400, "Listing not found")

        await db.execute("DELETE FROM market_listings WHERE id=?", (listing["id"],))
        await db.execute(
            "INSERT OR IGNORE INTO player_inventory (telegram_id, item_id) VALUES (?, ?)",
            (req.telegram_id, req.item_id)
        )
        await db.commit()

        inventory = await get_inventory(db, req.telegram_id)
        cursor = await db.execute("SELECT * FROM market_listings WHERE seller_id=?", (req.telegram_id,))
        my_listings = [dict(r) for r in await cursor.fetchall()]

        return {"inventory": inventory, "my_listings": my_listings}
    finally:
        await db.close()


@app.get("/api/market")
async def get_market():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT ml.*, p.username as seller_name FROM market_listings ml JOIN players p ON p.telegram_id=ml.seller_id ORDER BY ml.created_at DESC LIMIT 100"
        )
        listings = [dict(r) for r in await cursor.fetchall()]
        return {"listings": listings}
    finally:
        await db.close()


# ── Gangs ──

@app.post("/api/gang/create")
async def create_gang(req: GangCreateRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        if player["gang_id"]: raise HTTPException(400, "Already in a gang")
        if len(req.name) < 2 or len(req.tag) < 1: raise HTTPException(400, "Invalid name/tag")

        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)
        creation_cost = 10000
        if player["cash"] < creation_cost: raise HTTPException(400, "Need $10,000 to create a gang")

        cursor = await db.execute(
            "INSERT INTO gangs (name, tag, leader_id) VALUES (?, ?, ?)",
            (req.name, req.tag, req.telegram_id),
        )
        gang_id = cursor.lastrowid
        await db.execute("INSERT INTO gang_members (telegram_id, gang_id, role) VALUES (?, ?, 'leader')", (req.telegram_id, gang_id))
        await db.execute("UPDATE players SET gang_id=?, cash=cash-? WHERE telegram_id=?", (gang_id, creation_cost, req.telegram_id))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        return {"player": player, "gang_id": gang_id, "gang_name": req.name}
    finally:
        await db.close()


@app.post("/api/gang/join")
async def join_gang(req: GangJoinRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        if player["gang_id"]: raise HTTPException(400, "Already in a gang")

        cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (req.gang_id,))
        gang = await cursor.fetchone()
        if not gang: raise HTTPException(404, "Gang not found")

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM gang_members WHERE gang_id=?", (req.gang_id,))
        count = (await cursor.fetchone())["cnt"]
        if count >= 20: raise HTTPException(400, "Gang is full")

        await db.execute("INSERT INTO gang_members (telegram_id, gang_id) VALUES (?, ?)", (req.telegram_id, req.gang_id))
        await db.execute("UPDATE players SET gang_id=? WHERE telegram_id=?", (req.gang_id, req.telegram_id))
        await db.execute("UPDATE gangs SET power=power+1 WHERE id=?", (req.gang_id,))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        return {"player": player, "gang": dict(gang)}
    finally:
        await db.close()


@app.get("/api/gangs")
async def list_gangs():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT g.*, COUNT(gm.telegram_id) as members FROM gangs g LEFT JOIN gang_members gm ON g.id=gm.gang_id GROUP BY g.id ORDER BY g.power DESC LIMIT 50")
        gangs = [dict(r) for r in await cursor.fetchall()]
        return {"gangs": gangs}
    finally:
        await db.close()


@app.get("/api/gang/{gang_id}")
async def get_gang(gang_id: int):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (gang_id,))
        gang = await cursor.fetchone()
        if not gang: raise HTTPException(404, "Not found")
        cursor = await db.execute(
            "SELECT p.telegram_id, p.username, gm.role FROM gang_members gm JOIN players p ON p.telegram_id=gm.telegram_id WHERE gm.gang_id=?",
            (gang_id,)
        )
        members = [dict(r) for r in await cursor.fetchall()]
        return {"gang": dict(gang), "members": members}
    finally:
        await db.close()


# ── PvP ──

@app.post("/api/pvp/attack")
async def pvp_attack(req: PvpAttackRequest):
    db = await get_db()
    try:
        attacker = await get_player(db, req.telegram_id)
        if not attacker: raise HTTPException(404, "Player not found")
        defender = await get_player(db, req.target_id)
        if not defender: raise HTTPException(404, "Target not found")
        if req.telegram_id == req.target_id: raise HTTPException(400, "Can't attack yourself")
        if attacker["cash"] < PVP_MIN_CASH_TO_ATTACK: raise HTTPException(400, "Need more cash")

        a_owned = await get_owned_businesses(db, req.telegram_id)
        d_owned = await get_owned_businesses(db, req.target_id)
        attacker, _ = await sync_earnings(db, attacker, a_owned)
        defender, _ = await sync_earnings(db, defender, d_owned)

        a_power = get_player_level(a_owned) + attacker["reputation_fear"]
        d_power = get_player_level(d_owned) + defender["reputation_fear"] + defender["reputation_respect"]

        a_roll = a_power + random.randint(0, 20)
        d_roll = d_power + random.randint(0, 20)

        win = a_roll > d_roll
        if win:
            steal = defender["cash"] * PVP_STEAL_PERCENT
            steal = min(steal, 50000)
            await db.execute("UPDATE players SET cash=cash+?, pvp_wins=pvp_wins+1 WHERE telegram_id=?", (steal, req.telegram_id))
            await db.execute("UPDATE players SET cash=cash-? WHERE telegram_id=?", (steal, req.target_id))
            winner_id = req.telegram_id
        else:
            steal = attacker["cash"] * (PVP_STEAL_PERCENT * 0.5)
            steal = min(steal, 25000)
            await db.execute("UPDATE players SET cash=cash-? WHERE telegram_id=?", (steal, req.telegram_id))
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (steal, req.target_id))
            winner_id = req.target_id

        await db.execute(
            "INSERT INTO pvp_log (attacker_id, defender_id, winner_id, cash_stolen) VALUES (?,?,?,?)",
            (req.telegram_id, req.target_id, winner_id, steal),
        )
        await db.commit()

        # Mission hooks
        await advance_mission(db, req.telegram_id, "pvp_attack")
        if win:
            await advance_mission(db, req.telegram_id, "pvp_win")

        attacker = await get_player(db, req.telegram_id)

        return {
            "win": win,
            "cash_stolen": round(steal, 2),
            "your_power": a_power,
            "their_power": d_power,
            "player": attacker,
        }
    finally:
        await db.close()


# ── Upgrades ──

@app.post("/api/upgrade")
async def buy_upgrade(req: UpgradeRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        cfg = UPGRADES.get(req.upgrade_id)
        if not cfg: raise HTTPException(400, "Unknown upgrade")

        upgrades = await get_upgrades(db, req.telegram_id)
        existing = next((u for u in upgrades if u["upgrade_id"] == req.upgrade_id), None)
        current_level = existing["level"] if existing else 0
        cost = cfg["base_cost"] * (cfg["cost_multiplier"] ** current_level)

        if player["cash"] < cost: raise HTTPException(400, "Not enough cash")

        new_cash = player["cash"] - cost

        if existing:
            await db.execute("UPDATE player_upgrades SET level=? WHERE id=?", (current_level + 1, existing["id"]))
        else:
            await db.execute("INSERT INTO player_upgrades (telegram_id, upgrade_id, level) VALUES (?,?,1)", (req.telegram_id, req.upgrade_id))

        effect = cfg["effect"]
        if effect == "suspicion_reset":
            await db.execute("UPDATE players SET cash=?, suspicion=0 WHERE telegram_id=?", (new_cash, req.telegram_id))
        elif effect == "income_boost_10":
            await db.execute("UPDATE players SET cash=?, reputation_respect=reputation_respect+5, reputation_fear=reputation_fear+5 WHERE telegram_id=?", (new_cash, req.telegram_id))
        elif effect == "territory":
            await db.execute("UPDATE players SET cash=?, reputation_respect=reputation_respect+3, reputation_fear=reputation_fear+3 WHERE telegram_id=?", (new_cash, req.telegram_id))
        elif effect == "pvp_defense":
            await db.execute("UPDATE players SET cash=?, reputation_respect=reputation_respect+5 WHERE telegram_id=?", (new_cash, req.telegram_id))
        else:
            await db.execute("UPDATE players SET cash=? WHERE telegram_id=?", (new_cash, req.telegram_id))

        await db.commit()
        player = await get_player(db, req.telegram_id)
        upgrades = await get_upgrades(db, req.telegram_id)
        return {"player": player, "upgrades": upgrades}
    finally:
        await db.close()


@app.get("/api/pvp/targets/{telegram_id}")
async def pvp_targets(telegram_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT telegram_id, username, reputation_fear, reputation_respect FROM players WHERE telegram_id != ? ORDER BY RANDOM() LIMIT 5",
            (telegram_id,),
        )
        targets = [dict(r) for r in await cursor.fetchall()]
        return {"targets": targets}
    finally:
        await db.close()


# ── Leaderboard ──

@app.get("/api/leaderboard")
async def leaderboard():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT telegram_id, username, cash, total_earned, reputation_fear, reputation_respect FROM players ORDER BY total_earned DESC LIMIT 20")
        players = [dict(r) for r in await cursor.fetchall()]
        return {"leaderboard": players}
    finally:
        await db.close()


# ── Mission Claim ──

@app.post("/api/mission/claim")
async def claim_mission(req: MissionClaimRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM daily_missions WHERE id=? AND telegram_id=?",
            (req.mission_id, req.telegram_id),
        )
        mission = await cursor.fetchone()
        if not mission: raise HTTPException(400, "Mission not found")
        mission = dict(mission)
        if not mission["completed"]: raise HTTPException(400, "Not completed")
        if mission["claimed"]: raise HTTPException(400, "Already claimed")

        await db.execute("UPDATE daily_missions SET claimed=1 WHERE id=?", (mission["id"],))
        await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (mission["reward"], req.telegram_id))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        missions = await get_daily_missions(db, req.telegram_id)
        return {"player": player, "daily_missions": missions}
    finally:
        await db.close()


# ── Login Claim ──

@app.post("/api/login/claim")
async def claim_login(req: LoginClaimRequest):
    db = await get_db()
    try:
        login_data = await check_login_streak(db, req.telegram_id)
        if not login_data["can_claim"]:
            raise HTTPException(400, "Already claimed today")

        new_streak = login_data["streak"]
        reward_day = login_data["reward_day"]
        day = today_utc()

        # Update streak
        await db.execute(
            "UPDATE daily_login SET streak=?, last_claim_date=? WHERE telegram_id=?",
            (new_streak, day, req.telegram_id),
        )

        reward_cfg = LOGIN_REWARDS[reward_day - 1]
        reward_text = reward_cfg["label"]

        if reward_cfg["type"] == "cash":
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (reward_cfg["amount"], req.telegram_id))
        elif reward_cfg["type"] == "case":
            await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?,?)", (req.telegram_id, reward_cfg["case_id"]))

        await db.commit()
        player = await get_player(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)

        return {
            "player": player,
            "player_cases": player_cases,
            "reward_text": reward_text,
            "reward_day": reward_day,
            "streak": new_streak,
            "login_data": {"can_claim": False, "streak": new_streak, "reward_day": reward_day},
        }
    finally:
        await db.close()


# ── Prestige ──

@app.post("/api/prestige")
async def do_prestige(req: PrestigeRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        current_prestige = player.get("prestige_level", 0)
        required_level = PRESTIGE_CONFIG["base_level_required"] + current_prestige * PRESTIGE_CONFIG["level_increment"]
        player_level = get_player_level(owned)

        if player_level < required_level:
            raise HTTPException(400, f"Need level {required_level}")

        new_prestige = current_prestige + 1
        new_multiplier = 1.0 + new_prestige * PRESTIGE_CONFIG["multiplier_bonus"]

        # Reset businesses, cash, reputation — keep items, gang, prestige
        await db.execute("DELETE FROM player_businesses WHERE telegram_id=?", (req.telegram_id,))
        await db.execute("DELETE FROM player_upgrades WHERE telegram_id=?", (req.telegram_id,))
        await db.execute(
            "UPDATE players SET cash=1000, suspicion=0, reputation_fear=0, reputation_respect=0, "
            "total_earned=0, total_robberies=0, robbery_cooldown_ts=0, "
            "prestige_level=?, prestige_multiplier=? WHERE telegram_id=?",
            (new_prestige, new_multiplier, req.telegram_id),
        )
        await db.commit()

        player = await get_player(db, req.telegram_id)
        owned = await get_owned_businesses(db, req.telegram_id)
        return {
            "player": player,
            "businesses": owned,
            "prestige_level": new_prestige,
            "prestige_multiplier": new_multiplier,
            "income_per_sec": 0,
            "suspicion_per_sec": 0,
            "player_level": 0,
        }
    finally:
        await db.close()


# ── Territories ──

@app.get("/api/territories")
async def get_territories():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, g.name as gang_name, g.tag as gang_tag FROM territories t LEFT JOIN gangs g ON g.id=t.owner_gang_id"
        )
        territories = [dict(r) for r in await cursor.fetchall()]
        return {"territories": territories}
    finally:
        await db.close()


@app.post("/api/territory/attack")
async def territory_attack(req: TerritoryAttackRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        if not player["gang_id"]: raise HTTPException(400, "Not in a gang")

        # Check role
        cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
        member = await cursor.fetchone()
        if not member or member["role"] not in ("leader", "officer"):
            raise HTTPException(400, "Only leader/officer can attack")

        # Check cooldown
        cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (player["gang_id"],))
        gang = await cursor.fetchone()
        if not gang: raise HTTPException(400, "Gang not found")
        gang = dict(gang)

        now = time.time()
        if gang.get("last_territory_attack_ts", 0) + TERRITORY_ATTACK_COOLDOWN > now:
            remaining = int(gang["last_territory_attack_ts"] + TERRITORY_ATTACK_COOLDOWN - now)
            raise HTTPException(400, f"Cooldown: {remaining}s")

        # Get territory
        cursor = await db.execute("SELECT * FROM territories WHERE id=?", (req.territory_id,))
        territory = await cursor.fetchone()
        if not territory: raise HTTPException(400, "Territory not found")
        territory = dict(territory)

        if territory["owner_gang_id"] == player["gang_id"]:
            raise HTTPException(400, "Already own this territory")

        # Calculate attacker strength
        cursor = await db.execute(
            "SELECT SUM(pb.level) as total_level FROM gang_members gm JOIN player_businesses pb ON pb.telegram_id=gm.telegram_id WHERE gm.gang_id=?",
            (player["gang_id"],),
        )
        atk_row = await cursor.fetchone()
        atk_level = (atk_row["total_level"] or 0) if atk_row else 0
        atk_power = atk_level + gang["power"] + random.randint(0, 30)

        # Defender strength
        def_power = 0
        defender_gang_id = territory["owner_gang_id"]
        if defender_gang_id:
            cursor = await db.execute(
                "SELECT SUM(pb.level) as total_level FROM gang_members gm JOIN player_businesses pb ON pb.telegram_id=gm.telegram_id WHERE gm.gang_id=?",
                (defender_gang_id,),
            )
            def_row = await cursor.fetchone()
            def_level = (def_row["total_level"] or 0) if def_row else 0
            cursor = await db.execute("SELECT power FROM gangs WHERE id=?", (defender_gang_id,))
            def_gang = await cursor.fetchone()
            def_gang_power = def_gang["power"] if def_gang else 0
            def_power = def_level + def_gang_power + 10 + random.randint(0, 30)  # +10 defender bonus

        win = atk_power > def_power

        # Update cooldown
        await db.execute("UPDATE gangs SET last_territory_attack_ts=? WHERE id=?", (now, player["gang_id"]))

        if win:
            await db.execute(
                "UPDATE territories SET owner_gang_id=?, captured_at=? WHERE id=?",
                (player["gang_id"], now, req.territory_id),
            )

        # Log
        await db.execute(
            "INSERT INTO territory_wars_log (territory_id, attacker_gang_id, defender_gang_id, winner_gang_id, attacker_power, defender_power) VALUES (?,?,?,?,?,?)",
            (req.territory_id, player["gang_id"], defender_gang_id, player["gang_id"] if win else defender_gang_id, atk_power, def_power),
        )
        await db.commit()

        # Fetch updated territories
        cursor = await db.execute(
            "SELECT t.*, g.name as gang_name, g.tag as gang_tag FROM territories t LEFT JOIN gangs g ON g.id=t.owner_gang_id"
        )
        territories = [dict(r) for r in await cursor.fetchall()]

        return {
            "win": win,
            "territory_name": territory["name"],
            "attacker_power": atk_power,
            "defender_power": def_power,
            "territories": territories,
        }
    finally:
        await db.close()


# ── Achievements ──

@app.get("/api/achievements/{telegram_id}")
async def get_achievements(telegram_id: int):
    db = await get_db()
    try:
        await check_achievements(db, telegram_id)
        achievements = await get_player_achievements(db, telegram_id)
        return {"achievements": achievements, "achievements_config": ACHIEVEMENTS}
    finally:
        await db.close()


@app.post("/api/achievement/claim")
async def claim_achievement(req: AchievementClaimRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM player_achievements WHERE telegram_id=? AND achievement_id=?",
            (req.telegram_id, req.achievement_id),
        )
        ach = await cursor.fetchone()
        if not ach: raise HTTPException(400, "Achievement not unlocked")
        ach = dict(ach)
        if ach["claimed"]: raise HTTPException(400, "Already claimed")

        ach_cfg = next((a for a in ACHIEVEMENTS if a["id"] == req.achievement_id), None)
        if not ach_cfg: raise HTTPException(400, "Unknown achievement")

        await db.execute("UPDATE player_achievements SET claimed=1 WHERE id=?", (ach["id"],))
        await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (ach_cfg["reward"], req.telegram_id))
        await db.commit()

        player = await get_player(db, req.telegram_id)
        achievements = await get_player_achievements(db, req.telegram_id)
        return {"player": player, "achievements": achievements}
    finally:
        await db.close()


# ── Ad Reward ──

@app.post("/api/ad/reward")
async def ad_reward(req: AdRewardRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")

        # VIP players don't need ads
        if is_vip_active(player):
            raise HTTPException(400, "VIP players don't need ads")

        now = time.time()
        last_ad = player.get("last_ad_ts", 0)
        if now - last_ad < AD_COOLDOWN:
            remaining = int(AD_COOLDOWN - (now - last_ad))
            raise HTTPException(400, f"Ad cooldown: {remaining}s")

        owned = await get_owned_businesses(db, req.telegram_id)
        player, _ = await sync_earnings(db, player, owned)

        result = {}

        if req.reward_type == "income_boost":
            boost_until = now + 300  # 5 minutes
            await db.execute(
                "UPDATE players SET last_ad_ts=?, ad_boost_until=? WHERE telegram_id=?",
                (now, boost_until, req.telegram_id),
            )
            result = {"type": "income_boost", "duration": 300, "message": "x2 доход на 5 минут!"}

        elif req.reward_type == "free_bet":
            await db.execute(
                "UPDATE players SET last_ad_ts=?, cash=cash+1000 WHERE telegram_id=?",
                (now, req.telegram_id),
            )
            result = {"type": "free_bet", "cash": 1000, "message": "+$1,000 для ставки!"}

        elif req.reward_type == "reset_cooldown":
            await db.execute(
                "UPDATE players SET last_ad_ts=?, robbery_cooldown_ts=0 WHERE telegram_id=?",
                (now, req.telegram_id),
            )
            result = {"type": "reset_cooldown", "message": "Кулдаун ограбления сброшен!"}

        else:
            raise HTTPException(400, "Unknown reward type")

        await db.commit()
        player = await get_player(db, req.telegram_id)
        return {"player": player, "reward": result}
    finally:
        await db.close()


# ── Stars Invoice ──

@app.post("/api/stars/invoice")
async def create_stars_invoice(req: StarsInvoiceRequest):
    """Create a Telegram Stars invoice link for a package."""
    # Find the package
    all_packages = {**VIP_PACKAGES, **CASH_PACKAGES, **CASE_PACKAGES}
    pkg = all_packages.get(req.package_id)
    if not pkg:
        raise HTTPException(400, "Unknown package")

    stars = pkg["stars"]
    label = pkg["label"]
    payload = json.dumps({"telegram_id": req.telegram_id, "package_id": req.package_id})

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink",
                json={
                    "title": f"Shadow Empire — {label}",
                    "description": label,
                    "payload": payload,
                    "currency": "XTR",
                    "prices": [{"label": label, "amount": stars}],
                },
            )
            data = resp.json()
            if data.get("ok"):
                return {"invoice_link": data["result"]}
            else:
                raise HTTPException(500, f"Telegram API error: {data.get('description', 'unknown')}")
    except httpx.HTTPError as e:
        raise HTTPException(500, f"Network error: {str(e)}")


# ── VIP Status ──

@app.get("/api/vip/status/{telegram_id}")
async def get_vip_status(telegram_id: int):
    db = await get_db()
    try:
        player = await get_player(db, telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        vip = is_vip_active(player)
        days_left = 0
        if vip:
            days_left = max(0, int((player.get("vip_until", 0) - time.time()) / 86400))
        return {
            "is_vip": vip,
            "vip_until": player.get("vip_until", 0),
            "days_left": days_left,
        }
    finally:
        await db.close()


# ── VIP Daily Case ──

@app.post("/api/vip/daily-case")
async def claim_vip_daily_case(req: VipDailyCaseRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        if not is_vip_active(player): raise HTTPException(400, "VIP not active")

        today = today_utc()
        if player.get("last_vip_case_claim", "") == today:
            raise HTTPException(400, "Already claimed today")

        # Give a premium case
        await db.execute(
            "INSERT INTO player_cases (telegram_id, case_id) VALUES (?, ?)",
            (req.telegram_id, "case_premium"),
        )
        await db.execute(
            "UPDATE players SET last_vip_case_claim=? WHERE telegram_id=?",
            (today, req.telegram_id),
        )
        await db.commit()

        player = await get_player(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)
        return {"player": player, "player_cases": player_cases, "message": "Бесплатный премиум кейс получен!"}
    finally:
        await db.close()


# ── VIP Item Claim ──

@app.post("/api/vip/claim-item")
async def claim_vip_item(req: VipItemClaimRequest):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")
        if not is_vip_active(player): raise HTTPException(400, "VIP not active")

        item = VIP_ITEMS.get(req.item_id)
        if not item: raise HTTPException(400, "Unknown VIP item")

        # Check if already owned
        cursor = await db.execute(
            "SELECT id FROM player_inventory WHERE telegram_id=? AND item_id=?",
            (req.telegram_id, req.item_id),
        )
        if await cursor.fetchone():
            raise HTTPException(400, "Already owned")

        await db.execute(
            "INSERT INTO player_inventory (telegram_id, item_id) VALUES (?, ?)",
            (req.telegram_id, req.item_id),
        )
        await db.commit()

        player = await get_player(db, req.telegram_id)
        inventory = await get_inventory(db, req.telegram_id)
        return {"player": player, "inventory": inventory, "item": item}
    finally:
        await db.close()


# ── TON Connect ──

@app.post("/api/ton/create")
async def ton_create_payment(req: TonCreateRequest):
    """Create a TON payment request — returns wallet address, amount, and comment."""
    all_packages = {**VIP_PACKAGES, **CASH_PACKAGES, **CASE_PACKAGES}
    pkg = all_packages.get(req.package_id)
    if not pkg:
        raise HTTPException(400, "Unknown package")

    ton_price = TON_PRICES.get(req.package_id)
    if ton_price is None:
        raise HTTPException(400, "TON price not set for this package")

    # Unique comment for this transaction
    comment = f"se_{req.telegram_id}_{req.package_id}_{uuid.uuid4().hex[:8]}"
    amount_nano = int(ton_price * 1e9)

    return {
        "address": TON_WALLET_ADDRESS,
        "amount_nano": amount_nano,
        "amount_ton": ton_price,
        "comment": comment,
        "package_id": req.package_id,
    }


@app.post("/api/ton/verify")
async def ton_verify_payment(req: TonVerifyRequest):
    """Verify a TON transaction and activate the purchase."""
    # In production, verify the transaction on-chain via TON API
    # For now, we trust the client and activate the purchase
    # TODO: Implement proper on-chain verification
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")

        # Check if tx_hash was already used
        cursor = await db.execute(
            "SELECT id FROM premium_transactions WHERE amount=? AND payment_method='ton'",
            (req.tx_hash,),
        )
        if await cursor.fetchone():
            raise HTTPException(400, "Transaction already processed")

        # For now return a pending status — real verification needs TON API
        return {"status": "pending", "message": "Transaction verification in progress. Contact support if not activated within 5 minutes."}
    finally:
        await db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
