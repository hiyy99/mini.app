"""
FastAPI backend for Shadow Empire game.
"""

import os
import json
import time
import math
import random
import hashlib
import hmac
import uuid
import urllib.parse
import asyncio
import base64
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
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
    ACHIEVEMENTS, ACHIEVEMENT_CATEGORIES, TIER_INFO, TERRITORY_ATTACK_COOLDOWN,
    VIP_PACKAGES, CASH_PACKAGES, CASE_PACKAGES, TON_PRICES,
    TON_WALLET_ADDRESS, VIP_ITEMS, VIP_MARKET_COMMISSION, AD_COOLDOWN,
    GANG_UPGRADES, GANG_CREATE_COST, GANG_MAX_MEMBERS,
    BUSINESS_SKINS, SKIN_RARITIES, SKIN_CASE, SKIN_CASE_VIP,
    TOURNAMENT_SCORE_EVENTS, TOURNAMENT_PRIZES,
    QUEST_LINES, SEASONAL_EVENTS, BOSSES, BOSS_ATTACK_COOLDOWN,
    TALENT_TREE, ALL_TALENTS,
    WEEKLY_EVENTS, GANG_HEISTS, GANG_WAR_CONFIG,
    PVP_WEAPON_RARITY_BONUS, PVP_DEFENSE_RARITY_BONUS,
    SEASON_PASS_XP_EVENTS, SEASON_PASS_CONFIG, SEASON_PASS_REWARDS,
)
from backend.game_logic import (
    calc_total_income, calc_offline_earnings, attempt_robbery,
    get_buy_cost, calc_manager_cost, get_player_level,
)

BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")


TELEGRAM_PUBLIC_KEY = Ed25519PublicKey.from_public_bytes(
    bytes.fromhex("e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d")
)

def validate_init_data(init_data: str) -> dict | None:
    """Validate Telegram WebApp initData using Ed25519 signature (Bot API 8.0+)."""
    if not init_data:
        return None
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    signature = parsed.pop("signature", "")
    parsed.pop("hash", "")
    if not signature:
        return None
    bot_id = BOT_TOKEN.split(":")[0]
    data_check_string = bot_id + ":WebAppData\n" + "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )
    try:
        sig_bytes = base64.urlsafe_b64decode(signature + "==")
        TELEGRAM_PUBLIC_KEY.verify(sig_bytes, data_check_string.encode("utf-8"))
    except Exception:
        return None
    user_data = parsed.get("user", "")
    if user_data:
        return json.loads(user_data)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Shadow Empire", lifespan=lifespan)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/static/index.html")


@app.post("/api/admin/cash")
async def admin_add_cash(req: dict):
    if not ADMIN_SECRET or req.get("secret") != ADMIN_SECRET:
        raise HTTPException(403, "Forbidden")
    tid = req.get("telegram_id")
    amount = req.get("amount", 0)
    async with get_player_lock(tid):
        db = await get_db()
        try:
            # Sync earnings first so we don't lose them
            player = await get_player(db, tid)
            if not player:
                raise HTTPException(404, "Player not found")
            owned = await get_owned_businesses(db, tid)
            await sync_earnings(db, player, owned)
            # Now safely add cash
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (amount, tid))
            await db.commit()
            cursor = await db.execute("SELECT cash FROM players WHERE telegram_id=?", (tid,))
            row = await cursor.fetchone()
            return {"telegram_id": tid, "cash": row["cash"] if row else None}
        finally:
            await db.close()


@app.post("/api/admin/players")
async def admin_list_players(req: dict):
    if not ADMIN_SECRET or req.get("secret") != ADMIN_SECRET:
        raise HTTPException(403, "Forbidden")
    db = await get_db()
    try:
        cursor = await db.execute("SELECT telegram_id, username, cash, prestige_level FROM players ORDER BY created_at DESC LIMIT 50")
        rows = [dict(r) for r in await cursor.fetchall()]
        return {"players": rows}
    finally:
        await db.close()


@app.post("/api/admin/reset")
async def admin_reset_player(req: dict):
    if not ADMIN_SECRET or req.get("secret") != ADMIN_SECRET:
        raise HTTPException(403, "Forbidden")
    tid = req.get("telegram_id")
    db = await get_db()
    try:
        for table in [
            "players", "player_businesses", "player_character", "player_inventory",
            "player_cases", "player_upgrades", "player_achievements", "player_talents",
            "player_skins", "business_equipped_skins", "daily_missions", "daily_login",
            "player_quests", "player_event_progress", "tournament_scores",
        ]:
            await db.execute(f"DELETE FROM {table} WHERE telegram_id=?", (tid,))
        await db.execute("DELETE FROM gang_members WHERE telegram_id=?", (tid,))
        await db.execute("DELETE FROM market_listings WHERE seller_id=?", (tid,))
        await db.commit()
        return {"status": "ok", "telegram_id": tid}
    finally:
        await db.close()


# ── Request Models ──

class PlayerInit(BaseModel):
    telegram_id: int
    username: str = ""
    referral_code: str = ""
    init_data: str = ""

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

class GangDepositRequest(BaseModel):
    telegram_id: int
    amount: float

class GangWithdrawRequest(BaseModel):
    telegram_id: int
    amount: float

class GangLeaveRequest(BaseModel):
    telegram_id: int

class GangKickRequest(BaseModel):
    telegram_id: int
    target_id: int

class GangUpgradeRequest(BaseModel):
    telegram_id: int
    upgrade_id: str

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
    comment: str = ""
    package_id: str = ""

class VipItemClaimRequest(BaseModel):
    telegram_id: int
    item_id: str

class SkinCaseOpenRequest(BaseModel):
    telegram_id: int
    case_type: str = "normal"  # normal | vip
    count: int = 1  # mass open (1-50)

class SkinEquipRequest(BaseModel):
    telegram_id: int
    business_id: str
    skin_id: str  # skin_id or "none" to unequip

class EventClaimRequest(BaseModel):
    telegram_id: int
    milestone_index: int

class SeasonClaimRequest(BaseModel):
    telegram_id: int
    level: int
    track: str  # "free" or "premium"

class BossAttackRequest(BaseModel):
    telegram_id: int
    gang_id: int

class TalentAssignRequest(BaseModel):
    telegram_id: int
    talent_id: str


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


# ── Per-player lock to prevent race conditions ──
_player_locks: dict[int, asyncio.Lock] = {}


def get_player_lock(tid: int) -> asyncio.Lock:
    if tid not in _player_locks:
        _player_locks[tid] = asyncio.Lock()
    return _player_locks[tid]


def validate_amount(val: float, name: str = "amount"):
    """Validate that a float value is finite and positive."""
    if not math.isfinite(val) or val <= 0:
        raise HTTPException(400, f"Invalid {name}")


