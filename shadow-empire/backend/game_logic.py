"""
Core game logic — income calculation, buying, upgrading, robberies, raids.
"""

import time
import random
from backend.game_config import (
    ALL_BUSINESSES,
    ALL_ROBBERIES,
    LEGAL_BUSINESSES,
    SHADOW_BUSINESSES,
    RAID_THRESHOLD,
    RAID_CASH_PENALTY,
    SUSPICION_DECAY_PER_SEC,
    MAX_SUSPICION,
    FEAR_SHADOW_DISCOUNT,
    RESPECT_LEGAL_DISCOUNT,
    FEAR_INCOME_BONUS,
    RESPECT_SUSPICION_REDUCE,
)


def calc_business_cost(business_cfg, level):
    """Cost to upgrade from current level to next."""
    return business_cfg["base_cost"] * (business_cfg["cost_multiplier"] ** (level - 1))


def calc_business_income(business_cfg, level):
    """Income per second at given level."""
    return business_cfg["base_income"] * (business_cfg["income_multiplier"] ** (level - 1))


def calc_manager_cost(business_cfg):
    return business_cfg["manager_cost"]


def calc_total_income(owned_businesses, fear=0, respect=0, prestige_multiplier=1.0, territory_bonus=0.0, vip_multiplier=1.0, ad_boost=False, equip_income_bonus=0, upgrade_income_bonus=0, gang_income_bonus=0, event_income_multiplier=1.0, talent_income_bonus=0, talent_suspicion_reduce=0):
    """
    Returns (total_income_per_sec, total_suspicion_per_sec).
    talent_income_bonus: % bonus from passive_income talent
    talent_suspicion_reduce: % reduce from shadow_talent
    """
    total_income = 0.0
    total_suspicion_change = 0.0

    fear_bonus = min(fear * FEAR_INCOME_BONUS, 0.5)
    respect_reduce = min(respect * RESPECT_SUSPICION_REDUCE, 0.5)

    for ob in owned_businesses:
        cfg = ALL_BUSINESSES.get(ob["business_id"])
        if not cfg:
            continue
        income = calc_business_income(cfg, ob["level"])

        if cfg["type"] == "shadow":
            income *= (1 + fear_bonus)
            susp = cfg["suspicion_add"] * (1 - respect_reduce)
            susp *= (1 - talent_suspicion_reduce / 100.0)
            total_suspicion_change += susp
        else:
            total_suspicion_change -= cfg["suspicion_reduce"]

        total_income += income

    total_income *= prestige_multiplier
    total_income *= (1 + territory_bonus / 100.0)
    total_income *= (1 + equip_income_bonus / 100.0)
    total_income *= (1 + upgrade_income_bonus / 100.0)
    total_income *= (1 + gang_income_bonus / 100.0)
    total_income *= (1 + talent_income_bonus / 100.0)
    total_income *= vip_multiplier
    total_income *= event_income_multiplier
    if ad_boost:
        total_income *= 2.0
    total_suspicion_change -= SUSPICION_DECAY_PER_SEC

    return round(total_income, 2), round(total_suspicion_change, 4)


def calc_offline_earnings(owned_businesses, last_ts, current_suspicion, fear=0, respect=0, prestige_multiplier=1.0, territory_bonus=0.0, is_vip=False, equip_income_bonus=0, upgrade_income_bonus=0, gang_income_bonus=0, gang_raid_reduction=0, talent_offline_hours=0, talent_raid_reduce=0, talent_income_bonus=0, talent_suspicion_reduce=0):
    """
    Calculate earnings while player was away.
    Returns (earned_cash, new_suspicion, was_raided).
    """
    now = time.time()
    elapsed = now - last_ts
    if elapsed <= 0:
        return 0, current_suspicion, False

    # Cap offline earnings: 8 hours for VIP, 4 hours for regular + talent bonus
    base_hours = 8 if is_vip else 4
    max_offline = (base_hours + talent_offline_hours) * 3600
    elapsed = min(elapsed, max_offline)

    vip_multiplier = 2.0 if is_vip else 1.0
    income_per_sec, suspicion_per_sec = calc_total_income(owned_businesses, fear, respect, prestige_multiplier, territory_bonus, vip_multiplier=vip_multiplier, equip_income_bonus=equip_income_bonus, upgrade_income_bonus=upgrade_income_bonus, gang_income_bonus=gang_income_bonus, talent_income_bonus=talent_income_bonus, talent_suspicion_reduce=talent_suspicion_reduce)
    earned = income_per_sec * elapsed

    new_suspicion = current_suspicion + suspicion_per_sec * elapsed
    new_suspicion = max(0, min(MAX_SUSPICION, new_suspicion))

    was_raided = False
    if new_suspicion >= RAID_THRESHOLD:
        was_raided = True
        raid_penalty = max(0, RAID_CASH_PENALTY - gang_raid_reduction / 100.0 - talent_raid_reduce / 100.0)
        earned *= (1 - raid_penalty)
        new_suspicion = max(0, new_suspicion - 40)

    return round(earned, 2), round(new_suspicion, 2), was_raided


def attempt_robbery(robbery_id, player_fear=0, reward_bonus_pct=0):
    """
    Attempt a robbery. Fear increases success chance slightly.
    reward_bonus_pct: % bonus from big_loot talent.
    Returns (success, reward, suspicion_gain).
    """
    cfg = ALL_ROBBERIES.get(robbery_id)
    if not cfg:
        return False, 0, 0

    fear_bonus = min(player_fear * 0.005, 0.15)
    chance = min(cfg["success_chance"] + fear_bonus, 0.95)

    success = random.random() < chance
    if success:
        reward = random.uniform(cfg["min_reward"], cfg["max_reward"])
        reward *= (1 + reward_bonus_pct / 100.0)
        return True, round(reward, 2), cfg["suspicion_gain"]
    else:
        penalty_suspicion = cfg["suspicion_gain"] * 0.5
        return False, 0, round(penalty_suspicion, 2)


def get_buy_cost(business_id, current_level, fear=0, respect=0, talent_discount=0):
    """Get cost to buy/upgrade a business, applying reputation + talent discounts."""
    cfg = ALL_BUSINESSES.get(business_id)
    if not cfg:
        return None

    level = current_level if current_level > 0 else 1
    cost = calc_business_cost(cfg, level)

    if cfg["type"] == "shadow":
        discount = min(fear * FEAR_SHADOW_DISCOUNT, 0.3)
    else:
        discount = min(respect * RESPECT_LEGAL_DISCOUNT, 0.3)

    discount += talent_discount / 100.0
    discount = min(discount, 0.5)  # cap total discount at 50%

    return round(cost * (1 - discount), 2)


def get_player_level(owned_businesses):
    """Player level = sum of all business levels."""
    return sum(b["level"] for b in owned_businesses)