async def sync_earnings(db, player, owned):
    """Sync accumulated earnings before any action — fixes balance bug."""
    now = time.time()
    territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))
    vip = is_vip_active(player)
    equip_inc = await get_equip_income_bonus(db, player["telegram_id"])
    upgrade_inc = await get_upgrade_income_bonus(db, player["telegram_id"])
    gang_inc, gang_raid_red = 0, 0
    if player.get("gang_id"):
        gang_ups = await get_gang_upgrades(db, player["gang_id"])
        gang_inc = get_gang_income_bonus(gang_ups)
        gang_raid_red = get_gang_raid_reduction(gang_ups)
    talents = await get_player_talents(db, player["telegram_id"])
    tb = get_talent_bonuses(talents)
    earnings, new_suspicion, was_raided = calc_offline_earnings(
        owned, player["last_collect_ts"], player["suspicion"],
        player["reputation_fear"], player["reputation_respect"],
        player.get("prestige_multiplier", 1.0), territory_bonus,
        is_vip=vip, equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
        gang_income_bonus=gang_inc, gang_raid_reduction=gang_raid_red,
        talent_offline_hours=tb["efficiency"], talent_raid_reduce=tb["evasion"],
        talent_income_bonus=tb["passive_income"], talent_suspicion_reduce=tb["shadow_talent"],
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
        item_id = character.get(slot)
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

async def get_player_talents(db, telegram_id):
    cursor = await db.execute("SELECT talent_id, level FROM player_talents WHERE telegram_id=?", (telegram_id,))
    return {r["talent_id"]: r["level"] for r in await cursor.fetchall()}

def get_talent_effect(talents, talent_id, per_level):
    return talents.get(talent_id, 0) * per_level

def get_talent_bonuses(talents):
    """Compute all talent bonuses from a talents dict {talent_id: level}."""
    return {
        "trade_grip": get_talent_effect(talents, "trade_grip", 3),
        "passive_income": get_talent_effect(talents, "passive_income", 3),
        "quick_start": get_talent_effect(talents, "quick_start", 2000),
        "efficiency": get_talent_effect(talents, "efficiency", 1),
        "robbery_master": get_talent_effect(talents, "robbery_master", 8),
        "big_loot": get_talent_effect(talents, "big_loot", 5),
        "intimidation": get_talent_effect(talents, "intimidation", 2),
        "street_fighter": get_talent_effect(talents, "street_fighter", 5),
        "lucky": get_talent_effect(talents, "lucky", 5000),
        "lootbox_master": get_talent_effect(talents, "lootbox_master", 3),
        "evasion": get_talent_effect(talents, "evasion", 5),
        "shadow_talent": get_talent_effect(talents, "shadow_talent", 5),
    }

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
        reward_day = ((streak - 1) % 30) + 1
        return {"can_claim": False, "streak": streak, "reward_day": reward_day}

    if last_claim == yest:
        new_streak = streak + 1
    else:
        new_streak = 1

    reward_day = ((new_streak - 1) % 30) + 1
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

    # Count skins
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM player_skins WHERE telegram_id=?", (tid,))
    skins_row = await cursor.fetchone()
    skins_count = skins_row["cnt"] if skins_row else 0

    # Count market sales
    market_sales = player.get("market_sales", 0)

    # Casino stats
    casino_plays = player.get("casino_plays", 0)
    casino_wins = player.get("casino_wins", 0)

    # Gang territories
    gang_territories = 0
    if player.get("gang_id"):
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM territories WHERE owner_gang_id=?", (player["gang_id"],))
        t_row = await cursor.fetchone()
        gang_territories = t_row["cnt"] if t_row else 0

    values = {
        "total_robberies": player.get("total_robberies", 0),
        "total_earned": player.get("total_earned", 0),
        "level": player_level,
        "inventory_count": inventory_count,
        "legendary_count": legendary_count,
        "gang_id": 1 if player.get("gang_id", 0) > 0 else 0,
        "gang_territories": gang_territories,
        "prestige_level": player.get("prestige_level", 0),
        "pvp_wins": player.get("pvp_wins", 0),
        "casino_plays": casino_plays,
        "casino_wins": casino_wins,
        "skins_count": skins_count,
        "market_sales": market_sales,
        "tournament_top10": player.get("tournament_top10", 0),
        "tournament_top3": player.get("tournament_top3", 0),
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


# ── Tournament (Daily) ──

async def advance_tournament(db, tid, event_type, amount=1):
    score = TOURNAMENT_SCORE_EVENTS.get(event_type, 0) * amount
    if score <= 0:
        return
    day = today_utc()
    await db.execute(
        "INSERT INTO tournament_scores (telegram_id, day, score) VALUES (?,?,?) "
        "ON CONFLICT(telegram_id, day) DO UPDATE SET score=score+?",
        (tid, day, score, score),
    )
    await db.commit()

async def check_and_distribute_tournament_prizes(db, tid):
    """Check yesterday's tournament and distribute prizes if not claimed."""
    yest = yesterday_utc()
    cursor = await db.execute(
        "SELECT id FROM tournament_prizes_log WHERE telegram_id=? AND day=?", (tid, yest)
    )
    if await cursor.fetchone():
        return None  # already claimed

    cursor = await db.execute(
        "SELECT telegram_id, score FROM tournament_scores WHERE day=? ORDER BY score DESC LIMIT 10",
        (yest,),
    )
    rows = await cursor.fetchall()
    place = 0
    for i, r in enumerate(rows):
        if r["telegram_id"] == tid:
            place = i + 1
            break
    if place == 0 or place > len(TOURNAMENT_PRIZES):
        return None

    prize = TOURNAMENT_PRIZES[place - 1]
    await db.execute(
        "UPDATE players SET cash=cash+? WHERE telegram_id=?", (prize["cash"], tid)
    )
    for _ in range(prize.get("cases", 0)):
        await db.execute(
            "INSERT INTO player_cases (telegram_id, case_id) VALUES (?, 'case_premium')", (tid,)
        )
    await db.execute(
        "INSERT OR IGNORE INTO tournament_prizes_log (telegram_id, day, place, cash_prize, cases_prize) VALUES (?,?,?,?,?)",
        (tid, yest, place, prize["cash"], prize.get("cases", 0)),
    )
    # Track for achievements
    if place <= 10:
        await db.execute("UPDATE players SET tournament_top10=tournament_top10+1 WHERE telegram_id=?", (tid,))
    if place <= 3:
        await db.execute("UPDATE players SET tournament_top3=tournament_top3+1 WHERE telegram_id=?", (tid,))
    await db.commit()
    return {"place": place, "prize": prize}


# ── Quests ──

async def init_quests(db, tid, player_level):
    """Create quest entries for available quest lines."""
    for ql in QUEST_LINES:
        if player_level >= ql["unlock_level"]:
            await db.execute(
                "INSERT OR IGNORE INTO player_quests (telegram_id, quest_id, current_step, step_progress) VALUES (?,?,0,0)",
                (tid, ql["id"]),
            )
    await db.commit()

async def get_player_quests(db, tid):
    cursor = await db.execute("SELECT * FROM player_quests WHERE telegram_id=?", (tid,))
    return [dict(r) for r in await cursor.fetchall()]

async def advance_quest(db, tid, trigger_type, amount=1):
    """Advance progress on active quests matching trigger_type."""
    quests = await get_player_quests(db, tid)
    for q in quests:
        if q["completed"]:
            continue
        ql = next((l for l in QUEST_LINES if l["id"] == q["quest_id"]), None)
        if not ql:
            continue
        step_idx = q["current_step"]
        if step_idx >= len(ql["steps"]):
            continue
        step = ql["steps"][step_idx]
        if step["trigger"] != trigger_type:
            continue
        new_progress = min(q["step_progress"] + amount, step["target"])
        if new_progress >= step["target"]:
            # Step completed — give reward
            if step["reward_type"] == "cash":
                await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (step["reward_amount"], tid))
            elif step["reward_type"] == "case":
                await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?,?)", (tid, step["reward_amount"]))
            # Move to next step or complete quest
            next_step = step_idx + 1
            completed = 1 if next_step >= len(ql["steps"]) else 0
            await db.execute(
                "UPDATE player_quests SET current_step=?, step_progress=0, completed=? WHERE telegram_id=? AND quest_id=?",
                (next_step, completed, tid, q["quest_id"]),
            )
        else:
            await db.execute(
                "UPDATE player_quests SET step_progress=? WHERE telegram_id=? AND quest_id=?",
                (new_progress, tid, q["quest_id"]),
            )
    await db.commit()


# ── Seasonal Events ──

def get_active_event():
    for ev in SEASONAL_EVENTS:
        if ev.get("active"):
            return ev
    return None

async def advance_event(db, tid, event_type, amount=1):
    ev = get_active_event()
    if not ev:
        return
    score = ev["score_events"].get(event_type, 0) * amount
    if score <= 0:
        return
    await db.execute(
        "INSERT INTO player_event_progress (telegram_id, event_id, progress) VALUES (?,?,?) "
        "ON CONFLICT(telegram_id, event_id) DO UPDATE SET progress=progress+?",
        (tid, ev["id"], score, score),
    )
    await db.commit()

async def get_event_progress(db, tid, event_id):
    cursor = await db.execute(
        "SELECT * FROM player_event_progress WHERE telegram_id=? AND event_id=?",
        (tid, event_id),
    )
    row = await cursor.fetchone()
    return dict(row) if row else {"progress": 0, "rewards_claimed": ""}

# ── Season Pass ──

def calc_season_level(xp):
    return min(xp // SEASON_PASS_CONFIG["xp_per_level"] + 1, SEASON_PASS_CONFIG["max_level"])

async def get_season_pass(db, tid):
    season_id = SEASON_PASS_CONFIG["id"]
    cursor = await db.execute(
        "SELECT * FROM player_season_pass WHERE telegram_id=? AND season_id=?",
        (tid, season_id),
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return {"telegram_id": tid, "season_id": season_id, "xp": 0, "is_premium": 0, "free_claimed": "", "premium_claimed": "", "purchased_at": 0}

async def advance_season_pass(db, tid, action_type, amount=1):
    xp = SEASON_PASS_XP_EVENTS.get(action_type, 0) * amount
    if xp <= 0:
        return
    season_id = SEASON_PASS_CONFIG["id"]
    await db.execute(
        "INSERT INTO player_season_pass (telegram_id, season_id, xp) VALUES (?,?,?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET xp=xp+?",
        (tid, season_id, xp, xp),
    )
    await db.commit()

def get_active_weekly_event():
    """Get the active weekly event based on current day of week (Mon=0, Sun=6)."""
    dow = datetime.now(timezone.utc).weekday()
    return WEEKLY_EVENTS.get(dow)

def get_event_income_multiplier():
    """Get income multiplier from seasonal event only (weekly events don't stack income)."""
    ev = get_active_event()
    if not ev:
        return 1.0
    return ev["bonuses"].get("income_multiplier", 1.0)


# ── Bosses ──

async def spawn_boss_for_gang(db, gang_id):
    """Spawn a boss for a gang if none exists or current is defeated."""
    cursor = await db.execute(
        "SELECT * FROM active_bosses WHERE gang_id=? AND defeated=0", (gang_id,)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    # Get next boss index
    cursor = await db.execute("SELECT boss_index FROM active_bosses WHERE gang_id=? ORDER BY spawned_at DESC LIMIT 1", (gang_id,))
    last = await cursor.fetchone()
    boss_index = ((last["boss_index"] + 1) if last else 0) % len(BOSSES)
    boss = BOSSES[boss_index]
    # Scale HP by gang member count
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM gang_members WHERE gang_id=?", (gang_id,))
    members = (await cursor.fetchone())["cnt"]
    max_hp = boss["base_hp"] + boss["hp_per_gang_level"] * members
    await db.execute(
        "INSERT OR REPLACE INTO active_bosses (gang_id, boss_id, current_health, max_health, defeated, boss_index) VALUES (?,?,?,?,0,?)",
        (gang_id, boss["id"], max_hp, max_hp, boss_index),
    )
    await db.commit()
    return {"gang_id": gang_id, "boss_id": boss["id"], "current_health": max_hp, "max_health": max_hp, "defeated": 0, "boss_index": boss_index}

def calc_attack_damage(player_level, fear, equip_bonus=0, armory_bonus=0):
    base = 50 + player_level * 5 + fear * 2 + equip_bonus + armory_bonus
    variance = random.uniform(0.8, 1.2)
    return round(base * variance)

async def distribute_boss_rewards(db, gang_id, boss_id):
    boss_cfg = next((b for b in BOSSES if b["id"] == boss_id), None)
    if not boss_cfg:
        return
    cursor = await db.execute(
        "SELECT telegram_id, SUM(damage) as total_dmg FROM boss_attack_log WHERE gang_id=? GROUP BY telegram_id",
        (gang_id,),
    )
    attackers = [dict(r) for r in await cursor.fetchall()]
    total_dmg = sum(a["total_dmg"] for a in attackers)
    if total_dmg <= 0:
        return
    for a in attackers:
        share = a["total_dmg"] / total_dmg
        cash_reward = round(boss_cfg["reward_pool"] * share)
        await db.execute("UPDATE players SET cash=cash+?, bosses_killed=bosses_killed+1 WHERE telegram_id=?", (cash_reward, a["telegram_id"]))
        await db.execute(
            "INSERT INTO boss_rewards_log (gang_id, boss_id, telegram_id, cash_reward) VALUES (?,?,?,?)",
            (gang_id, boss_id, a["telegram_id"], cash_reward),
        )
    # Clear attack log for this gang
    await db.execute("DELETE FROM boss_attack_log WHERE gang_id=?", (gang_id,))
    await db.commit()

async def get_boss_data(db, gang_id):
    cursor = await db.execute("SELECT * FROM active_bosses WHERE gang_id=? AND defeated=0", (gang_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    boss_data = dict(row)
    boss_cfg = next((b for b in BOSSES if b["id"] == boss_data["boss_id"]), None)
    if boss_cfg:
        boss_data["name"] = boss_cfg["name"]
        boss_data["emoji"] = boss_cfg["emoji"]
        boss_data["reward_pool"] = boss_cfg["reward_pool"]
    # Get attack log
    cursor = await db.execute(
        "SELECT bal.telegram_id, p.username, SUM(bal.damage) as total_dmg "
        "FROM boss_attack_log bal JOIN players p ON p.telegram_id=bal.telegram_id "
        "WHERE bal.gang_id=? GROUP BY bal.telegram_id ORDER BY total_dmg DESC LIMIT 20",
        (gang_id,),
    )
    boss_data["attackers"] = [dict(r) for r in await cursor.fetchall()]
    return boss_data


# ── Unified Action Tracker ──

async def track_action(db, tid, action_type, amount=1):
    """Central tracker — advances missions, tournament, events, and quests."""
    await advance_mission(db, tid, action_type, amount)
    await advance_tournament(db, tid, action_type, amount)
    await advance_event(db, tid, action_type, amount)
    await advance_quest(db, tid, action_type, amount)
    await advance_season_pass(db, tid, action_type, amount)


# ── Player Init ──

@app.post("/api/init")
async def player_init(req: PlayerInit):
    # Validate Telegram initData
    if req.init_data:
        user = validate_init_data(req.init_data)
        if not user or user.get("id") != req.telegram_id:
            raise HTTPException(403, "Invalid initData")
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
        gang_inc = 0
        if player.get("gang_id"):
            gang_ups = await get_gang_upgrades(db, player["gang_id"])
            gang_inc = get_gang_income_bonus(gang_ups)
        event_mult = get_event_income_multiplier()
        talents = await get_player_talents(db, req.telegram_id)
        tb = get_talent_bonuses(talents)
        income_per_sec, suspicion_per_sec = calc_total_income(
            owned, player["reputation_fear"], player["reputation_respect"],
            player.get("prestige_multiplier", 1.0), territory_bonus,
            vip_multiplier=vip_mult, ad_boost=ad_boost,
            equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
            gang_income_bonus=gang_inc, event_income_multiplier=event_mult,
            talent_income_bonus=tb["passive_income"], talent_suspicion_reduce=tb["shadow_talent"],
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

        # Tournament — check yesterday's prizes
        tournament_prize = await check_and_distribute_tournament_prizes(db, req.telegram_id)
        # Today's score
        cursor = await db.execute("SELECT score FROM tournament_scores WHERE telegram_id=? AND day=?", (req.telegram_id, today_utc()))
        ts_row = await cursor.fetchone()
        tournament_score = ts_row["score"] if ts_row else 0

        # Quests
        await init_quests(db, req.telegram_id, get_player_level(owned))
        player_quests = await get_player_quests(db, req.telegram_id)

        # Event
        active_event = get_active_event()
        event_progress = None
        if active_event:
            event_progress = await get_event_progress(db, req.telegram_id, active_event["id"])
        event_mult = get_event_income_multiplier()

        # Boss
        boss_data = None
        if player.get("gang_id"):
            await spawn_boss_for_gang(db, player["gang_id"])
            boss_data = await get_boss_data(db, player["gang_id"])

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
            # Skins
            "player_skins": await get_player_skins(db, req.telegram_id),
            "equipped_skins": await get_equipped_skins(db, req.telegram_id),
            "skins_config": BUSINESS_SKINS,
            "skin_rarities": SKIN_RARITIES,
            "skin_case": SKIN_CASE,
            "skin_case_vip": SKIN_CASE_VIP,
            # Tournament
            "tournament_score": tournament_score,
            "tournament_prize": tournament_prize,
            # Quests
            "player_quests": player_quests,
            "quest_lines": QUEST_LINES,
            # Event
            "active_event": active_event,
            "event_progress": event_progress,
            # Boss
            "boss_data": boss_data,
            # Achievements extended
            "achievement_categories": ACHIEVEMENT_CATEGORIES,
            "tier_info": TIER_INFO,
            # Talent Tree
            "talent_tree_config": TALENT_TREE,
            "player_talents": talents,
            "talent_points": player.get("talent_points", 0),
            # Weekly event
            "weekly_event": get_active_weekly_event(),
            # Gang heists config
            "gang_heists_config": GANG_HEISTS,
            # Gang war config
            "gang_war_config": GANG_WAR_CONFIG,
            # Season Pass
            "season_pass": await get_season_pass(db, req.telegram_id),
            "season_pass_config": SEASON_PASS_CONFIG,
            "season_pass_rewards": SEASON_PASS_REWARDS,
        }
    finally:
        await db.close()


# ── Business ──

@app.post("/api/buy")
async def buy_business(req: BuyRequest):
    async with get_player_lock(req.telegram_id):
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

            cash_before = player["cash"]
            existing = next((b for b in owned if b["business_id"] == req.business_id), None)
            current_level = existing["level"] if existing else 0
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            cost = get_buy_cost(req.business_id, max(current_level, 1), player["reputation_fear"], player["reputation_respect"], talent_discount=tb["trade_grip"])
            if player["cash"] < cost: raise HTTPException(400, "Not enough cash")

            new_cash = player["cash"] - cost
            if existing:
                await db.execute("UPDATE player_businesses SET level = ? WHERE id = ?", (existing["level"] + 1, existing["id"]))
            else:
                await db.execute("INSERT INTO player_businesses (telegram_id, business_id, level) VALUES (?, ?, 1)", (req.telegram_id, req.business_id))

            rep_col = "reputation_fear" if cfg["type"] == "shadow" else "reputation_respect"
            await db.execute(f"UPDATE players SET cash = ?, {rep_col} = {rep_col} + 1 WHERE telegram_id = ?", (new_cash, req.telegram_id))
            await db.commit()

            await track_action(db, req.telegram_id, "buy_business")

            player = await get_player(db, req.telegram_id)
            owned = await get_owned_businesses(db, req.telegram_id)
            territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))
            vip_mult = 2.0 if is_vip_active(player) else 1.0
            ad_boost = has_ad_boost(player)
            equip_inc = await get_equip_income_bonus(db, req.telegram_id)
            upgrade_inc = await get_upgrade_income_bonus(db, req.telegram_id)
            gang_inc = 0
            if player.get("gang_id"):
                gang_ups = await get_gang_upgrades(db, player["gang_id"])
                gang_inc = get_gang_income_bonus(gang_ups)
            event_mult = get_event_income_multiplier()
            income_per_sec, suspicion_per_sec = calc_total_income(
                owned, player["reputation_fear"], player["reputation_respect"],
                player.get("prestige_multiplier", 1.0), territory_bonus,
                vip_multiplier=vip_mult, ad_boost=ad_boost,
                equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
                gang_income_bonus=gang_inc, event_income_multiplier=event_mult,
                talent_income_bonus=tb["passive_income"], talent_suspicion_reduce=tb["shadow_talent"],
            )
            return {"player": player, "businesses": owned, "income_per_sec": income_per_sec, "suspicion_per_sec": suspicion_per_sec, "player_level": get_player_level(owned), "cash_before": cash_before}

        finally:
            await db.close()


@app.post("/api/manager")
async def hire_manager(req: ManagerRequest):
    async with get_player_lock(req.telegram_id):
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
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            owned = await get_owned_businesses(db, req.telegram_id)
            old_earned = player.get("total_earned", 0)
            player, was_raided = await sync_earnings(db, player, owned)
            new_earned = player.get("total_earned", 0)
            earnings = new_earned - old_earned

            if earnings > 0:
                await track_action(db, req.telegram_id, "earn_cash", int(earnings))

            territory_bonus = await get_territory_bonus(db, player.get("gang_id", 0))
            vip_mult = 2.0 if is_vip_active(player) else 1.0
            ad_boost = has_ad_boost(player)
            equip_inc = await get_equip_income_bonus(db, req.telegram_id)
            upgrade_inc = await get_upgrade_income_bonus(db, req.telegram_id)
            gang_inc = 0
            if player.get("gang_id"):
                gang_ups = await get_gang_upgrades(db, player["gang_id"])
                gang_inc = get_gang_income_bonus(gang_ups)
            event_mult = get_event_income_multiplier()
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            income_per_sec, suspicion_per_sec = calc_total_income(
                owned, player["reputation_fear"], player["reputation_respect"],
                player.get("prestige_multiplier", 1.0), territory_bonus,
                vip_multiplier=vip_mult, ad_boost=ad_boost,
                equip_income_bonus=equip_inc, upgrade_income_bonus=upgrade_inc,
                gang_income_bonus=gang_inc, event_income_multiplier=event_mult,
                talent_income_bonus=tb["passive_income"], talent_suspicion_reduce=tb["shadow_talent"],
            )
            return {"player": player, "was_raided": was_raided, "income_per_sec": income_per_sec, "suspicion_per_sec": suspicion_per_sec}

        finally:
            await db.close()


# ── Robbery ──

@app.post("/api/robbery")
async def do_robbery(req: RobberyRequest):
    async with get_player_lock(req.telegram_id):
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

            cash_before = player["cash"]
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            success, reward, suspicion_gain = attempt_robbery(req.robbery_id, player["reputation_fear"], reward_bonus_pct=tb["big_loot"])
            new_cash = player["cash"] + reward
            new_suspicion = min(player["suspicion"] + suspicion_gain, MAX_SUSPICION)
            actual_cd = max(5, cfg["cooldown_seconds"] * (1 - tb["robbery_master"] / 100.0))

            await db.execute(
                "UPDATE players SET cash=?, suspicion=?, robbery_cooldown_ts=?, reputation_fear=reputation_fear+2, total_robberies=total_robberies+1 WHERE telegram_id=?",
                (new_cash, new_suspicion, now + actual_cd, req.telegram_id),
            )
            await db.execute(
                "INSERT INTO robbery_log (telegram_id, target, success, reward, suspicion_gain) VALUES (?,?,?,?,?)",
                (req.telegram_id, req.robbery_id, int(success), reward, suspicion_gain),
            )
            await db.commit()

            await track_action(db, req.telegram_id, "robbery")
            if success:
                await track_action(db, req.telegram_id, "robbery_success")

            player = await get_player(db, req.telegram_id)
            return {"success": success, "reward": reward, "suspicion_gain": suspicion_gain, "player": player, "cash_before": cash_before}

        finally:
            await db.close()


# ── Casino ──

@app.post("/api/casino")
async def casino_play(req: CasinoBetRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            owned = await get_owned_businesses(db, req.telegram_id)
            player, _ = await sync_earnings(db, player, owned)

            game_cfg = CASINO_GAMES.get(req.game)
            if not game_cfg: raise HTTPException(400, "Unknown game")
            validate_amount(req.bet, "bet")
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            effective_max_bet = game_cfg["max_bet"] + tb["lucky"]
            if req.bet < game_cfg["min_bet"] or req.bet > effective_max_bet:
                raise HTTPException(400, f"Bet must be {game_cfg['min_bet']}-{effective_max_bet}")
            if player["cash"] < req.bet:
                raise HTTPException(400, "Not enough cash")

            payout = 0
            result_data = {}

            if req.game == "coinflip":
                if req.choice not in ("heads", "tails"):
                    raise HTTPException(400, "Choice must be heads or tails")
                flip = random.choice(["heads", "tails"])
                win = flip == req.choice
                payout = req.bet * 2 if win else 0
                result_data = {"flip": flip, "win": win}

            elif req.game == "dice":
                if req.choice not in ("over", "under", "seven"):
                    raise HTTPException(400, "Choice must be over, under, or seven")
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

            # Track casino stats
            await db.execute("UPDATE players SET casino_plays=casino_plays+1 WHERE telegram_id=?", (req.telegram_id,))
            if payout > 0:
                await db.execute("UPDATE players SET casino_wins=casino_wins+1 WHERE telegram_id=?", (req.telegram_id,))
            await db.commit()

            await track_action(db, req.telegram_id, "casino_play")
            if payout > 0:
                await track_action(db, req.telegram_id, "casino_win")

            player = await get_player(db, req.telegram_id)

            return {"payout": payout, "net": net, "result": result_data, "player": player}

        finally:
            await db.close()


# ── Shop & Character ──

@app.post("/api/shop/buy")
async def shop_buy(req: ShopBuyRequest):
    async with get_player_lock(req.telegram_id):
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

            await track_action(db, req.telegram_id, "shop_buy")

            player = await get_player(db, req.telegram_id)
            inventory = await get_inventory(db, req.telegram_id)
            return {"player": player, "inventory": inventory}

        finally:
            await db.close()


@app.post("/api/shop/equip")
async def equip_item(req: EquipRequest):
    async with get_player_lock(req.telegram_id):
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
    async with get_player_lock(req.telegram_id):
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
    async with get_player_lock(req.telegram_id):
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
            # Apply lootbox_master talent: boost weights for rare+ items
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            lootbox_boost = tb["lootbox_master"]  # % boost for rare+
            loot = case_cfg["loot"]
            items = [l["item_id"] for l in loot]
            weights = []
            for l in loot:
                w = l["weight"]
                if lootbox_boost > 0:
                    item_rarity = SHOP_ITEMS.get(l["item_id"], {}).get("rarity", "common")
                    if item_rarity in ("rare", "epic", "legendary"):
                        w *= (1 + lootbox_boost / 100.0)
                weights.append(w)

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

            await track_action(db, req.telegram_id, "case_open")

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
    async with get_player_lock(req.telegram_id):
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

            # Weighted random selection with lootbox_master talent boost
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            lootbox_boost = tb["lootbox_master"]
            loot = case_cfg["loot"]
            items = [l["item_id"] for l in loot]
            weights = []
            for l in loot:
                w = l["weight"]
                if lootbox_boost > 0:
                    item_rarity = SHOP_ITEMS.get(l["item_id"], {}).get("rarity", "common")
                    if item_rarity in ("rare", "epic", "legendary"):
                        w *= (1 + lootbox_boost / 100.0)
                weights.append(w)

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
            await track_action(db, req.telegram_id, "case_open")

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
    raise HTTPException(400, "Продажа предметов временно отключена")


@app.post("/api/market/buy")
async def market_buy(req: MarketBuyRequest):
    raise HTTPException(400, "Маркет временно отключён")


@app.post("/api/market/cancel")
async def market_cancel(req: MarketListRequest):
    """Cancel a listing — return item to inventory."""
    async with get_player_lock(req.telegram_id):
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

async def gang_log(db, gang_id, message):
    await db.execute("INSERT INTO gang_log (gang_id, message) VALUES (?, ?)", (gang_id, message))

async def get_gang_upgrades(db, gang_id):
    cursor = await db.execute("SELECT upgrade_id, level FROM gang_upgrades WHERE gang_id=?", (gang_id,))
    return {r["upgrade_id"]: r["level"] for r in await cursor.fetchall()}

def get_gang_income_bonus(gang_ups):
    lvl = gang_ups.get("gang_hq", 0)
    if lvl <= 0: return 0
    return GANG_UPGRADES["gang_hq"]["bonuses"][lvl - 1]

def get_gang_attack_bonus(gang_ups):
    lvl = gang_ups.get("gang_armory", 0)
    if lvl <= 0: return 0
    return GANG_UPGRADES["gang_armory"]["bonuses"][lvl - 1]

def get_gang_raid_reduction(gang_ups):
    lvl = gang_ups.get("gang_vault", 0)
    if lvl <= 0: return 0
    return GANG_UPGRADES["gang_vault"]["bonuses"][lvl - 1]

@app.post("/api/gang/create")
async def create_gang(req: GangCreateRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if player["gang_id"]: raise HTTPException(400, "Already in a gang")
            if len(req.name) < 2 or len(req.tag) < 1 or len(req.tag) > 4: raise HTTPException(400, "Invalid name/tag")

            owned = await get_owned_businesses(db, req.telegram_id)
            player, _ = await sync_earnings(db, player, owned)
            if player["cash"] < GANG_CREATE_COST: raise HTTPException(400, f"Need ${GANG_CREATE_COST:,}")

            cursor = await db.execute(
                "INSERT INTO gangs (name, tag, leader_id) VALUES (?, ?, ?)",
                (req.name, req.tag[:4], req.telegram_id),
            )
            gang_id = cursor.lastrowid
            await db.execute("INSERT INTO gang_members (telegram_id, gang_id, role) VALUES (?, ?, 'leader')", (req.telegram_id, gang_id))
            await db.execute("UPDATE players SET gang_id=?, cash=cash-? WHERE telegram_id=?", (gang_id, GANG_CREATE_COST, req.telegram_id))
            await gang_log(db, gang_id, f"🎉 {player['username']} создал банду")
            await db.commit()
            await track_action(db, req.telegram_id, "gang_join")

            player = await get_player(db, req.telegram_id)
            return {"player": player, "gang_id": gang_id, "gang_name": req.name}

        finally:
            await db.close()


@app.post("/api/gang/join")
async def join_gang(req: GangJoinRequest):
    async with get_player_lock(req.telegram_id):
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
            if count >= GANG_MAX_MEMBERS: raise HTTPException(400, "Gang is full")

            await db.execute("INSERT INTO gang_members (telegram_id, gang_id) VALUES (?, ?)", (req.telegram_id, req.gang_id))
            await db.execute("UPDATE players SET gang_id=? WHERE telegram_id=?", (req.gang_id, req.telegram_id))
            await db.execute("UPDATE gangs SET power=power+1 WHERE id=?", (req.gang_id,))
            await gang_log(db, req.gang_id, f"👤 {player['username']} вступил в банду")
            await db.commit()
            await track_action(db, req.telegram_id, "gang_join")

            player = await get_player(db, req.telegram_id)
            return {"player": player, "gang": dict(gang)}

        finally:
            await db.close()


@app.post("/api/gang/leave")
async def leave_gang(req: GangLeaveRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            gang_id = player["gang_id"]
            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            is_leader = member and member["role"] == "leader"

            await db.execute("DELETE FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            await db.execute("UPDATE players SET gang_id=0 WHERE telegram_id=?", (req.telegram_id,))
            await db.execute("UPDATE gangs SET power=MAX(0,power-1) WHERE id=?", (gang_id,))
            await gang_log(db, gang_id, f"🚪 {player['username']} покинул банду")

            if is_leader:
                cursor = await db.execute("SELECT telegram_id FROM gang_members WHERE gang_id=? ORDER BY joined_at ASC LIMIT 1", (gang_id,))
                new_leader = await cursor.fetchone()
                if new_leader:
                    await db.execute("UPDATE gang_members SET role='leader' WHERE telegram_id=?", (new_leader["telegram_id"],))
                    await db.execute("UPDATE gangs SET leader_id=? WHERE id=?", (new_leader["telegram_id"], gang_id))
                    await gang_log(db, gang_id, f"👑 Новый лидер назначен")
                else:
                    await db.execute("DELETE FROM gangs WHERE id=?", (gang_id,))
                    await db.execute("DELETE FROM gang_upgrades WHERE gang_id=?", (gang_id,))
                    await db.execute("UPDATE territories SET owner_gang_id=NULL WHERE owner_gang_id=?", (gang_id,))

            await db.commit()
            player = await get_player(db, req.telegram_id)
            return {"player": player}

        finally:
            await db.close()


@app.post("/api/gang/kick")
async def kick_member(req: GangKickRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player or not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            if not member or member["role"] != "leader": raise HTTPException(403, "Only leader can kick")

            if req.target_id == req.telegram_id: raise HTTPException(400, "Cannot kick yourself")

            cursor = await db.execute("SELECT telegram_id FROM gang_members WHERE telegram_id=? AND gang_id=?", (req.target_id, player["gang_id"]))
            target = await cursor.fetchone()
            if not target: raise HTTPException(404, "Member not found")

            target_player = await get_player(db, req.target_id)
            await db.execute("DELETE FROM gang_members WHERE telegram_id=?", (req.target_id,))
            await db.execute("UPDATE players SET gang_id=0 WHERE telegram_id=?", (req.target_id,))
            await db.execute("UPDATE gangs SET power=MAX(0,power-1) WHERE id=?", (player["gang_id"],))
            await gang_log(db, player["gang_id"], f"❌ {target_player['username']} кикнут из банды")
            await db.commit()
            return {"ok": True}

        finally:
            await db.close()


@app.post("/api/gang/deposit")
async def gang_deposit(req: GangDepositRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player or not player["gang_id"]: raise HTTPException(400, "Not in a gang")
            validate_amount(req.amount, "amount")

            owned = await get_owned_businesses(db, req.telegram_id)
            player, _ = await sync_earnings(db, player, owned)
            if player["cash"] < req.amount: raise HTTPException(400, "Not enough cash")

            await db.execute("UPDATE players SET cash=cash-? WHERE telegram_id=?", (req.amount, req.telegram_id))
            await db.execute("UPDATE gangs SET cash_bank=cash_bank+? WHERE id=?", (req.amount, player["gang_id"]))
            await gang_log(db, player["gang_id"], f"💰 {player['username']} внёс ${int(req.amount):,}")
            await db.commit()

            player = await get_player(db, req.telegram_id)
            cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (player["gang_id"],))
            gang = dict(await cursor.fetchone())
            return {"player": player, "gang": gang}

        finally:
            await db.close()


@app.post("/api/gang/withdraw")
async def gang_withdraw(req: GangWithdrawRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player or not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            if not member or member["role"] != "leader": raise HTTPException(403, "Only leader can withdraw")

            validate_amount(req.amount, "amount")

            cursor = await db.execute("SELECT cash_bank FROM gangs WHERE id=?", (player["gang_id"],))
            gang = await cursor.fetchone()
            if gang["cash_bank"] < req.amount: raise HTTPException(400, "Not enough in bank")

            await db.execute("UPDATE gangs SET cash_bank=cash_bank-? WHERE id=?", (req.amount, player["gang_id"]))
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (req.amount, req.telegram_id))
            await gang_log(db, player["gang_id"], f"💸 Лидер снял ${int(req.amount):,} из банка")
            await db.commit()

            player = await get_player(db, req.telegram_id)
            cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (player["gang_id"],))
            gang = dict(await cursor.fetchone())
            return {"player": player, "gang": gang}

        finally:
            await db.close()


@app.post("/api/gang/upgrade")
async def gang_upgrade(req: GangUpgradeRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player or not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            if not member or member["role"] != "leader": raise HTTPException(403, "Only leader can upgrade")

            cfg = GANG_UPGRADES.get(req.upgrade_id)
            if not cfg: raise HTTPException(400, "Unknown upgrade")

            gang_ups = await get_gang_upgrades(db, player["gang_id"])
            current_level = gang_ups.get(req.upgrade_id, 0)
            if current_level >= cfg["max_level"]: raise HTTPException(400, "Max level reached")

            cost = cfg["costs"][current_level]
            cursor = await db.execute("SELECT cash_bank FROM gangs WHERE id=?", (player["gang_id"],))
            gang = await cursor.fetchone()
            if gang["cash_bank"] < cost: raise HTTPException(400, f"Need ${cost:,} in gang bank")

            await db.execute("UPDATE gangs SET cash_bank=cash_bank-? WHERE id=?", (cost, player["gang_id"]))
            await db.execute(
                "INSERT INTO gang_upgrades (gang_id, upgrade_id, level) VALUES (?,?,1) ON CONFLICT(gang_id, upgrade_id) DO UPDATE SET level=?",
                (player["gang_id"], req.upgrade_id, current_level + 1),
            )

            new_level = current_level + 1
            bonus = cfg["bonuses"][new_level - 1]
            await gang_log(db, player["gang_id"], f"⬆️ {cfg['emoji']} {cfg['name']} улучшен до ур.{new_level} (+{bonus}{'%' if cfg['bonus_type'] != 'attack_power' else ''})")
            await db.commit()

            cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (player["gang_id"],))
            gang = dict(await cursor.fetchone())
            gang_ups = await get_gang_upgrades(db, player["gang_id"])
            return {"gang": gang, "gang_upgrades": gang_ups}

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
        gang = dict(gang)
        cursor = await db.execute(
            "SELECT p.telegram_id, p.username, gm.role FROM gang_members gm JOIN players p ON p.telegram_id=gm.telegram_id WHERE gm.gang_id=?",
            (gang_id,)
        )
        members = [dict(r) for r in await cursor.fetchall()]
        gang_ups = await get_gang_upgrades(db, gang_id)
        cursor = await db.execute("SELECT message, created_at FROM gang_log WHERE gang_id=? ORDER BY id DESC LIMIT 20", (gang_id,))
        log = [dict(r) for r in await cursor.fetchall()]
        return {"gang": gang, "members": members, "gang_upgrades": gang_ups, "gang_log": log, "gang_upgrades_config": GANG_UPGRADES}
    finally:
        await db.close()


# ── PvP ──

@app.post("/api/pvp/attack")
async def pvp_attack(req: PvpAttackRequest):
    lock1_id, lock2_id = sorted([req.telegram_id, req.target_id])
    async with get_player_lock(lock1_id):
      async with get_player_lock(lock2_id):
        db = await get_db()
        try:
            attacker = await get_player(db, req.telegram_id)
            if not attacker: raise HTTPException(404, "Player not found")
            defender = await get_player(db, req.target_id)
            if not defender: raise HTTPException(404, "Target not found")
            if req.telegram_id == req.target_id: raise HTTPException(400, "Can't attack yourself")
            if attacker["cash"] < PVP_MIN_CASH_TO_ATTACK: raise HTTPException(400, "Need more cash")

            # PvP cooldown check
            now = time.time()
            if attacker.get("pvp_cooldown_ts", 0) > now:
                raise HTTPException(400, f"PvP cooldown: {int(attacker['pvp_cooldown_ts'] - now)}s")

            a_owned = await get_owned_businesses(db, req.telegram_id)
            d_owned = await get_owned_businesses(db, req.target_id)
            attacker, _ = await sync_earnings(db, attacker, a_owned)
            defender, _ = await sync_earnings(db, defender, d_owned)

            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            a_power = get_player_level(a_owned) + attacker["reputation_fear"] + tb["street_fighter"]
            d_power = get_player_level(d_owned) + defender["reputation_fear"] + defender["reputation_respect"]

            a_roll = a_power + random.randint(0, 20)
            d_roll = d_power + random.randint(0, 20)

            # Equipment-based PvP bonuses
            a_char = await get_character(db, req.telegram_id)
            d_char = await get_character(db, req.target_id)
            weapon_bonus = 0.0
            if a_char and a_char.get("weapon") and a_char["weapon"] in SHOP_ITEMS:
                w_rarity = SHOP_ITEMS[a_char["weapon"]].get("rarity", "common")
                weapon_bonus = PVP_WEAPON_RARITY_BONUS.get(w_rarity, 0)
            defense_bonus = 0.0
            if d_char:
                for slot in ["hat", "jacket", "accessory", "car", "weapon"]:
                    item_id = d_char.get(slot)
                    if item_id and item_id in SHOP_ITEMS:
                        r = SHOP_ITEMS[item_id].get("rarity", "common")
                        defense_bonus += PVP_DEFENSE_RARITY_BONUS.get(r, 0)
            defense_bonus = min(defense_bonus, 0.15)

            win = a_roll > d_roll
            if win:
                steal_pct = PVP_STEAL_PERCENT + weapon_bonus
                steal = defender["cash"] * steal_pct * (1 - defense_bonus)
                steal = min(steal, 50000)
                await db.execute("UPDATE players SET cash=cash+?, pvp_wins=pvp_wins+1 WHERE telegram_id=?", (steal, req.telegram_id))
                await db.execute("UPDATE players SET cash=MAX(0, cash-?) WHERE telegram_id=?", (steal, req.target_id))
                winner_id = req.telegram_id
            else:
                steal = attacker["cash"] * (PVP_STEAL_PERCENT * 0.5)
                steal = min(steal, 25000)
                await db.execute("UPDATE players SET cash=MAX(0, cash-?) WHERE telegram_id=?", (steal, req.telegram_id))
                await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (steal, req.target_id))
                winner_id = req.target_id

            # Set PvP cooldown
            await db.execute("UPDATE players SET pvp_cooldown_ts=? WHERE telegram_id=?", (now + PVP_COOLDOWN_SECONDS, req.telegram_id))

            await db.execute(
                "INSERT INTO pvp_log (attacker_id, defender_id, winner_id, cash_stolen) VALUES (?,?,?,?)",
                (req.telegram_id, req.target_id, winner_id, steal),
            )
            await db.commit()

            await track_action(db, req.telegram_id, "pvp_attack")
            if win:
                await track_action(db, req.telegram_id, "pvp_win")
                # Increment gang war score for PvP win
                if attacker.get("gang_id"):
                    await increment_war_score(db, attacker["gang_id"], "pvp_win")

            # Notify defender
            await notify_player(db, req.target_id, f"⚔️ На тебя напал {'и победил' if win else 'но проиграл'} игрок {attacker.get('username', 'Аноним')}! {'Украдено' if win else 'Ты отбился и украл'}: ${int(steal):,}")

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
    async with get_player_lock(req.telegram_id):
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
  async with get_player_lock(req.telegram_id):
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
  async with get_player_lock(req.telegram_id):
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
        elif reward_cfg["type"] == "cash_and_case":
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (reward_cfg["amount"], req.telegram_id))
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
    async with get_player_lock(req.telegram_id):
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

            # Talent bonuses applied to starting values
            talents = await get_player_talents(db, req.telegram_id)
            tb = get_talent_bonuses(talents)
            start_cash = 1000 + tb["quick_start"]
            start_fear = tb["intimidation"]

            # Anti-abuse: cancel market listings (return items to inventory)
            cursor = await db.execute("SELECT item_id FROM market_listings WHERE seller_id=?", (req.telegram_id,))
            for row in await cursor.fetchall():
                await db.execute(
                    "INSERT OR IGNORE INTO player_inventory (telegram_id, item_id) VALUES (?,?)",
                    (req.telegram_id, row["item_id"]),
                )
            await db.execute("DELETE FROM market_listings WHERE seller_id=?", (req.telegram_id,))

            # Anti-abuse: delete unopened cases
            await db.execute("DELETE FROM player_cases WHERE telegram_id=?", (req.telegram_id,))

            # Anti-abuse: prevent gang bank cash stashing
            if player.get("gang_id"):
                cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
                member = await cursor.fetchone()
                if member and member["role"] == "leader":
                    # Leader: zero the gang bank (they can withdraw)
                    await db.execute("UPDATE gangs SET cash_bank=0 WHERE id=?", (player["gang_id"],))

            # Reset businesses, cash, reputation — keep items, gang, prestige, talents
            await db.execute("DELETE FROM player_businesses WHERE telegram_id=?", (req.telegram_id,))
            await db.execute("DELETE FROM player_upgrades WHERE telegram_id=?", (req.telegram_id,))
            await db.execute(
                "UPDATE players SET cash=?, suspicion=0, reputation_fear=?, reputation_respect=0, "
                "total_earned=0, total_robberies=0, robbery_cooldown_ts=0, pvp_cooldown_ts=0, "
                "prestige_level=?, prestige_multiplier=?, talent_points=talent_points+1 WHERE telegram_id=?",
                (start_cash, start_fear, new_prestige, new_multiplier, req.telegram_id),
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
                "talent_points": player.get("talent_points", 0),
            }

        finally:
            await db.close()


# ── Talent Tree ──

@app.post("/api/talent/assign")
async def assign_talent(req: TalentAssignRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")

            talent_cfg = ALL_TALENTS.get(req.talent_id)
            if not talent_cfg: raise HTTPException(400, "Unknown talent")

            if player.get("talent_points", 0) <= 0:
                raise HTTPException(400, "No talent points")

            talents = await get_player_talents(db, req.telegram_id)
            current_level = talents.get(req.talent_id, 0)
            if current_level >= talent_cfg["max_level"]:
                raise HTTPException(400, "Max level reached")

            # Insert or update talent level
            await db.execute(
                "INSERT INTO player_talents (telegram_id, talent_id, level) VALUES (?,?,1) "
                "ON CONFLICT(telegram_id, talent_id) DO UPDATE SET level=level+1",
                (req.telegram_id, req.talent_id),
            )
            await db.execute(
                "UPDATE players SET talent_points=talent_points-1 WHERE telegram_id=?",
                (req.telegram_id,),
            )
            await db.commit()

            player = await get_player(db, req.telegram_id)
            talents = await get_player_talents(db, req.telegram_id)
            return {
                "player": player,
                "player_talents": talents,
                "talent_points": player.get("talent_points", 0),
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
    async with get_player_lock(req.telegram_id):
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

            # Calculate attacker strength (includes gang armory bonus)
            atk_gang_ups = await get_gang_upgrades(db, player["gang_id"])
            atk_armory_bonus = get_gang_attack_bonus(atk_gang_ups)
            cursor = await db.execute(
                "SELECT SUM(pb.level) as total_level FROM gang_members gm JOIN player_businesses pb ON pb.telegram_id=gm.telegram_id WHERE gm.gang_id=?",
                (player["gang_id"],),
            )
            atk_row = await cursor.fetchone()
            atk_level = (atk_row["total_level"] or 0) if atk_row else 0
            atk_power = atk_level + gang["power"] + atk_armory_bonus + random.randint(0, 30)

            # Defender strength (includes their armory bonus)
            def_power = 0
            defender_gang_id = territory["owner_gang_id"]
            if defender_gang_id:
                def_gang_ups = await get_gang_upgrades(db, defender_gang_id)
                def_armory_bonus = get_gang_attack_bonus(def_gang_ups)
                cursor = await db.execute(
                    "SELECT SUM(pb.level) as total_level FROM gang_members gm JOIN player_businesses pb ON pb.telegram_id=gm.telegram_id WHERE gm.gang_id=?",
                    (defender_gang_id,),
                )
                def_row = await cursor.fetchone()
                def_level = (def_row["total_level"] or 0) if def_row else 0
                cursor = await db.execute("SELECT power FROM gangs WHERE id=?", (defender_gang_id,))
                def_gang = await cursor.fetchone()
                def_gang_power = def_gang["power"] if def_gang else 0
                def_power = def_level + def_gang_power + def_armory_bonus + 10 + random.randint(0, 30)  # +10 defender bonus

            win = atk_power > def_power

            # Update cooldown
            await db.execute("UPDATE gangs SET last_territory_attack_ts=? WHERE id=?", (now, player["gang_id"]))

            if win:
                await db.execute(
                    "UPDATE territories SET owner_gang_id=?, captured_at=? WHERE id=?",
                    (player["gang_id"], now, req.territory_id),
                )
                await track_action(db, req.telegram_id, "territory_capture")
                # Increment gang war score for territory capture
                await increment_war_score(db, player["gang_id"], "territory_capture")
                # Notify defender gang
                if defender_gang_id:
                    cursor2 = await db.execute("SELECT leader_id FROM gangs WHERE id=?", (defender_gang_id,))
                    def_leader = await cursor2.fetchone()
                    if def_leader:
                        await notify_player(db, def_leader["leader_id"], f"🗺 Территория \"{territory['name']}\" была захвачена!")

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
  async with get_player_lock(req.telegram_id):
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
    async with get_player_lock(req.telegram_id):
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
    # Add skin case as purchasable
    if req.package_id == "skin_case":
        all_packages["skin_case"] = {"stars": SKIN_CASE["stars_price"], "label": SKIN_CASE["name"]}
    # Add season pass premium
    if req.package_id == "season_1_premium":
        all_packages["season_1_premium"] = {"stars": SEASON_PASS_CONFIG["premium_stars"], "label": "Премиум Пас 🏴"}
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
  async with get_player_lock(req.telegram_id):
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
  async with get_player_lock(req.telegram_id):
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


# ── Business Skins ──

async def get_player_skins(db, telegram_id):
    cursor = await db.execute("SELECT skin_id FROM player_skins WHERE telegram_id=?", (telegram_id,))
    return [r["skin_id"] for r in await cursor.fetchall()]

async def get_equipped_skins(db, telegram_id):
    cursor = await db.execute("SELECT business_id, skin_id FROM business_equipped_skins WHERE telegram_id=?", (telegram_id,))
    return {r["business_id"]: r["skin_id"] for r in await cursor.fetchall()}

def roll_skin(vip_boost=False):
    """Roll a random skin based on rarity chances."""
    skins_by_rarity = {}
    for sid, s in BUSINESS_SKINS.items():
        skins_by_rarity.setdefault(s["rarity"], []).append(sid)

    # Build weighted rarity list
    rarities = list(SKIN_RARITIES.items())
    roll = random.random()
    if vip_boost:
        roll *= 0.7  # VIP gets 30% better odds (shifts toward rarer)

    cumulative = 0
    chosen_rarity = "common"
    for rarity_id, rarity_cfg in rarities:
        cumulative += rarity_cfg["chance"]
        if roll < cumulative:
            chosen_rarity = rarity_id
            break

    pool = skins_by_rarity.get(chosen_rarity, skins_by_rarity["common"])
    return random.choice(pool)


@app.post("/api/skin/open")
async def open_skin_case(req: SkinCaseOpenRequest):
  async with get_player_lock(req.telegram_id):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")

        vip = is_vip_active(player)
        count = max(1, min(req.count, 50))
        results = []

        if req.case_type == "vip":
            if not vip: raise HTTPException(400, "VIP not active")
            today = today_utc()
            if player.get("last_vip_skin_claim", "") == today:
                raise HTTPException(400, "Already claimed today")
            await db.execute("UPDATE players SET last_vip_skin_claim=? WHERE telegram_id=?", (today, req.telegram_id))
            skin_id = roll_skin(vip_boost=True)
            await db.execute("INSERT INTO player_skins (telegram_id, skin_id) VALUES (?, ?)", (req.telegram_id, skin_id))
            skin_cfg = BUSINESS_SKINS[skin_id]
            rarity_cfg = SKIN_RARITIES[skin_cfg["rarity"]]
            results.append({"skin_id": skin_id, "skin": skin_cfg, "rarity": rarity_cfg})
        else:
            # Get available cases
            cursor = await db.execute(
                "SELECT id FROM player_cases WHERE telegram_id=? AND case_id='skin_case' ORDER BY id LIMIT ?",
                (req.telegram_id, count),
            )
            case_rows = await cursor.fetchall()
            if not case_rows: raise HTTPException(400, "No skin cases")

            for case_row in case_rows:
                await db.execute("DELETE FROM player_cases WHERE id=?", (case_row["id"],))
                skin_id = roll_skin(vip_boost=False)
                await db.execute("INSERT INTO player_skins (telegram_id, skin_id) VALUES (?, ?)", (req.telegram_id, skin_id))
                skin_cfg = BUSINESS_SKINS[skin_id]
                rarity_cfg = SKIN_RARITIES[skin_cfg["rarity"]]
                results.append({"skin_id": skin_id, "skin": skin_cfg, "rarity": rarity_cfg})

        await db.commit()

        player_skins = await get_player_skins(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)

        # Single open — backward compatible
        if len(results) == 1:
            return {
                "skin_id": results[0]["skin_id"],
                "skin": results[0]["skin"],
                "rarity": results[0]["rarity"],
                "player_skins": player_skins,
                "player_cases": player_cases,
                "results": results,
            }

        return {
            "results": results,
            "player_skins": player_skins,
            "player_cases": player_cases,
        }
    finally:
        await db.close()


@app.post("/api/skin/equip")
async def equip_skin(req: SkinEquipRequest):
  async with get_player_lock(req.telegram_id):
    db = await get_db()
    try:
        player = await get_player(db, req.telegram_id)
        if not player: raise HTTPException(404, "Player not found")

        if req.skin_id == "none":
            await db.execute(
                "DELETE FROM business_equipped_skins WHERE telegram_id=? AND business_id=?",
                (req.telegram_id, req.business_id),
            )
        else:
            # Check player owns this skin
            cursor = await db.execute(
                "SELECT id FROM player_skins WHERE telegram_id=? AND skin_id=?",
                (req.telegram_id, req.skin_id),
            )
            if not await cursor.fetchone():
                raise HTTPException(400, "Skin not owned")

            await db.execute(
                "INSERT INTO business_equipped_skins (telegram_id, business_id, skin_id) VALUES (?,?,?) ON CONFLICT(telegram_id, business_id) DO UPDATE SET skin_id=?",
                (req.telegram_id, req.business_id, req.skin_id, req.skin_id),
            )
        await db.commit()

        equipped = await get_equipped_skins(db, req.telegram_id)
        return {"equipped_skins": equipped}
    finally:
        await db.close()


@app.get("/api/skins/config")
async def skins_config():
    return {"skins": BUSINESS_SKINS, "rarities": SKIN_RARITIES, "case": SKIN_CASE, "case_vip": SKIN_CASE_VIP}


# ── TON Connect ──

@app.post("/api/ton/create")
async def ton_create_payment(req: TonCreateRequest):
    """Create a TON payment request — returns wallet address, amount, and comment."""
    all_packages = {**VIP_PACKAGES, **CASH_PACKAGES, **CASE_PACKAGES, "season_1_premium": {"label": "Season Pass Premium"}}
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
    """Verify a TON transaction on-chain and activate the purchase."""
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

        # Verify on-chain via TON Center API
        verified = False
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://toncenter.com/api/v2/getTransactions",
                params={"address": TON_WALLET_ADDRESS, "limit": 20},
            )
            if resp.status_code == 200:
                data = resp.json()
                for tx in data.get("result", []):
                    msg = tx.get("in_msg", {})
                    body = msg.get("message", "")
                    value = int(msg.get("value", "0"))
                    if req.comment and req.comment in body and value > 0:
                        # Verify amount matches expected price
                        ton_price = TON_PRICES.get(req.package_id, {}).get("ton", 999)
                        expected_nano = int(float(ton_price) * 1e9)
                        if value < int(expected_nano * 0.95):  # 5% tolerance
                            continue
                        verified = True
                        break

        if not verified:
            return {"status": "pending", "message": "Транзакция ещё не найдена. Подожди 1-2 минуты и нажми проверить снова."}

        # Activate purchase
        all_packages = {**VIP_PACKAGES, **CASH_PACKAGES, **CASE_PACKAGES, "season_1_premium": {"label": "Season Pass Premium"}}
        pkg = all_packages.get(req.package_id)
        if not pkg:
            raise HTTPException(400, "Unknown package")

        now = time.time()
        if req.package_id == "season_1_premium":
            season_id = SEASON_PASS_CONFIG["id"]
            await db.execute(
                "INSERT INTO player_season_pass (telegram_id, season_id, is_premium, purchased_at) VALUES (?,?,1,?) "
                "ON CONFLICT(telegram_id) DO UPDATE SET is_premium=1, purchased_at=?",
                (req.telegram_id, season_id, now, now),
            )

        elif req.package_id in VIP_PACKAGES:
            days = pkg["days"]
            cursor2 = await db.execute("SELECT vip_until FROM players WHERE telegram_id=?", (req.telegram_id,))
            row = await cursor2.fetchone()
            if row:
                current_until = row["vip_until"] or 0
                base = max(current_until, now)
                new_until = base + days * 86400
                await db.execute("UPDATE players SET is_vip=1, vip_until=? WHERE telegram_id=?", (new_until, req.telegram_id))

        elif req.package_id in CASH_PACKAGES:
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (pkg["cash"], req.telegram_id))

        elif req.package_id in CASE_PACKAGES:
            for case_id, count in pkg["cases"]:
                for _ in range(count):
                    await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?, ?)", (req.telegram_id, case_id))

        # Log transaction
        await db.execute(
            "INSERT INTO premium_transactions (telegram_id, package_id, payment_method, amount) VALUES (?,?,?,?)",
            (req.telegram_id, req.package_id, "ton", req.tx_hash),
        )
        await db.commit()

        player = await get_player(db, req.telegram_id)
        return {"status": "ok", "message": "Покупка активирована!", "player": player}
    finally:
        await db.close()


# ── Tournament Leaderboard ──

@app.get("/api/tournament/leaderboard")
async def tournament_leaderboard():
    db = await get_db()
    try:
        day = today_utc()
        cursor = await db.execute(
            "SELECT ts.telegram_id, ts.score, p.username FROM tournament_scores ts "
            "JOIN players p ON p.telegram_id=ts.telegram_id WHERE ts.day=? ORDER BY ts.score DESC LIMIT 20",
            (day,),
        )
        rows = [dict(r) for r in await cursor.fetchall()]
        return {"leaderboard": rows, "day": day, "prizes": TOURNAMENT_PRIZES}
    finally:
        await db.close()


# ── Quests ──

@app.get("/api/quests/{telegram_id}")
async def get_quests(telegram_id: int):
    db = await get_db()
    try:
        owned = await get_owned_businesses(db, telegram_id)
        await init_quests(db, telegram_id, get_player_level(owned))
        quests = await get_player_quests(db, telegram_id)
        return {"quests": quests, "quest_lines": QUEST_LINES}
    finally:
        await db.close()


# ── Event Claim ──

@app.post("/api/event/claim")
async def claim_event_milestone(req: EventClaimRequest):
  async with get_player_lock(req.telegram_id):
    db = await get_db()
    try:
        ev = get_active_event()
        if not ev:
            raise HTTPException(400, "No active event")

        progress_row = await get_event_progress(db, req.telegram_id, ev["id"])
        progress = progress_row.get("progress", 0)
        claimed_str = progress_row.get("rewards_claimed", "")
        claimed_set = set(claimed_str.split(",")) if claimed_str else set()

        milestones = ev["milestones"]
        if req.milestone_index < 0 or req.milestone_index >= len(milestones):
            raise HTTPException(400, "Invalid milestone")

        ms = milestones[req.milestone_index]
        ms_key = str(req.milestone_index)
        if ms_key in claimed_set:
            raise HTTPException(400, "Already claimed")
        if progress < ms["target"]:
            raise HTTPException(400, "Not enough progress")

        # Give reward
        if ms["reward_type"] == "cash":
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (ms["reward_amount"], req.telegram_id))
        elif ms["reward_type"] == "case":
            await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?,?)", (req.telegram_id, ms["reward_amount"]))
        elif ms["reward_type"] == "item":
            await db.execute("INSERT OR IGNORE INTO player_inventory (telegram_id, item_id) VALUES (?,?)", (req.telegram_id, ms["reward_amount"]))

        claimed_set.add(ms_key)
        new_claimed = ",".join(sorted(claimed_set))
        await db.execute(
            "UPDATE player_event_progress SET rewards_claimed=? WHERE telegram_id=? AND event_id=?",
            (new_claimed, req.telegram_id, ev["id"]),
        )
        await db.commit()

        player = await get_player(db, req.telegram_id)
        event_progress = await get_event_progress(db, req.telegram_id, ev["id"])
        return {"player": player, "event_progress": event_progress}
    finally:
        await db.close()


# ── Season Pass Claim ──

@app.post("/api/season/claim")
async def claim_season_reward(req: SeasonClaimRequest):
  async with get_player_lock(req.telegram_id):
    db = await get_db()
    try:
        sp = await get_season_pass(db, req.telegram_id)
        level = calc_season_level(sp["xp"])

        if req.level < 1 or req.level > SEASON_PASS_CONFIG["max_level"]:
            raise HTTPException(400, "Invalid level")
        if req.level > level:
            raise HTTPException(400, "Level not reached yet")
        if req.track not in ("free", "premium"):
            raise HTTPException(400, "Invalid track")
        if req.track == "premium" and not sp["is_premium"]:
            raise HTTPException(400, "Premium pass required")

        reward_entry = SEASON_PASS_REWARDS.get(req.level)
        if not reward_entry:
            raise HTTPException(400, "No reward for this level")

        claimed_field = "free_claimed" if req.track == "free" else "premium_claimed"
        claimed_str = sp.get(claimed_field, "")
        claimed_set = set(claimed_str.split(",")) if claimed_str else set()
        level_key = str(req.level)

        if level_key in claimed_set:
            raise HTTPException(400, "Already claimed")

        reward = reward_entry[req.track]
        # Give reward
        if reward["type"] == "cash":
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (reward["amount"], req.telegram_id))
        elif reward["type"] == "case":
            await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?,?)", (req.telegram_id, reward["case_id"]))
        elif reward["type"] == "cash_and_case":
            await db.execute("UPDATE players SET cash=cash+? WHERE telegram_id=?", (reward["amount"], req.telegram_id))
            await db.execute("INSERT INTO player_cases (telegram_id, case_id) VALUES (?,?)", (req.telegram_id, reward["case_id"]))

        claimed_set.add(level_key)
        new_claimed = ",".join(sorted(claimed_set, key=lambda x: int(x)))
        season_id = SEASON_PASS_CONFIG["id"]
        await db.execute(
            f"INSERT INTO player_season_pass (telegram_id, season_id, {claimed_field}) VALUES (?,?,?) "
            f"ON CONFLICT(telegram_id) DO UPDATE SET {claimed_field}=?",
            (req.telegram_id, season_id, new_claimed, new_claimed),
        )
        await db.commit()

        player = await get_player(db, req.telegram_id)
        season_pass = await get_season_pass(db, req.telegram_id)
        player_cases = await get_player_cases(db, req.telegram_id)
        return {"player": player, "season_pass": season_pass, "player_cases": player_cases}
    finally:
        await db.close()


# ── Boss Attack ──

@app.post("/api/boss/attack")
async def boss_attack(req: BossAttackRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if not player.get("gang_id") or player["gang_id"] != req.gang_id:
                raise HTTPException(400, "Not in this gang")

            # Cooldown check
            now = time.time()
            last_attack = player.get("last_boss_attack_ts", 0)
            if now - last_attack < BOSS_ATTACK_COOLDOWN:
                remaining = int(BOSS_ATTACK_COOLDOWN - (now - last_attack))
                raise HTTPException(400, f"Cooldown: {remaining}s")

            # Get boss
            cursor = await db.execute("SELECT * FROM active_bosses WHERE gang_id=? AND defeated=0", (req.gang_id,))
            boss_row = await cursor.fetchone()
            if not boss_row:
                raise HTTPException(400, "No active boss")
            boss_row = dict(boss_row)

            # Calculate damage
            owned = await get_owned_businesses(db, req.telegram_id)
            player_level = get_player_level(owned)
            equip_bonus = await get_equip_income_bonus(db, req.telegram_id)
            armory_bonus = 0
            if player.get("gang_id"):
                gang_ups = await get_gang_upgrades(db, player["gang_id"])
                armory_bonus = get_gang_attack_bonus(gang_ups)
            damage = calc_attack_damage(player_level, player["reputation_fear"], equip_bonus, armory_bonus)

            new_hp = max(0, boss_row["current_health"] - damage)
            defeated = 1 if new_hp <= 0 else 0

            await db.execute("UPDATE active_bosses SET current_health=?, defeated=? WHERE gang_id=? AND defeated=0",
                             (new_hp, defeated, req.gang_id))
            await db.execute("INSERT INTO boss_attack_log (gang_id, telegram_id, damage) VALUES (?,?,?)",
                             (req.gang_id, req.telegram_id, damage))
            await db.execute("UPDATE players SET last_boss_attack_ts=? WHERE telegram_id=?", (now, req.telegram_id))
            await db.commit()

            rewards = None
            if defeated:
                await distribute_boss_rewards(db, req.gang_id, boss_row["boss_id"])
                # Spawn next boss
                await spawn_boss_for_gang(db, req.gang_id)
                rewards = {"boss_defeated": True, "boss_name": boss_row["boss_id"]}

            boss_data = await get_boss_data(db, req.gang_id)
            player = await get_player(db, req.telegram_id)
            return {"damage": damage, "boss_data": boss_data, "player": player, "rewards": rewards}

        finally:
            await db.close()


@app.get("/api/boss/{gang_id}")
async def get_boss(gang_id: int):
    db = await get_db()
    try:
        await spawn_boss_for_gang(db, gang_id)
        boss_data = await get_boss_data(db, gang_id)
        return {"boss_data": boss_data}
    finally:
        await db.close()


# ── Telegram Notifications ──

async def send_telegram_notification(telegram_id: int, text: str):
    """Send a Telegram notification to a player. Non-blocking, graceful failure."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": telegram_id, "text": text, "parse_mode": "HTML"},
            )
    except Exception:
        pass  # graceful failure (user blocked bot, etc.)

async def notify_player(db, telegram_id: int, text: str):
    """Send notification if player has notifications enabled."""
    player = await get_player(db, telegram_id)
    if player and player.get("notifications_enabled", 1):
        asyncio.create_task(send_telegram_notification(telegram_id, text))


# ── Gang Heists ──

class GangHeistStartRequest(BaseModel):
    telegram_id: int
    heist_type: str

class GangHeistJoinRequest(BaseModel):
    telegram_id: int
    heist_id: int

class GangHeistExecuteRequest(BaseModel):
    telegram_id: int
    heist_id: int

@app.post("/api/gang/heist/start")
async def gang_heist_start(req: GangHeistStartRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cfg = GANG_HEISTS.get(req.heist_type)
            if not cfg: raise HTTPException(400, "Unknown heist type")

            # Check role
            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            if not member or member["role"] not in ("leader", "officer"):
                raise HTTPException(400, "Only leader/officer can start heists")

            # Check cooldown
            cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (player["gang_id"],))
            gang = dict(await cursor.fetchone())
            now = time.time()
            if gang.get("last_heist_ts", 0) + cfg["cooldown"] > now:
                remaining = int(gang["last_heist_ts"] + cfg["cooldown"] - now)
                raise HTTPException(400, f"Heist cooldown: {remaining}s")

            # Check no active heist
            cursor = await db.execute(
                "SELECT id FROM gang_heists WHERE gang_id=? AND status='recruiting'", (player["gang_id"],)
            )
            if await cursor.fetchone():
                raise HTTPException(400, "Already have an active heist")

            # Create heist
            await db.execute(
                "INSERT INTO gang_heists (gang_id, heist_type, participants) VALUES (?,?,?)",
                (player["gang_id"], req.heist_type, str(req.telegram_id)),
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT * FROM gang_heists WHERE gang_id=? AND status='recruiting' ORDER BY id DESC LIMIT 1",
                (player["gang_id"],)
            )
            heist = dict(await cursor.fetchone())
            await gang_log(db, player["gang_id"], f"🏴 {player['username']} начал ограбление: {cfg['name']}")
            await db.commit()

            return {"heist": heist, "config": cfg}
        finally:
            await db.close()


@app.post("/api/gang/heist/join")
async def gang_heist_join(req: GangHeistJoinRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cursor = await db.execute(
                "SELECT * FROM gang_heists WHERE id=? AND gang_id=? AND status='recruiting'",
                (req.heist_id, player["gang_id"]),
            )
            row = await cursor.fetchone()
            if not row: raise HTTPException(400, "Heist not found or not recruiting")
            heist = dict(row)

            participants = heist["participants"].split(",") if heist["participants"] else []
            if str(req.telegram_id) in participants:
                raise HTTPException(400, "Already joined")

            participants.append(str(req.telegram_id))
            await db.execute(
                "UPDATE gang_heists SET participants=? WHERE id=?",
                (",".join(participants), heist["id"]),
            )
            await db.commit()

            heist["participants"] = ",".join(participants)
            cfg = GANG_HEISTS.get(heist["heist_type"], {})
            return {"heist": heist, "config": cfg, "participant_count": len(participants)}
        finally:
            await db.close()


@app.post("/api/gang/heist/execute")
async def gang_heist_execute(req: GangHeistExecuteRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            if not member or member["role"] not in ("leader", "officer"):
                raise HTTPException(400, "Only leader/officer can execute")

            cursor = await db.execute(
                "SELECT * FROM gang_heists WHERE id=? AND gang_id=? AND status='recruiting'",
                (req.heist_id, player["gang_id"]),
            )
            row = await cursor.fetchone()
            if not row: raise HTTPException(400, "Heist not found")
            heist = dict(row)

            cfg = GANG_HEISTS.get(heist["heist_type"])
            if not cfg: raise HTTPException(400, "Invalid heist type")

            participants = heist["participants"].split(",") if heist["participants"] else []
            if len(participants) < cfg["min_members"]:
                raise HTTPException(400, f"Need at least {cfg['min_members']} members")

            now = time.time()
            # Calculate reward
            base_reward = random.uniform(cfg["min_reward"], cfg["max_reward"])
            member_bonus = len(participants) * cfg["reward_per_member"]
            total_reward = base_reward + member_bonus

            # Distribute evenly among participants
            share = total_reward / len(participants)
            for pid_str in participants:
                pid = int(pid_str)
                await db.execute("UPDATE players SET cash=cash+?, total_earned=total_earned+? WHERE telegram_id=?", (share, share, pid))
                await notify_player(db, pid, f"🏴 Ограбление \"{cfg['name']}\" успешно!\n💰 Твоя доля: ${int(share):,}")

            # Update heist status
            await db.execute(
                "UPDATE gang_heists SET status='completed', executed_at=?, total_reward=? WHERE id=?",
                (now, total_reward, heist["id"]),
            )
            await db.execute("UPDATE gangs SET last_heist_ts=? WHERE id=?", (now, player["gang_id"]))
            await gang_log(db, player["gang_id"], f"💰 Ограбление \"{cfg['name']}\" принесло ${int(total_reward):,}")
            await db.commit()

            return {
                "success": True,
                "total_reward": round(total_reward, 2),
                "share": round(share, 2),
                "participants": len(participants),
            }
        finally:
            await db.close()


@app.get("/api/gang/heists/{gang_id}")
async def get_active_heists(gang_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM gang_heists WHERE gang_id=? AND status='recruiting' ORDER BY id DESC",
            (gang_id,),
        )
        heists = [dict(r) for r in await cursor.fetchall()]
        return {"heists": heists}
    finally:
        await db.close()


# ── Gang Wars ──

class GangWarDeclareRequest(BaseModel):
    telegram_id: int
    target_gang_id: int

@app.post("/api/gang/war/declare")
async def gang_war_declare(req: GangWarDeclareRequest):
    async with get_player_lock(req.telegram_id):
        db = await get_db()
        try:
            player = await get_player(db, req.telegram_id)
            if not player: raise HTTPException(404, "Player not found")
            if not player["gang_id"]: raise HTTPException(400, "Not in a gang")

            cursor = await db.execute("SELECT role FROM gang_members WHERE telegram_id=?", (req.telegram_id,))
            member = await cursor.fetchone()
            if not member or member["role"] != "leader":
                raise HTTPException(400, "Only leader can declare war")

            if player["gang_id"] == req.target_gang_id:
                raise HTTPException(400, "Can't declare war on yourself")

            # Check target gang exists
            cursor = await db.execute("SELECT * FROM gangs WHERE id=?", (req.target_gang_id,))
            target_gang = await cursor.fetchone()
            if not target_gang: raise HTTPException(400, "Target gang not found")

            # Check no active war
            cursor = await db.execute(
                "SELECT id FROM gang_wars WHERE status='active' AND (attacker_gang_id=? OR defender_gang_id=? OR attacker_gang_id=? OR defender_gang_id=?)",
                (player["gang_id"], player["gang_id"], req.target_gang_id, req.target_gang_id),
            )
            if await cursor.fetchone():
                raise HTTPException(400, "One of the gangs already in a war")

            # Check cost
            cursor = await db.execute("SELECT cash_bank FROM gangs WHERE id=?", (player["gang_id"],))
            gang = await cursor.fetchone()
            if gang["cash_bank"] < GANG_WAR_CONFIG["declare_cost"]:
                raise HTTPException(400, "Not enough in gang bank")

            # Deduct cost and create war
            await db.execute("UPDATE gangs SET cash_bank=cash_bank-? WHERE id=?", (GANG_WAR_CONFIG["declare_cost"], player["gang_id"]))
            await db.execute(
                "INSERT INTO gang_wars (attacker_gang_id, defender_gang_id) VALUES (?,?)",
                (player["gang_id"], req.target_gang_id),
            )
            await gang_log(db, player["gang_id"], f"⚔️ Объявлена война банде #{req.target_gang_id}!")
            await gang_log(db, req.target_gang_id, f"⚔️ Банда #{player['gang_id']} объявила войну!")

            # Notify defender gang leader
            target_gang = dict(target_gang)
            await notify_player(db, target_gang["leader_id"], f"⚔️ Вашей банде объявлена война!")

            await db.commit()
            return {"status": "war_declared", "target_gang_id": req.target_gang_id}
        finally:
            await db.close()


async def check_and_finalize_wars(db):
    """Auto-finalize expired wars."""
    now = time.time()
    cursor = await db.execute(
        "SELECT * FROM gang_wars WHERE status='active' AND started_at + ? < ?",
        (GANG_WAR_CONFIG["duration"], now),
    )
    wars = [dict(r) for r in await cursor.fetchall()]
    for war in wars:
        if war["attacker_score"] > war["defender_score"]:
            winner = war["attacker_gang_id"]
            loser = war["defender_gang_id"]
        elif war["defender_score"] > war["attacker_score"]:
            winner = war["defender_gang_id"]
            loser = war["attacker_gang_id"]
        else:
            winner = 0
            loser = 0

        await db.execute(
            "UPDATE gang_wars SET status='finished', ended_at=?, winner_gang_id=? WHERE id=?",
            (now, winner, war["id"]),
        )
        if winner:
            await db.execute("UPDATE gangs SET cash_bank=cash_bank+? WHERE id=?", (GANG_WAR_CONFIG["winner_reward"], winner))
            await db.execute("UPDATE gangs SET cash_bank=cash_bank+? WHERE id=?", (GANG_WAR_CONFIG["loser_reward"], loser))
            await gang_log(db, winner, f"🏆 Война выиграна! +${GANG_WAR_CONFIG['winner_reward']:,} в банк")
            await gang_log(db, loser, f"😞 Война проиграна. +${GANG_WAR_CONFIG['loser_reward']:,} утешительный приз")
        else:
            for gid in [war["attacker_gang_id"], war["defender_gang_id"]]:
                await gang_log(db, gid, "🤝 Война окончена ничьей")
    if wars:
        await db.commit()


@app.get("/api/gang/war/{gang_id}")
async def get_gang_war(gang_id: int):
    db = await get_db()
    try:
        await check_and_finalize_wars(db)
        cursor = await db.execute(
            "SELECT gw.*, g1.name as attacker_name, g1.tag as attacker_tag, g2.name as defender_name, g2.tag as defender_tag "
            "FROM gang_wars gw "
            "JOIN gangs g1 ON g1.id=gw.attacker_gang_id "
            "JOIN gangs g2 ON g2.id=gw.defender_gang_id "
            "WHERE (gw.attacker_gang_id=? OR gw.defender_gang_id=?) "
            "ORDER BY gw.id DESC LIMIT 5",
            (gang_id, gang_id),
        )
        wars = [dict(r) for r in await cursor.fetchall()]
        return {"wars": wars, "config": GANG_WAR_CONFIG}
    finally:
        await db.close()


# Increment war scores in territory_attack and pvp_attack
async def increment_war_score(db, gang_id: int, score_type: str):
    """Add score to an active war for a gang."""
    if not gang_id:
        return
    score = GANG_WAR_CONFIG.get(f"score_per_{score_type}", 0)
    if score <= 0:
        return
    cursor = await db.execute(
        "SELECT * FROM gang_wars WHERE status='active' AND (attacker_gang_id=? OR defender_gang_id=?)",
        (gang_id, gang_id),
    )
    war = await cursor.fetchone()
    if not war:
        return
    war = dict(war)
    if war["attacker_gang_id"] == gang_id:
        await db.execute("UPDATE gang_wars SET attacker_score=attacker_score+? WHERE id=?", (score, war["id"]))
    else:
        await db.execute("UPDATE gang_wars SET defender_score=defender_score+? WHERE id=?", (score, war["id"]))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
