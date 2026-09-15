import json
import os
import random
import shutil
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from filelock import FileLock

from baleio import Bot, Dispatcher, md, F
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.filters import Command, CommandStart
from baleio.fsm import FSMContext, State, StatesGroup
from baleio.types import Message, CallbackQuery, PreCheckoutQuery
from baleio.utils import InlineKeyboardBuilder

# ==================== تنظیمات ====================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN تنظیم نشده!")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "WALLET-TEST-1111111111111111")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "data.json"
BACKUP_FILE = "data_backup.json"
LOCK_FILE = "data.lock"
lock = FileLock(LOCK_FILE, timeout=10)

# ==================== میوه‌ها ====================
FRUITS = ["توت‌فرنگی", "گوجه", "سیب", "پرتقال", "نارگیل", "آناناس", "میوه اژدها"]
PRICES = [(1, 3), (15, 38), (304, 760), (9120, 22800),
          (456000, 1140000), (27360000, 68400000), (2052000000, 5130000000)]
GROWTH_TIMES = [1, 2.5, 4, 5.5, 7, 8.5, 10]

XP_REQUIRED = {1: 5, 2: 30, 3: 75, 4: 250, 5: 1000, 6: 5000}
XP_FROM_SALES = {"توت‌فرنگی": (1, 1), "گوجه": (2, 3), "سیب": (4, 6),
                 "پرتقال": (8, 12), "نارگیل": (20, 30), "آناناس": (35, 65)}

LEVEL_UNLOCKS = {
    1: {"fruits": [0], "features": ["status", "pet"]},
    2: {"fruits": [0, 1], "features": ["status", "pet", "leaderboard"]},
    3: {"fruits": [0, 1, 2], "features": ["status", "pet", "leaderboard", "upgrades"]},
    4: {"fruits": [0, 1, 2, 3], "features": ["status", "pet", "leaderboard", "upgrades", "daily_orders", "shop"]},
    5: {"fruits": [0, 1, 2, 3, 4], "features": ["status", "pet", "leaderboard", "upgrades", "daily_orders", "shop", "worker", "clan"]},
    6: {"fruits": [0, 1, 2, 3, 4, 5], "features": ["status", "pet", "leaderboard", "upgrades", "daily_orders", "shop", "worker", "clan", "gift"]},
    7: {"fruits": [0, 1, 2, 3, 4, 5, 6], "features": ["status", "pet", "leaderboard", "upgrades", "daily_orders", "shop", "worker", "clan", "gift", "prestige", "league"]},
}

ALL_FEATURES = ["status", "pet", "leaderboard", "upgrades", "daily_orders",
                "shop", "worker", "clan", "gift", "prestige", "league"]
ALL_FRUITS = [0, 1, 2, 3, 4, 5, 6]

PRESTIGE_PRICES = {1: 50_000_000_000, 2: 100_000_000_000, 3: 200_000_000_000,
                   4: 500_000_000_000, 5: 725_000_000_000, 6: 1_000_000_000_000,
                   7: 1_500_000_000_000, 8: 2_500_000_000_000,
                   9: 5_000_000_000_000, 10: 10_000_000_000_000}

SHOP_PRICES = {
    4: {5000: 114000, 10000: 228000, 20000: 456000, 50000: 1140000, 70000: 1600000, 100000: 2280000},
    5: {5000: 5700000, 10000: 11400000, 20000: 22800000, 50000: 57000000, 70000: 80000000, 100000: 114000000},
    6: {5000: 342000000, 10000: 684000000, 20000: 1368000000, 50000: 3420000000, 70000: 4800000000, 100000: 6840000000},
    7: {5000: 25650000000, 10000: 51300000000, 20000: 102600000000, 50000: 256500000000, 70000: 360000000000, 100000: 513000000000},
}

INVENTORY_CAPACITY = {1: 1, 2: 2, 3: 3, 4: 5, 5: 8, 6: 12, 7: 20}
LAND_PRICES = [5000, 150000, 6000000, 100000000]
MAX_PLOTS = 5

SEASON_CYCLE = ["spring", "summer", "autumn", "winter"]
SEASON_DURATION_MIN = 45
SEASON_FA = {"spring": "🌸 بهار", "summer": "☀️ تابستان", "autumn": "🍂 پاییز", "winter": "❄️ زمستان"}

PHOENIX_PET = {"name": "ققنوس", "emoji": "🦅", "type": "sell", "value": 100}

PET_EGGS = {
    "common": {"price": 50, "name": "معمولی 🥚", "pets": [
        {"name": "مرغ", "emoji": "🐔", "chance": 40, "type": "sell", "value": 2},
        {"name": "گربه", "emoji": "🐈", "chance": 30, "type": "speed", "value": 3},
        {"name": "گاو", "emoji": "🐄", "chance": 20, "type": "xp", "value": 4},
        {"name": "گوسفند", "emoji": "🐑", "chance": 10, "type": "sell", "value": 5},
    ]},
    "uncommon": {"price": 1000, "name": "غیرمعمولی 🥚", "pets": [
        {"name": "سگ", "emoji": "🐕", "chance": 40, "type": "speed", "value": 5},
        {"name": "خرگوش", "emoji": "🐇", "chance": 30, "type": "xp", "value": 6},
        {"name": "اردک", "emoji": "🦆", "chance": 20, "type": "sell", "value": 7},
        {"name": "لاک‌پشت", "emoji": "🐢", "chance": 10, "type": "sell", "value": 9},
    ]},
    "rare": {"price": 30000, "name": "کمیاب 🥚", "pets": [
        {"name": "بز", "emoji": "🐐", "chance": 40, "type": "xp", "value": 9},
        {"name": "مار", "emoji": "🐍", "chance": 30, "type": "sell", "value": 11},
        {"name": "عنکبوت", "emoji": "🕷", "chance": 20, "type": "speed", "value": 13},
        {"name": "موش کور", "emoji": "🦫", "chance": 10, "type": "xp", "value": 16},
    ]},
    "epic": {"price": 1250000, "name": "حماسی 🥚", "pets": [
        {"name": "روباه", "emoji": "🦊", "chance": 40, "type": "sell", "value": 15},
        {"name": "خرس", "emoji": "🐻", "chance": 30, "type": "speed", "value": 18},
        {"name": "ببر", "emoji": "🐯", "chance": 20, "type": "xp", "value": 22},
        {"name": "شیر", "emoji": "🦁", "chance": 10, "type": "sell", "value": 27},
    ]},
    "legendary": {"price": 75000000, "name": "افسانه‌ای 🥚", "pets": [
        {"name": "عقاب", "emoji": "🦅", "chance": 40, "type": "xp", "value": 25},
        {"name": "طاووس", "emoji": "🦚", "chance": 30, "type": "sell", "value": 30},
        {"name": "ایگوانا", "emoji": "🦎", "chance": 20, "type": "speed", "value": 38},
        {"name": "هزارپا", "emoji": "🐛", "chance": 10, "type": "sell", "value": 48},
    ]},
    "mythic": {"price": 10000000000, "name": "اساطیری 🥚", "pets": [
        {"name": "جگوار", "emoji": "🐆", "chance": 40, "type": "sell", "value": 45},
        {"name": "کرگدن", "emoji": "🦏", "chance": 30, "type": "speed", "value": 55},
        {"name": "کروکودیل", "emoji": "🐊", "chance": 20, "type": "speed", "value": 65},
        {"name": "غژگاو", "emoji": "🐃", "chance": 10, "type": "sell", "value": 75},
    ]},
}

CLAN_CREATE_COST = 500000
CLAN_LEVEL_COSTS = {1: 0, 2: 1000000, 3: 5000000, 4: 25000000, 5: 100000000,
                    6: 500000000, 7: 2500000000, 8: 10000000000,
                    9: 50000000000, 10: 250000000000}
CLAN_MAX_MEMBERS = {1: 10, 2: 10, 3: 15, 4: 15, 5: 20, 6: 25, 7: 30, 8: 40, 9: 45, 10: 50}
CLAN_BONUS_PER_LEVEL = 2
LEAGUE_FA = {0: "I", 1: "II", 2: "III", 3: "IV", 4: "V", 5: "VI",
             6: "VII", 7: "VIII", 8: "IX", 9: "X", 10: "XI"}

# ==================== ادمین ====================
def is_admin(user_id):
    return ADMIN_ID != 0 and int(user_id) == ADMIN_ID

class UserForm(StatesGroup):
    name = State()
    gift_target = State()
    gift_amount = State()
    clan_name = State()
    clan_invite = State()
    clan_donate = State()
    clan_chat = State()
    plant_plot = State()

# ==================== دیتابیس ====================
def create_default_data():
    return {
        "game_start_time": datetime.now().isoformat(),
        "users": {}, "leaderboard": [], "clans": {}, "leagues": {},
        "active_event": None,
        "gift_codes": {},
        "banned": [],
    }

def create_default_user(user_id):
    now = datetime.now().isoformat()
    return {
        "name": "", "level": 1, "xp": 0, "coins": 1,
        "plots": [{"fruit": 0, "state": "idle", "harvest_time": None}],
        "max_plots": 1, "current_fruit": 0, "inventory": {},
        "upgrades": {"auto_water": 0, "golden_pot": 0, "professional_seeder": 0},
        "worker": {"level": 1, "active": False},
        "daily_orders": {"date": "", "orders": [], "completed": False},
        "prestige": 0, "prestige_multiplier": 1.0,
        "gifts_given": 0, "gifts_received": 0,
        "referral_code": f"REF{user_id}{random.randint(100,999)}",
        "pet": None, "phoenix_owned": False, "clan_id": None,
        "period_start_coins": 1, "period_start_time": now,
        "current_period": 1, "last_seen_period": 1,
        "achievements": [], "pending_purchase": None,
        "used_gift_codes": [],
    }

def _ensure_keys(data):
    if not isinstance(data, dict):
        return create_default_data()
    for k, v in create_default_data().items():
        if k not in data:
            data[k] = v
    return data

def _migrate_user(u, gst):
    inv = u.get("inventory", [])
    if isinstance(inv, list):
        new_inv = {}
        for item in inv:
            new_inv[item] = new_inv.get(item, 0) + 1
        u["inventory"] = new_inv
    elif not isinstance(inv, dict):
        u["inventory"] = {}
    if "plots" not in u:
        old_fruit = u.get("current_fruit", 0)
        old_state = u.get("state", "idle")
        old_ht = u.get("harvest_time")
        u["plots"] = [{"fruit": old_fruit, "state": old_state, "harvest_time": old_ht}]
        u["max_plots"] = 1
    for k in ["state", "harvest_time"]:
        u.pop(k, None)
    defaults = {
        "max_plots": 1, "current_fruit": 0, "pet": None, "phoenix_owned": False,
        "clan_id": None, "achievements": [], "pending_purchase": None,
        "period_start_coins": 1, "period_start_time": gst,
        "current_period": 1, "last_seen_period": 1,
        "gifts_given": 0, "gifts_received": 0, "used_gift_codes": [],
    }
    for k, v in defaults.items():
        if k not in u:
            u[k] = v

def load_data():
    with lock:
        if not os.path.exists(DATA_FILE):
            if os.path.exists(BACKUP_FILE):
                try: shutil.copy(BACKUP_FILE, DATA_FILE)
                except: pass
            else:
                d = create_default_data()
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
                return d
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data = _ensure_keys(data)
            gst = data.get("game_start_time", datetime.now().isoformat())
            for uid, u in data.get("users", {}).items():
                _migrate_user(u, gst)
            return data
        except Exception:
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                        return _ensure_keys(json.load(f))
                except: pass
            d = create_default_data()
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            return d

def save_data(data):
    with lock:
        data = _ensure_keys(data)
        tf = DATA_FILE + ".tmp"
        try:
            with open(tf, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except: return False
        if os.path.exists(DATA_FILE):
            try: shutil.copy(DATA_FILE, BACKUP_FILE)
            except: pass
        try:
            os.replace(tf, DATA_FILE); return True
        except:
            if os.path.exists(BACKUP_FILE): shutil.copy(BACKUP_FILE, DATA_FILE)
            return False

def get_user(user_id):
    return load_data()["users"].get(str(user_id))

def update_user(user_id, updates):
    data = load_data()
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = create_default_user(user_id)
    data["users"][str(user_id)].update(updates)
    save_data(data)

def update_leaderboard(user_id, name, coins, level, prestige):
    data = load_data()
    data["leaderboard"] = [i for i in data["leaderboard"] if i.get("user_id") != str(user_id)]
    data["leaderboard"].append({"user_id": str(user_id), "name": name,
                                 "coins": coins, "level": level, "prestige": prestige})
    data["leaderboard"].sort(key=lambda x: (x["prestige"], x["level"], x["coins"]), reverse=True)
    data["leaderboard"] = data["leaderboard"][:50]
    save_data(data)

def find_user_by_name_or_code(query):
    data = load_data()
    q = query.lower()
    for uid, u in data["users"].items():
        if u.get("name", "").lower() == q: return uid, u
        if u.get("referral_code", "").lower() == q: return uid, u
    return None, None

# ==================== ایونت ====================
def get_active_event():
    data = load_data()
    ev = data.get("active_event")
    if not ev: return None
    try:
        end = datetime.fromisoformat(ev["end_time"])
        if datetime.now() >= end:
            data["active_event"] = None
            save_data(data)
            return None
    except: return None
    return ev

# ==================== انبار ====================
def get_inv_count(user):
    return sum(user.get("inventory", {}).values())

def get_inv_capacity(user):
    return INVENTORY_CAPACITY.get(user.get("level", 1), 1)

def add_to_inventory(user_id, fruit_name):
    user = get_user(user_id)
    if not user: return False
    if get_inv_count(user) >= get_inv_capacity(user): return False
    inv = user.get("inventory", {})
    inv[fruit_name] = inv.get(fruit_name, 0) + 1
    update_user(user_id, {"inventory": inv})
    return True

# ==================== زمین‌ها ====================
def get_plot_remaining(plot):
    if plot.get("state") != "growing": return None
    ht = plot.get("harvest_time")
    if not ht: return None
    try:
        return max(0, int((datetime.fromisoformat(ht) - datetime.now()).total_seconds()))
    except: return None

def check_all_harvests(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user: return False
    changed = False
    for plot in user.get("plots", []):
        if plot.get("state") == "growing":
            ht = plot.get("harvest_time")
            if ht:
                try:
                    if datetime.now() >= datetime.fromisoformat(ht):
                        plot["state"] = "harvested"
                        plot["harvest_time"] = None
                        changed = True
                except: pass
    if changed:
        data["users"][str(user_id)] = user
        save_data(data)
    return changed

# ==================== فصل و ایونت ====================
def get_current_season():
    data = load_data()
    s = data.get("game_start_time", datetime.now().isoformat())
    try:
        start = datetime.fromisoformat(s)
        elapsed = (datetime.now() - start).total_seconds() / 60
        return SEASON_CYCLE[int(elapsed // SEASON_DURATION_MIN) % len(SEASON_CYCLE)]
    except: return "spring"

def get_season_effects():
    season = get_current_season()
    e = {"growth_mult": 1.0, "sell_mult": 1.0, "buy_mult": 1.0, "golden_chance": 0.02, "xp_mult": 1.0}
    if season == "spring": e["growth_mult"] = 1 / 1.2
    elif season == "summer": e["golden_chance"] = 0.02 * 1.75
    elif season == "autumn": e["sell_mult"] = random.uniform(1.25, 1.5)
    elif season == "winter": e["buy_mult"] = 1 / 1.2
    
    # ✅ اعمال ایونت فعال
    ev = get_active_event()
    if ev:
        e["buy_mult"] *= ev.get("buy_mult", 1.0)
        e["sell_mult"] *= ev.get("sell_mult", 1.0)
        e["growth_mult"] *= ev.get("growth_mult", 1.0)
        e["xp_mult"] *= ev.get("xp_mult", 1.0)
    
    return e, season

# ==================== پت ====================
def get_pet_effect(user, t):
    pet = user.get("pet")
    if not pet: return 0
    return pet.get("value", 0) if pet.get("type") == t else 0

def spin_egg(egg_type):
    if egg_type not in PET_EGGS: return None
    pets = PET_EGGS[egg_type]["pets"]
    r = random.randint(1, 100); c = 0
    for p in pets:
        c += p["chance"]
        if r <= c: return p
    return pets[-1]

# ==================== کلن ====================
def get_clan(clan_id):
    return load_data()["clans"].get(clan_id)

def create_clan(clan_id, name, lid, lname):
    data = load_data()
    if clan_id in data["clans"]: return False
    data["clans"][clan_id] = {"name": name, "leader_id": lid, "leader_name": lname,
        "level": 1, "treasury": 0, "members": [lid],
        "member_names": {lid: lname}, "created_at": datetime.now().isoformat()}
    save_data(data); return True

def get_clan_bonus(user):
    if not user.get("clan_id"): return 0
    clan = get_clan(user["clan_id"])
    return clan["level"] * CLAN_BONUS_PER_LEVEL if clan else 0

# ==================== لیگ ====================
def get_week_number(s, now=None):
    start = datetime.fromisoformat(s)
    if now is None: now = datetime.now()
    return int((now - start).total_seconds() / (7 * 24 * 3600)) + 1

def get_period_number():
    data = load_data()
    s = data.get("game_start_time")
    return get_week_number(s) if s else 1

def process_period_end(pn, user, uid_str):
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0: return
    pk = str(user.get("prestige", 0))
    data = load_data()
    leagues = data.get("leagues", {})
    per_key = f"period_{pn}"
    if pk not in leagues or per_key not in leagues[pk]: return
    members = leagues[pk][per_key].get("members", {})
    if uid_str not in members: return
    total = len(members)
    if total == 0: return
    sm = sorted(members.items(), key=lambda x: x[1].get("profit", 0), reverse=True)
    rank = next((i+1 for i, (uid, _) in enumerate(sm) if uid == uid_str), 0)
    if rank == 0: return
    ach_date = datetime.now().strftime("%Y-%m-%d")
    prestige = user.get("prestige", 0)
    if total < 10:
        user.setdefault("achievements", []).append(
            {"type": "lone_eagle", "rank": rank, "period": pn, "league": prestige, "date": ach_date})
        return
    if rank == 1:
        user.setdefault("achievements", []).append(
            {"type": "medal_gold", "rank": 1, "period": pn, "league": prestige, "date": ach_date})
    elif rank == 2 and total >= 31:
        user.setdefault("achievements", []).append(
            {"type": "medal_silver", "rank": 2, "period": pn, "league": prestige, "date": ach_date})
    elif rank == 3 and total >= 41:
        user.setdefault("achievements", []).append(
            {"type": "medal_bronze", "rank": 3, "period": pn, "league": prestige, "date": ach_date})
    pct = max(1, int((rank / total) * 100))
    if pct <= 10:
        user.setdefault("achievements", []).append(
            {"type": "top_percent", "percent": pct, "period": pn, "league": prestige, "date": ach_date})

def check_period_reset(user_id):
    data = load_data()
    cp = get_period_number()
    user = data["users"].get(str(user_id))
    if not user: return False
    lp = user.get("last_seen_period", cp)
    if cp > lp:
        for p in range(lp, cp):
            process_period_end(p, user, str(user_id))
        user["period_start_coins"] = user["coins"]
        user["period_start_time"] = datetime.now().isoformat()
        user["current_period"] = cp
        user["last_seen_period"] = cp
        data["users"][str(user_id)] = user
        save_data(data); return True
    return False

def update_league_profit(user_id, user, profit):
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0: return
    pk = str(user.get("prestige", 0))
    pn = user.get("current_period", 1)
    per_key = f"period_{pn}"
    data = load_data()
    data.setdefault("leagues", {}).setdefault(pk, {}).setdefault(per_key, {"started_at": user.get("period_start_time"), "members": {}})
    data["leagues"][pk][per_key]["members"][str(user_id)] = {
        "name": user.get("name", "?"), "profit": profit}
    save_data(data)

# ==================== توابع کمکی ====================
def get_available_fruits(user):
    if user.get("prestige", 0) > 0: return ALL_FRUITS
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["fruits"]

def get_available_features(user):
    if user.get("prestige", 0) > 0: return ALL_FEATURES
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["features"]

def has_feature(user, f): return f in get_available_features(user)
def xp_needed_for(l): return XP_REQUIRED.get(l, 999999)
def xp_from_sale(f): return random.randint(*XP_FROM_SALES[f]) if f in XP_FROM_SALES else 0
def get_land_price(cp):
    if cp >= MAX_PLOTS: return None
    return LAND_PRICES[cp - 1]

def is_banned(user_id):
    data = load_data()
    return str(user_id) in data.get("banned", [])

# ==================== کیبورد ====================
def get_keyboard(user_id):
    user = get_user(user_id)
    if not user: return InlineKeyboardBuilder().as_markup()
    kb = InlineKeyboardBuilder()
    plots = user.get("plots", [])
    max_plots = user.get("max_plots", 1)
    
    if max_plots == 1:
        plot = plots[0]
        cf = plot.get("fruit", 0)
        fruit = FRUITS[cf]
        if plot["state"] == "growing":
            rem = get_plot_remaining(plot)
            if rem is not None and rem > 0:
                kb.button(f"⏳ در حال رشد ({rem//60}:{rem%60:02d})", callback_data="noop")
            else:
                kb.button("⏳ در حال رشد...", callback_data="noop")
            kb.button("⏳ هنوز نرسیده!", callback_data="noop")
        elif plot["state"] == "harvested":
            kb.button(f"📦 برداشت {fruit}", callback_data="harvest_0")
        else:
            kb.button("🌱 خرید بذر", callback_data="buy_0")
        kb.adjust(2)
    else:
        kb.button("🏞️ زمین‌ها", callback_data="lands_menu")
        kb.button("📦 انبار", callback_data="inventory_menu")
        kb.adjust(2)
    
    kb.button("📊 وضعیت", callback_data="status")
    if max_plots == 1:
        kb.button("📦 انبار", callback_data="inventory_menu")
    if has_feature(user, "pet"): kb.button("🐾 پت", callback_data="pet_menu")
    if has_feature(user, "leaderboard"): kb.button("🏆 لیدربرد", callback_data="leaderboard")
    if has_feature(user, "upgrades"): kb.button("🔧 ارتقاء ابزار", callback_data="upgrades")
    if has_feature(user, "daily_orders"): kb.button("📦 سفارشات روزانه", callback_data="daily_orders")
    if has_feature(user, "shop"): kb.button("🛒 فروشگاه سکه", callback_data="shop")
    if has_feature(user, "worker"): kb.button("👷 کارگر", callback_data="worker_menu")
    if has_feature(user, "clan"): kb.button("🏰 کلن", callback_data="clan_menu")
    if has_feature(user, "gift"): kb.button("🎁 هدیه دادن", callback_data="gift")
    if has_feature(user, "league"):
        kb.button("🏅 لیگ", callback_data="league_menu")
        kb.button("🎖️ افتخارات", callback_data="achievements")
    if has_feature(user, "prestige") and user["level"] >= 7:
        kb.button("⭐ پرستیژ", callback_data="prestige_menu")
    if is_admin(user_id):
        kb.button("👑 پنل ادمین", callback_data="admin_panel")
    kb.adjust(2)
    return kb.as_markup()

# ==================== متن وضعیت ====================
def build_status_text(user, user_id):
    effects, season = get_season_effects()
    mult = user["prestige_multiplier"]
    feats = get_available_features(user)
    profit = user["coins"] - user.get("period_start_coins", 1)
    pn = user.get("current_period", 1)
    inv_count = get_inv_count(user)
    inv_cap = get_inv_capacity(user)
    
    text = (f"📊 **وضعیت {user['name']}:**\n"
            f"💰 سکه: {user['coins']:,}\n"
            f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
            f"🌤 فصل: {SEASON_FA[season]}\n")
    
    # ✅ نمایش ایونت فعال
    ev = get_active_event()
    if ev:
        try:
            end = datetime.fromisoformat(ev["end_time"])
            rem = end - datetime.now()
            h = int(rem.total_seconds() // 3600)
            m = int((rem.total_seconds() % 3600) // 60)
            text += f"🎉 **ایونت فعال!** ({h}s {m}d باقی)\n"
            text += f"  💰 خرید ×{ev['buy_mult']} | 💵 فروش ×{ev['sell_mult']}\n"
            text += f"  ⚡ رشد ×{ev['growth_mult']} | ⭐ XP ×{ev['xp_mult']}\n"
        except: pass
    
    if "prestige" in feats:
        text += f"⭐ پرستیژ: {user['prestige']} | ضریب: {mult:.2f}x\n"
    if "league" in feats:
        text += f"💵 سود دوره {pn}: {profit:,}\n"
    if "pet" in feats:
        pet = user.get("pet")
        if pet:
            tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
            pet_text = f"{pet['emoji']} {pet['name']} (+{pet['value']}٪ {tfa.get(pet['type'], '')})"
        else: pet_text = "ندارد"
        text += f"🐾 پت: {pet_text}\n"
    text += f"📦 انبار: {inv_count}/{inv_cap}\n"
    text += f"🏞️ زمین‌ها: {user.get('max_plots', 1)}\n"
    if "worker" in feats:
        w = user["worker"]
        text += f"👷 کارگر: لول {w['level']} ({'فعال' if w['active'] else 'غیرفعال'})\n"
    if "clan" in feats:
        if user.get("clan_id"):
            clan = get_clan(user["clan_id"])
            if clan: text += f"🏰 کلن: {clan['name']} (لول {clan['level']})\n"
        else: text += f"🏰 کلن: بدون کلن\n"
    if "gift" in feats:
        text += f"🎁 هدیه: {user.get('gifts_given',0)} | {user.get('gifts_received',0)}\n"
    if "league" in feats:
        rank = get_user_league_rank(user_id, user)
        text += f"🏅 رتبه لیگ: {rank}\n"
        text += f"🎖️ افتخارات: {len(user.get('achievements', []))}\n"
    
    plots = user.get("plots", [])
    if len(plots) > 1:
        text += f"\n🏞️ **زمین‌ها:**\n"
        for i, p in enumerate(plots):
            fruit = FRUITS[p.get("fruit", 0)]
            if p["state"] == "growing":
                rem = get_plot_remaining(p)
                if rem is not None:
                    text += f"• زمین {i+1}: 🍅 {fruit} ({rem//60}:{rem%60:02d})\n"
                else: text += f"• زمین {i+1}: 🍅 {fruit} (در حال رشد)\n"
            elif p["state"] == "harvested":
                text += f"• زمین {i+1}: 📦 {fruit} (برداشت)\n"
            else: text += f"• زمین {i+1}: خالی\n"
    
    text += f"\n🌱 میوه انتخابی: {FRUITS[user['current_fruit']]}\n\n🍎 **قیمت‌ها:**\n"
    for i in get_available_fruits(user):
        bp = int(PRICES[i][0] * mult * effects["buy_mult"])
        sp = int(PRICES[i][1] * mult * effects["sell_mult"])
        mark = "✅ " if i == user["current_fruit"] else ""
        text += f"{mark}{FRUITS[i]}: خرید {bp:,} | فروش {sp:,}\n"
    return text

def get_user_league_rank(user_id, user):
    pk = str(user.get("prestige", 0))
    pn = user.get("current_period", 1)
    per_key = f"period_{pn}"
    data = load_data()
    leagues = data.get("leagues", {})
    if pk not in leagues or per_key not in leagues[pk]: return "—"
    members = leagues[pk][per_key].get("members", {})
    if str(user_id) not in members: return "—"
    sm = sorted(members.items(), key=lambda x: x[1].get("profit", 0), reverse=True)
    for i, (uid, _) in enumerate(sm, 1):
        if uid == str(user_id): return f"#{i} از {len(members)}"
    return "—"

# ==================== راه‌اندازی ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# ==================== دستورات ادمین ====================
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    if not is_admin(uid):
        await message.answer("⛔ دسترسی ندارید.")
        return
    text = ("👑 **پنل ادمین**\n\n"
            "**دستورات کاربری:**\n"
            "`/user_info <user_id>` — اطلاعات کاربر\n"
            "`/give_coins <user_id> <مقدار>` — دادن سکه\n"
            "`/set_coins <user_id> <مقدار>` — تنظیم سکه\n"
            "`/set_level <user_id> <لول>` — تنظیم لول\n"
            "`/set_xp <user_id> <xp>` — تنظیم XP\n"
            "`/set_prestige <user_id> <پرستیژ>` — تنظیم پرستیژ\n"
            "`/give_pet <user_id> <نوع>` — دادن پت\n"
            "  انواع: `phoenix`, `sell`, `speed`, `xp`\n"
            "`/reset_user <user_id>` — ریست کامل\n"
            "`/ban <user_id>` — بن\n"
            "`/unban <user_id>` — آنبن\n\n"
            "**مدیریت:**\n"
            "`/stats` — آمار کلی\n"
            "`/broadcast <پیام>` — پیام به همه\n"
            "`/reset_season` — ریست فصل\n"
            "`/reset_league` — ریست لیگ\n"
            "`/events` — مشاهده ایونت فعال\n"
            "`/end_event` — پایان ایونت\n\n"
            "**ایونت:**\n"
            "`/event <buy> <sell> <growth> <xp> <ساعت> <پیام>`\n\n"
            "**گیفت کد:**\n"
            "`/giftcode <مقدار> <all|عدد> <ساعت> <کد>`\n"
            "مثال: `/giftcode 100000 all 3 /yalda`")
    await message.answer(text)

@dp.message(Command("user_info"))
async def cmd_user_info(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ `/user_info <user_id>`"); return
    target = get_user(parts[1])
    if not target:
        await message.answer("❌ کاربر پیدا نشد."); return
    text = (f"👤 **کاربر {parts[1]}**\n"
            f"نام: {target.get('name', '?')}\n"
            f"💰 سکه: {target['coins']:,}\n"
            f"📈 لول: {target['level']} | XP: {target['xp']}\n"
            f"⭐ پرستیژ: {target.get('prestige', 0)}\n"
            f"📦 انبار: {get_inv_count(target)}/{get_inv_capacity(target)}\n"
            f"🏞️ زمین‌ها: {target.get('max_plots', 1)}\n"
            f"🐾 پت: {target.get('pet', {}).get('name', 'ندارد') if target.get('pet') else 'ندارد'}\n"
            f"🏰 کلن: {target.get('clan_id', 'ندارد')}\n"
            f"🎖️ افتخارات: {len(target.get('achievements', []))}\n"
            f"🎁 هدیه: {target.get('gifts_given',0)} | {target.get('gifts_received',0)}")
    await message.answer(text)

@dp.message(Command("give_coins"))
async def cmd_give_coins(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ `/give_coins <user_id> <مقدار>`"); return
    try: amt = int(parts[2])
    except: await message.answer("❌ مقدار نامعتبر."); return
    target = get_user(parts[1])
    if not target:
        await message.answer("❌ کاربر پیدا نشد."); return
    new_coins = target["coins"] + amt
    update_user(int(parts[1]), {"coins": new_coins})
    update_leaderboard(int(parts[1]), target["name"], new_coins, target["level"], target["prestige"])
    await message.answer(f"✅ {amt:,} سکه به {target['name']} داده شد.\nموجودی جدید: {new_coins:,}")

@dp.message(Command("set_coins"))
async def cmd_set_coins(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 3: return
    try: amt = int(parts[2])
    except: return
    target = get_user(parts[1])
    if not target:
        await message.answer("❌ کاربر پیدا نشد."); return
    update_user(int(parts[1]), {"coins": amt})
    update_leaderboard(int(parts[1]), target["name"], amt, target["level"], target["prestige"])
    await message.answer(f"✅ سکه {target['name']} تنظیم شد به {amt:,}")

@dp.message(Command("set_level"))
async def cmd_set_level(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 3: return
    try: lv = int(parts[2])
    except: return
    if lv < 1 or lv > 7: await message.answer("❌ لول ۱ تا ۷"); return
    target = get_user(parts[1])
    if not target: await message.answer("❌ کاربر پیدا نشد."); return
    update_user(int(parts[1]), {"level": lv})
    await message.answer(f"✅ لول {target['name']} = {lv}")

@dp.message(Command("set_xp"))
async def cmd_set_xp(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 3: return
    try: xp = int(parts[2])
    except: return
    target = get_user(parts[1])
    if not target: await message.answer("❌ کاربر پیدا نشد."); return
    update_user(int(parts[1]), {"xp": xp})
    await message.answer(f"✅ XP {target['name']} = {xp}")

@dp.message(Command("set_prestige"))
async def cmd_set_prestige(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 3: return
    try: p = int(parts[2])
    except: return
    if p < 0 or p > 10: return
    target = get_user(parts[1])
    if not target: return
    mult = 1.5 ** p
    update_user(int(parts[1]), {"prestige": p, "prestige_multiplier": mult})
    await message.answer(f"✅ پرستیژ {target['name']} = {p} (ضریب {mult:.2f}x)")

@dp.message(Command("give_pet"))
async def cmd_give_pet(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 3: return
    target = get_user(parts[1])
    if not target: return
    t = parts[2].lower()
    if t == "phoenix":
        update_user(int(parts[1]), {"pet": PHOENIX_PET, "phoenix_owned": True})
        await message.answer(f"✅ ققنوس به {target['name']} داده شد.")
    elif t in ["sell", "speed", "xp"]:
        pet = {"name": f"پت {t}", "emoji": "🐾", "type": t, "value": 50}
        update_user(int(parts[1]), {"pet": pet})
        await message.answer(f"✅ پت {t} (۵۰٪) به {target['name']} داده شد.")
    else:
        await message.answer("❌ نوع نامعتبر. phoenix / sell / speed / xp")

@dp.message(Command("reset_user"))
async def cmd_reset_user(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 2: return
    target = get_user(parts[1])
    if not target: return
    name = target["name"]
    ref = target["referral_code"]
    ach = target.get("achievements", [])
    nu = create_default_user(int(parts[1]))
    nu["name"] = name
    nu["referral_code"] = ref
    nu["achievements"] = ach
    data = load_data()
    data["users"][parts[1]] = nu
    save_data(data)
    await message.answer(f"✅ کاربر {name} ریست شد (نام و افتخارات حفظ شد).")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 2: return
    data = load_data()
    if parts[1] not in data.get("banned", []):
        data.setdefault("banned", []).append(parts[1])
        save_data(data)
    await message.answer(f"🚫 کاربر {parts[1]} بن شد.")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    parts = message.text.split()
    if len(parts) < 2: return
    data = load_data()
    if parts[1] in data.get("banned", []):
        data["banned"].remove(parts[1])
        save_data(data)
    await message.answer(f"✅ کاربر {parts[1]} آنبن شد.")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    data = load_data()
    users = data.get("users", {})
    total_coins = sum(u.get("coins", 0) for u in users.values())
    total_prestige = sum(u.get("prestige", 0) for u in users.values())
    text = (f"📊 **آمار ربات**\n\n"
            f"👥 کل کاربران: {len(users):,}\n"
            f"💰 کل سکه‌ها: {total_coins:,}\n"
            f"⭐ کل پرستیژ: {total_prestige}\n"
            f"🏰 کل کلن‌ها: {len(data.get('clans', {}))}\n"
            f"🎟️ گیفت کدهای فعال: {len([c for c in data.get('gift_codes', {}).values() if datetime.now() < datetime.fromisoformat(c['end_time'])])}\n"
            f"🎉 ایونت: {'فعال' if get_active_event() else 'غیرفعال'}\n"
            f"🚫 بن‌شده‌ها: {len(data.get('banned', []))}")
    await message.answer(text)

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("❌ متن پیام خالی است."); return
    data = load_data()
    sent = 0; failed = 0
    for u_id in data.get("users", {}).keys():
        try:
            await bot.send_message(int(u_id), f"📢 **اعلان:**\n\n{text}")
            sent += 1
        except: failed += 1
        await asyncio.sleep(0.05)
    await message.answer(f"✅ ارسال شد: {sent} | ❌ ناموفق: {failed}")

@dp.message(Command("reset_season"))
async def cmd_reset_season(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    data = load_data()
    data["game_start_time"] = datetime.now().isoformat()
    save_data(data)
    await message.answer("✅ فصل‌ها ریست شدند (از بهار شروع می‌شود).")

@dp.message(Command("reset_league"))
async def cmd_reset_league(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    data = load_data()
    data["leagues"] = {}
    save_data(data)
    await message.answer("✅ لیگ‌ها ریست شدند.")

# ==================== ایونت ====================
@dp.message(Command("event"))
async def cmd_event(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    
    parts = message.text.split(maxsplit=6)
    if len(parts) < 7:
        await message.answer(
            "❌ فرمت:\n`/event <buy> <sell> <growth> <xp> <ساعت> <پیام>`\n\n"
            "مثال:\n`/event 1.25 2 1 1.5 24 نوروز مبارک!`"
        ); return
    
    try:
        buy_mult = float(parts[1])
        sell_mult = float(parts[2])
        growth_mult = float(parts[3])
        xp_mult = float(parts[4])
        hours = float(parts[5])
        msg = parts[6]
    except Exception as e:
        await message.answer(f"❌ خطا در پارامترها: {e}"); return
    
    end_time = datetime.now() + timedelta(hours=hours)
    data = load_data()
    data["active_event"] = {
        "buy_mult": buy_mult,
        "sell_mult": sell_mult,
        "growth_mult": growth_mult,
        "xp_mult": xp_mult,
        "end_time": end_time.isoformat(),
        "message": msg,
        "created_at": datetime.now().isoformat(),
    }
    save_data(data)
    
    await message.answer(
        f"✅ **ایونت فعال شد!**\n\n"
        f"💰 خرید ×{buy_mult}\n"
        f"💵 فروش ×{sell_mult}\n"
        f"⚡ رشد ×{growth_mult}\n"
        f"⭐ XP ×{xp_mult}\n"
        f"⏰ مدت: {hours} ساعت\n"
        f"📢 پیام: {msg}"
    )
    
    # ارسال به همه کاربران
    broadcast_text = (f"🎉 **ایونت ویژه!**\n\n"
                       f"{msg}\n\n"
                       f"💰 خرید ×{buy_mult} | 💵 فروش ×{sell_mult}\n"
                       f"⚡ رشد ×{growth_mult} | ⭐ XP ×{xp_mult}\n"
                       f"⏰ {hours} ساعت فرصت داری!")
    for u_id in data.get("users", {}).keys():
        try: await bot.send_message(int(u_id), broadcast_text)
        except: pass
        await asyncio.sleep(0.05)

@dp.message(Command("end_event"))
async def cmd_end_event(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    data = load_data()
    data["active_event"] = None
    save_data(data)
    await message.answer("✅ ایونت پایان یافت.")

@dp.message(Command("events"))
async def cmd_events(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    ev = get_active_event()
    if not ev:
        await message.answer("ایونت فعالی وجود ندارد.")
        return
    end = datetime.fromisoformat(ev["end_time"])
    rem = end - datetime.now()
    h = int(rem.total_seconds() // 3600)
    m = int((rem.total_seconds() % 3600) // 60)
    await message.answer(
        f"🎉 **ایونت فعال** ({h}s {m}d باقی)\n\n"
        f"💰 خرید ×{ev['buy_mult']}\n"
        f"💵 فروش ×{ev['sell_mult']}\n"
        f"⚡ رشد ×{ev['growth_mult']}\n"
        f"⭐ XP ×{ev['xp_mult']}\n"
        f"📢 {ev['message']}"
    )

# ==================== گیفت کد ====================
@dp.message(Command("giftcode"))
async def cmd_giftcode(message: Message):
    uid = message.from_user.id
    if not is_admin(uid): return
    
    parts = message.text.split(maxsplit=4)
    if len(parts) < 5:
        await message.answer(
            "❌ فرمت:\n`/giftcode <مقدار> <all|عدد> <ساعت> <کد>`\n\n"
            "مثال:\n`/giftcode 100000 all 3 /yalda`\n"
            "`/giftcode 50000 100 24 /noruz`"
        ); return
    
    try:
        amount = int(parts[1])
        limit_str = parts[2].lower()
        hours = float(parts[3])
        code = parts[4].strip()
    except Exception as e:
        await message.answer(f"❌ خطا: {e}"); return
    
    if not code.startswith("/"):
        await message.answer("❌ کد باید با / شروع شود."); return
    if len(code) < 2:
        await message.answer("❌ کد خیلی کوتاهه."); return
    
    if limit_str == "all":
        max_users = "all"
    else:
        try: max_users = int(limit_str)
        except: await message.answer("❌ افراد باید all یا عدد باشد."); return
    
    end_time = datetime.now() + timedelta(hours=hours)
    data = load_data()
    data.setdefault("gift_codes", {})[code] = {
        "amount": amount,
        "max_users": max_users,
        "end_time": end_time.isoformat(),
        "used_by": [],
        "created_at": datetime.now().isoformat(),
    }
    save_data(data)
    
    limit_text = "همه کاربران" if max_users == "all" else f"{max_users} نفر اول"
    await message.answer(
        f"✅ **گیفت کد ساخته شد!**\n\n"
        f"🎟️ کد: `{code}`\n"
        f"💰 مبلغ: {amount:,} سکه\n"
        f"👥 محدودیت: {limit_text}\n"
        f"⏰ مدت: {hours} ساعت\n\n"
        f"کاربران با ارسال `{code}` می‌توانند دریافت کنند."
    )
    
    # ارسال به همه
    broadcast_text = (f"🎟️ **گیفت کد جدید!**\n\n"
                       f"برای دریافت {amount:,} سکه، ارسال کن:\n"
                       f"`{code}`\n\n"
                       f"⏰ فقط {hours} ساعت فرصت داری!\n"
                       f"👥 {limit_text}")
    for u_id in data.get("users", {}).keys():
        try: await bot.send_message(int(u_id), broadcast_text)
        except: pass
        await asyncio.sleep(0.05)

# ==================== هندلر گیفت کد برای کاربران ====================
@dp.message(F.text.startswith("/"))
async def handle_any_command(message: Message, state: FSMContext):
    """هندل کردن گیفت کدها (هر پیامی که با / شروع شه)"""
    text = message.text.strip()
    uid = message.from_user.id
    
    # اگه یکی از دستورات شناخته‌شده باشه، نادیده بگیر
    known = ["/start", "/status", "/gift", "/admin", "/user_info", "/give_coins",
             "/set_coins", "/set_level", "/set_xp", "/set_prestige", "/give_pet",
             "/reset_user", "/ban", "/unban", "/stats", "/broadcast",
             "/reset_season", "/reset_league", "/event", "/end_event", "/events",
             "/giftcode"]
    if text.split()[0] in known:
        return
    
    # چک کردن گیفت کد
    data = load_data()
    codes = data.get("gift_codes", {})
    if text not in codes:
        return  # کد نامعتبر - نادیده بگیر
    
    code_data = codes[text]
    
    # چک انقضا
    try:
        end = datetime.fromisoformat(code_data["end_time"])
        if datetime.now() >= end:
            await message.answer("❌ این گیفت کد منقضی شده است.")
            return
    except:
        await message.answer("❌ خطا در گیفت کد.")
        return
    
    # چک استفاده قبلی
    if str(uid) in code_data.get("used_by", []):
        await message.answer("❌ قبلاً از این گیفت کد استفاده کرده‌ای.")
        return
    
    # چک محدودیت نفرات
    max_users = code_data["max_users"]
    if max_users != "all":
        if len(code_data.get("used_by", [])) >= max_users:
            await message.answer("❌ ظرفیت این گیفت کد پر شده است.")
            return
    
    # ✅ اعطای جایزه
    user = get_user(uid)
    if not user:
        await message.answer("❌ اول /start رو بزن.")
        return
    
    amount = code_data["amount"]
    new_coins = user["coins"] + amount
    code_data.setdefault("used_by", []).append(str(uid))
    data["users"][str(uid)]["coins"] = new_coins
    data["gift_codes"][text] = code_data
    save_data(data)
    update_leaderboard(uid, user["name"], new_coins, user["level"], user["prestige"])
    
    await message.answer(
        f"🎉 **تبریک!**\n\n"
        f"✅ گیفت کد `{text}` با موفقیت استفاده شد.\n"
        f"💰 +{amount:,} سکه\n"
        f"💼 موجودی جدید: {new_coins:,}"
    )

# ==================== هندلرهای پیام اصلی ====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("🚫 شما از ربات مسدود شده‌اید.")
        return
    
    check_all_harvests(user_id); check_period_reset(user_id)
    user = get_user(user_id)
    if not user or user.get("name", "") == "":
        await state.set_state(UserForm.name)
        await message.answer("👤 لطفاً یک نام انتخاب کن (حداقل ۳ کاراکتر، بدون فاصله، تکراری نباشد):")
        return
    await show_main_menu(message)

@dp.message(Command("status"))
async def cmd_status(message: Message):
    uid = message.from_user.id
    if is_banned(uid): return
    check_all_harvests(uid); check_period_reset(uid)
    user = get_user(uid)
    if not user: return
    await message.answer(build_status_text(user, uid), reply_markup=get_keyboard(uid))

@dp.message(Command("gift"))
async def cmd_gift(message: Message, state: FSMContext):
    uid = message.from_user.id
    check_all_harvests(uid)
    user = get_user(uid)
    if not user or not has_feature(user, "gift"):
        await message.answer("🔒 لول ۶ باز می‌شود."); return
    await state.set_state(UserForm.gift_target)
    await message.answer("🎁 نام یا کد کاربر مقصد:")

@dp.message(UserForm.name)
async def process_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    name = message.text.strip()
    if len(name) < 3 or " " in name:
        await message.answer("❌ نام باید حداقل ۳ حرف و بدون فاصله باشد:")
        return
    data = load_data()
    for uid2, u in data["users"].items():
        if u.get("name", "").lower() == name.lower():
            await message.answer("❌ این نام قبلاً ثبت شده:")
            return
    update_user(uid, {"name": name})
    await state.clear()
    await message.answer(f"✅ نام '{name}' ثبت شد!")
    await show_main_menu(message)

@dp.message(UserForm.gift_target)
async def process_gift_target(message: Message, state: FSMContext):
    await state.update_data(gift_target=message.text.strip())
    await state.set_state(UserForm.gift_amount)
    await message.answer("💰 مقدار سکه:")

@dp.message(UserForm.gift_amount)
async def process_gift_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    try:
        amount = int(message.text.strip())
        if amount <= 0: raise ValueError
    except:
        await message.answer("❌ عدد مثبت وارد کن."); return
    d = await state.get_data()
    tq = d.get("gift_target")
    await state.clear()
    if user["coins"] < amount:
        await message.answer(f"❌ موجودی: {user['coins']:,}"); return
    tid, target = find_user_by_name_or_code(tq)
    if not tid or tid == str(uid):
        await message.answer("❌ کاربر پیدا نشد."); return
    update_user(uid, {"coins": user["coins"] - amount, "gifts_given": user.get("gifts_given", 0) + 1})
    update_user(int(tid), {"coins": target["coins"] + amount, "gifts_received": target.get("gifts_received", 0) + 1})
    update_leaderboard(uid, user["name"], user["coins"] - amount, user["level"], user["prestige"])
    update_leaderboard(int(tid), target["name"], target["coins"] + amount, target["level"], target["prestige"])
    await message.answer(f"✅ {amount:,} سکه به {target['name']} هدیه دادی!")

@dp.message(UserForm.clan_name)
async def process_clan_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    name = message.text.strip()
    if len(name) < 3 or len(name) > 20 or " " in name:
        await message.answer("❌ نام کلن ۳-۲۰ کاراکتر و بدون فاصله:"); return
    data = load_data()
    for cid, c in data.get("clans", {}).items():
        if c.get("name", "").lower() == name.lower():
            await message.answer("❌ تکراریه:"); return
    if user["coins"] < CLAN_CREATE_COST:
        await message.answer(f"❌ نیاز به {CLAN_CREATE_COST:,}"); await state.clear(); return
    cid = f"clan_{uid}"
    create_clan(cid, name, str(uid), user["name"])
    update_user(uid, {"clan_id": cid, "coins": user["coins"] - CLAN_CREATE_COST})
    await state.clear()
    await message.answer(f"🏰 کلن «{name}» ساخته شد!", reply_markup=get_keyboard(uid))

@dp.message(UserForm.clan_invite)
async def process_clan_invite(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("clan_id"): await state.clear(); return
    tid, target = find_user_by_name_or_code(message.text.strip())
    if not tid: await message.answer("❌ پیدا نشد."); return
    if target.get("clan_id"): await message.answer("❌ در کلن دیگه‌ایه."); return
    data = load_data()
    clan = data["clans"].get(user["clan_id"])
    if not clan: await state.clear(); return
    if len(clan["members"]) >= CLAN_MAX_MEMBERS.get(clan["level"], 10):
        await message.answer("❌ کلن پر است!"); return
    clan["members"].append(str(tid))
    clan["member_names"][str(tid)] = target["name"]
    save_data(data); update_user(int(tid), {"clan_id": user["clan_id"]})
    await state.clear()
    await message.answer(f"✅ {target['name']} اضافه شد.")

@dp.message(UserForm.clan_donate)
async def process_clan_donate(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("clan_id"): await state.clear(); return
    try:
        amount = int(message.text.strip())
        if amount < 10000: raise ValueError
    except: await message.answer("❌ حداقل ۱۰,۰۰۰"); return
    if user["coins"] < amount: await message.answer("❌ کافی نیست."); return
    data = load_data()
    clan = data["clans"].get(user["clan_id"])
    if not clan: await state.clear(); return
    clan["treasury"] += amount; save_data(data)
    update_user(uid, {"coins": user["coins"] - amount})
    await state.clear()
    await message.answer(f"✅ {amount:,} سکه اهدا شد.")

@dp.message(UserForm.clan_chat)
async def process_clan_chat(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("clan_id"): await state.clear(); return
    clan = get_clan(user["clan_id"])
    if not clan: await state.clear(); return
    msg = f"🏰 **کلن - {user['name']}:**\n\n{message.text}"
    for m in clan["members"]:
        try: await bot.send_message(int(m), msg)
        except: pass
    await state.clear()

async def show_main_menu(message: Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    _, season = get_season_effects()
    p = f"⭐ پرستیژ {user['prestige']}" if user['prestige'] > 0 else "بدون پرستیژ"
    plots = user.get("plots", [])
    plots_text = ""
    for i, pl in enumerate(plots):
        fr = FRUITS[pl.get("fruit", 0)]
        if pl["state"] == "growing":
            rem = get_plot_remaining(pl)
            t = f"{rem//60}:{rem%60:02d}" if rem else "..."
            plots_text += f"🏞 {i+1}: {fr} ({t})\n"
        elif pl["state"] == "harvested":
            plots_text += f"🏞 {i+1}: 📦 {fr}\n"
        else: plots_text += f"🏞 {i+1}: خالی\n"
    
    event_text = ""
    ev = get_active_event()
    if ev: event_text = f"\n🎉 **ایونت فعال!** {ev['message']}\n"
    
    text = (f"🌾 **مزرعه‌ی {user['name']}**\n\n"
            f"🌤 فصل: {SEASON_FA[season]}\n"
            f"💰 سکه: {user['coins']:,}\n"
            f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
            f"⭐ {p}\n"
            f"📦 انبار: {get_inv_count(user)}/{get_inv_capacity(user)}\n"
            f"{event_text}\n"
            f"{plots_text}")
    await message.answer(text, reply_markup=get_keyboard(uid))

# ==================== پرداخت ====================
@dp.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery):
    try: await query.answer(ok=True)
    except: pass

@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    sp = message.successful_payment
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    parts = sp.invoice_payload.split("_")
    try: amount = int(parts[1])
    except: return
    inv = user.get("inventory", {})
    gift_msg = ""
    if len(parts) >= 4 and parts[3] == "phoenix":
        coins = int(parts[2])
        new_coins = user["coins"] + coins
        update_user(uid, {"coins": new_coins, "pet": PHOENIX_PET, "phoenix_owned": True, "pending_purchase": None})
        update_leaderboard(uid, user["name"], new_coins, user["level"], user["prestige"])
        await message.answer(f"✅ پرداخت موفق!\n💰 {amount:,} تومان\n🪙 +{coins:,} سکه\n🦅 ققنوس داده شد!",
                              reply_markup=get_keyboard(uid))
        return
    try: coins = int(parts[2])
    except: return
    new_coins = user["coins"] + coins
    if amount == 50000:
        fi = random.choice(get_available_fruits(user))
        inv[FRUITS[fi]] = inv.get(FRUITS[fi], 0) + 1
        gift_msg = f"\n🎁 بذر {FRUITS[fi]}"
    elif amount == 100000:
        fi = random.randint(0, len(FRUITS)-1)
        inv[f"طلایی_{FRUITS[fi]}"] = inv.get(f"طلایی_{FRUITS[fi]}", 0) + 1
        gift_msg = f"\n✨ بذر طلایی {FRUITS[fi]}"
    update_user(uid, {"coins": new_coins, "inventory": inv, "pending_purchase": None})
    update_leaderboard(uid, user["name"], new_coins, user["level"], user["prestige"])
    await message.answer(f"✅ پرداخت موفق!\n💰 {amount:,} تومان\n🪙 +{coins:,} سکه\n💼 {new_coins:,}{gift_msg}",
                          reply_markup=get_keyboard(uid))

# ==================== کال‌بک‌ها ====================
@dp.callback_query()
async def on_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    
    if is_banned(uid): return
    
    check_all_harvests(uid); check_period_reset(uid)
    data = callback.data
    user = get_user(uid)
    if not user: return
    
    if data == "noop": return
    elif data == "status": await edit_status(callback, user, uid)
    elif data == "admin_panel": await show_admin_panel(callback, uid)
    elif data == "lands_menu": await show_lands_menu(callback, user, uid)
    elif data == "inventory_menu": await show_inventory(callback, user, uid)
    elif data.startswith("buy_"):
        plot_idx = int(data.split("_")[1])
        await buy_seed_for_plot(callback, user, uid, plot_idx)
    elif data.startswith("harvest_"):
        plot_idx = int(data.split("_")[1])
        await harvest_plot(callback, user, uid, plot_idx)
    elif data.startswith("sell_inv_"):
        fruit = data.replace("sell_inv_", "")
        await sell_from_inventory(callback, user, uid, fruit)
    elif data.startswith("plant_plot_"):
        parts = data.split("_")
        plot_idx = int(parts[2]); fruit_idx = int(parts[3])
        await plant_in_plot(callback, user, uid, plot_idx, fruit_idx)
    elif data.startswith("switch_"):
        await switch_fruit(callback, user, uid, int(data.split("_")[1]))
    elif data == "leaderboard": await show_leaderboard(callback, user, uid)
    elif data == "upgrades": await show_upgrades(callback, user, uid)
    elif data.startswith("upgrade_"): await buy_upgrade(callback, user, uid, data.replace("upgrade_", ""))
    elif data == "buy_land": await buy_land(callback, user, uid)
    elif data == "daily_orders": await show_daily_orders(callback, user, uid)
    elif data == "complete_orders": await complete_orders(callback, user, uid)
    elif data == "shop": await show_shop(callback, user, uid)
    elif data.startswith("shop_"): await buy_shop(callback, user, uid, int(data.split("_")[1]))
    elif data == "worker_menu": await show_worker(callback, user, uid)
    elif data == "worker_toggle": await toggle_worker(callback, user, uid)
    elif data == "worker_upgrade": await upgrade_worker(callback, user, uid)
    elif data == "gift": await start_gift(callback, user, uid, state)
    elif data == "prestige_menu": await show_prestige(callback, user, uid)
    elif data == "buy_prestige": await buy_prestige(callback, user, uid)
    elif data == "pet_menu": await show_pet_menu(callback, user, uid)
    elif data.startswith("spin_"): await do_spin(callback, user, uid, data.replace("spin_", ""))
    elif data == "clan_menu": await show_clan_menu(callback, user, uid)
    elif data == "clan_create": await start_clan_create(callback, user, uid, state)
    elif data == "clan_info": await show_clan_info(callback, user, uid)
    elif data == "clan_invite":
        await state.set_state(UserForm.clan_invite)
        await callback.message.edit_text("👤 نام یا کد کاربر:", reply_markup=get_keyboard(uid))
    elif data == "clan_donate":
        await state.set_state(UserForm.clan_donate)
        await callback.message.edit_text("💰 مقدار سکه (حداقل ۱۰,۰۰۰):", reply_markup=get_keyboard(uid))
    elif data == "clan_chat":
        await state.set_state(UserForm.clan_chat)
        await callback.message.edit_text("✉️ پیام برای اعضا:", reply_markup=get_keyboard(uid))
    elif data == "clan_upgrade": await upgrade_clan(callback, user, uid)
    elif data == "clan_leave": await leave_clan(callback, user, uid)
    elif data == "clan_disband": await disband_clan(callback, user, uid)
    elif data == "league_menu": await show_league_menu(callback, user, uid)
    elif data == "achievements": await show_achievements(callback, user, uid)
    elif data == "back":
        await callback.message.edit_text("🔙 منوی اصلی", reply_markup=get_keyboard(uid))

async def show_admin_panel(callback, uid):
    if not is_admin(uid): return
    text = ("👑 **پنل ادمین**\n\n"
            "دستورات را از طریق پیام ارسال کن.\n\n"
            "`/user_info` — اطلاعات کاربر\n"
            "`/give_coins` — دادن سکه\n"
            "`/event` — ایونت\n"
            "`/giftcode` — گیفت کد\n"
            "`/stats` — آمار\n"
            "`/broadcast` — پیام همگانی\n\n"
            "برای لیست کامل: /admin")
    kb = InlineKeyboardBuilder()
    kb.button("📊 آمار", callback_data="admin_stats_cb")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

# ==================== زمین‌ها و انبار ====================
async def show_lands_menu(callback, user, uid):
    plots = user.get("plots", [])
    max_plots = user.get("max_plots", 1)
    text = f"🏞️ **زمین‌های شما ({max_plots} زمین)**\n\n"
    kb = InlineKeyboardBuilder()
    for i, p in enumerate(plots):
        fruit = FRUITS[p.get("fruit", 0)]
        if p["state"] == "growing":
            rem = get_plot_remaining(p)
            t = f"{rem//60}:{rem%60:02d}" if rem is not None else "..."
            text += f"🏞 زمین {i+1}: ⏳ {fruit} ({t})\n"
            kb.button(f"🏞{i+1} ⏳", callback_data="noop")
        elif p["state"] == "harvested":
            text += f"🏞 زمین {i+1}: 📦 {fruit}\n"
            kb.button(f"🏞{i+1} 📦 {fruit}", callback_data=f"harvest_{i}")
        else:
            text += f"🏞 زمین {i+1}: خالی\n"
            kb.button(f"🏞{i+1} 🌱", callback_data=f"buy_{i}")
    next_price = get_land_price(max_plots)
    if next_price:
        text += f"\n🛒 خرید زمین {max_plots+1}: {next_price:,}\n"
        kb.button(f"🛒 ({next_price:,})", callback_data="buy_land")
    kb.button("📦 انبار", callback_data="inventory_menu")
    kb.button("🔙", callback_data="back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def show_inventory(callback, user, uid):
    inv = user.get("inventory", {})
    cap = get_inv_capacity(user)
    count = get_inv_count(user)
    text = f"📦 **انبار ({count}/{cap})**\n\n"
    kb = InlineKeyboardBuilder()
    if not inv: text += "انبار خالیه!"
    else:
        for fruit_name, cnt in inv.items():
            if fruit_name.startswith("طلایی_"):
                real = fruit_name.replace("طلایی_", "")
                text += f"✨ {real} (طلایی): {cnt} عدد\n"
            else:
                text += f"🍎 {fruit_name}: {cnt} عدد\n"
                kb.button(f"💰 فروش {fruit_name}", callback_data=f"sell_inv_{fruit_name}")
    kb.button("🔙", callback_data="back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_land(callback, user, uid):
    max_plots = user.get("max_plots", 1)
    price = get_land_price(max_plots)
    if price is None:
        await callback.message.edit_text("✅ حداکثر زمین‌ها را داری.", reply_markup=get_keyboard(uid)); return
    if user["coins"] < price:
        await callback.message.edit_text(f"❌ نیاز به {price:,} سکه.", reply_markup=get_keyboard(uid)); return
    plots = user.get("plots", [])
    plots.append({"fruit": 0, "state": "idle", "harvest_time": None})
    update_user(uid, {"coins": user["coins"] - price, "plots": plots, "max_plots": max_plots + 1})
    update_leaderboard(uid, user["name"], user["coins"] - price, user["level"], user["prestige"])
    await callback.message.edit_text(f"🎉 زمین {max_plots+1} خریداری شد!", reply_markup=get_keyboard(uid))

async def buy_seed_for_plot(callback, user, uid, plot_idx):
    plots = user.get("plots", [])
    if plot_idx >= len(plots): return
    plot = plots[plot_idx]
    if plot["state"] == "growing":
        await callback.message.edit_text("⏳ در حال رشده.", reply_markup=get_keyboard(uid)); return
    if plot["state"] == "harvested":
        await callback.message.edit_text("📦 اول برداشت کن.", reply_markup=get_keyboard(uid)); return
    available = get_available_fruits(user)
    effects, _ = get_season_effects()
    mult = user["prestige_multiplier"]
    text = f"🌱 **کاشت در زمین {plot_idx+1}**\n\n"
    kb = InlineKeyboardBuilder()
    for i in available:
        bp = int(PRICES[i][0] * mult * effects["buy_mult"])
        text += f"• {FRUITS[i]}: {bp:,} سکه\n"
        kb.button(f"🌱 {FRUITS[i]} ({bp:,})", callback_data=f"plant_plot_{plot_idx}_{i}")
    kb.button("🔙 بازگشت", callback_data="lands_menu")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def plant_in_plot(callback, user, uid, plot_idx, fruit_idx):
    plots = user.get("plots", [])
    if plot_idx >= len(plots) or fruit_idx not in get_available_fruits(user): return
    effects, _ = get_season_effects()
    buy_price = int(PRICES[fruit_idx][0] * user["prestige_multiplier"] * effects["buy_mult"])
    if user["coins"] < buy_price:
        await callback.message.edit_text(f"❌ نیاز به {buy_price:,}", reply_markup=get_keyboard(uid)); return
    growth_time = GROWTH_TIMES[fruit_idx] * effects["growth_mult"]
    if user["upgrades"].get("auto_water", 0) > 0: growth_time *= 0.8
    sb = get_pet_effect(user, "speed")
    if sb > 0: growth_time *= (1 - sb / 100)
    harvest_dt = datetime.now() + timedelta(minutes=growth_time)
    plots[plot_idx] = {"fruit": fruit_idx, "state": "growing", "harvest_time": harvest_dt.isoformat()}
    update_user(uid, {"coins": user["coins"] - buy_price, "plots": plots, "current_fruit": fruit_idx})
    mins = int(growth_time); secs = int((growth_time - mins) * 60)
    await callback.message.edit_text(f"🌱 {FRUITS[fruit_idx]} در زمین {plot_idx+1} کاشته شد!\n⏳ {mins}:{secs:02d}",
                                       reply_markup=get_keyboard(uid))

async def harvest_plot(callback, user, uid, plot_idx):
    plots = user.get("plots", [])
    if plot_idx >= len(plots): return
    plot = plots[plot_idx]
    if plot["state"] != "harvested":
        await callback.message.edit_text("⏳ هنوز نرسیده.", reply_markup=get_keyboard(uid)); return
    fruit_name = FRUITS[plot.get("fruit", 0)]
    if not add_to_inventory(uid, fruit_name):
        await callback.message.edit_text(f"📦 انبارت پره! ({get_inv_count(user)}/{get_inv_capacity(user)})",
                                           reply_markup=get_keyboard(uid)); return
    plots[plot_idx] = {"fruit": 0, "state": "idle", "harvest_time": None}
    update_user(uid, {"plots": plots})
    await callback.message.edit_text(f"📦 {fruit_name} به انبار اضافه شد!",
                                       reply_markup=get_keyboard(uid))

async def sell_from_inventory(callback, user, uid, fruit_name):
    inv = user.get("inventory", {})
    if inv.get(fruit_name, 0) < 1:
        await callback.message.edit_text("❌ موجودی کافی نیست.", reply_markup=get_keyboard(uid)); return
    try: cf = FRUITS.index(fruit_name)
    except ValueError:
        await callback.message.edit_text("❌ نامعتبر.", reply_markup=get_keyboard(uid)); return
    inv[fruit_name] -= 1
    if inv[fruit_name] <= 0: del inv[fruit_name]
    effects, _ = get_season_effects()
    base_sell = int(PRICES[cf][1] * user["prestige_multiplier"] * effects["sell_mult"])
    sell_price = base_sell
    pb = get_pet_effect(user, "sell")
    if pb > 0: sell_price += int(base_sell * pb / 100)
    cb = get_clan_bonus(user)
    if cb > 0: sell_price += int(base_sell * cb / 100)
    if user["upgrades"].get("golden_pot", 0) > 0:
        sell_price = int(sell_price * (1 + 0.1 * user["upgrades"]["golden_pot"]))
    golden = random.random() < effects["golden_chance"]
    if golden: sell_price *= 2
    xp_gain = int(xp_from_sale(fruit_name) * user["prestige_multiplier"] * effects["xp_mult"])
    px = get_pet_effect(user, "xp")
    if px > 0: xp_gain += int(xp_gain * px / 100)
    new_coins = user["coins"] + sell_price
    new_xp = user["xp"] + xp_gain
    new_level = user["level"]
    lu = ""
    xn = xp_needed_for(new_level)
    while new_xp >= xn and new_level < 7:
        new_xp -= xn; new_level += 1
        xn = xp_needed_for(new_level)
        lu = f"\n🎉 لول {new_level}!"
    update_user(uid, {"coins": new_coins, "xp": new_xp, "level": new_level, "inventory": inv})
    update_leaderboard(uid, user["name"], new_coins, new_level, user["prestige"])
    upd = get_user(uid)
    update_league_profit(uid, upd, upd["coins"] - upd.get("period_start_coins", 1))
    gt = " ✨" if golden else ""
    await callback.message.edit_text(f"✅ {fruit_name} فروخته شد{gt}\n💵 {base_sell:,}\n💰 +{sell_price:,}\n⭐ +{xp_gain} XP\n📈 لول {new_level}{lu}",
                                       reply_markup=get_keyboard(uid))

async def edit_status(callback, user, uid):
    await callback.message.edit_text(build_status_text(user, uid), reply_markup=get_keyboard(uid))

async def switch_fruit(callback, user, uid, idx):
    if idx not in get_available_fruits(user):
        await callback.message.edit_text("🔒 قفل!", reply_markup=get_keyboard(uid)); return
    update_user(uid, {"current_fruit": idx})
    await callback.message.edit_text(f"✅ {FRUITS[idx]}", reply_markup=get_keyboard(uid))

# ==================== بقیه ====================
async def show_leaderboard(callback, user, uid):
    data = load_data()
    lb = data["leaderboard"][:10]
    text = "🏆 **لیدربرد:**\n\n"
    for i, item in enumerate(lb, 1):
        p = f"⭐{item['prestige']}" if item['prestige'] > 0 else ""
        text += f"{i}. {item['name']} {p} — لول {item['level']} | {item['coins']:,}\n"
    if not lb: text += "خالیه!"
    await callback.message.edit_text(text, reply_markup=get_keyboard(uid))

async def show_upgrades(callback, user, uid):
    u = user["upgrades"]
    c1 = 1000 * (u.get("auto_water", 0) + 1)
    c2 = 2000 * (u.get("golden_pot", 0) + 1)
    c3 = 5000 * (u.get("professional_seeder", 0) + 1)
    max_plots = user.get("max_plots", 1)
    lp = get_land_price(max_plots)
    text = (f"🔧 **ارتقاء:**\n\n💧 آبیاری — {c1:,}\n🏺 گلدان — {c2:,}\n🌱 بذرپاش — {c3:,}\n")
    kb = InlineKeyboardBuilder()
    kb.button(f"💧 ({c1:,})", callback_data="upgrade_auto_water")
    kb.button(f"🏺 ({c2:,})", callback_data="upgrade_golden_pot")
    kb.button(f"🌱 ({c3:,})", callback_data="upgrade_professional_seeder")
    if lp:
        text += f"\n🏞️ زمین {max_plots+1}: {lp:,}"
        kb.button(f"🏞️ ({lp:,})", callback_data="buy_land")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_upgrade(callback, user, uid, key):
    base = {"auto_water": 1000, "golden_pot": 2000, "professional_seeder": 5000}
    if key not in base: return
    count = user["upgrades"].get(key, 0)
    cost = base[key] * (count + 1)
    if user["coins"] < cost:
        await callback.message.edit_text(f"❌ {cost:,}", reply_markup=get_keyboard(uid)); return
    u = user["upgrades"]; u[key] = count + 1
    update_user(uid, {"coins": user["coins"] - cost, "upgrades": u})
    await callback.message.edit_text("✅", reply_markup=get_keyboard(uid))

async def show_daily_orders(callback, user, uid):
    today = datetime.now().strftime("%Y-%m-%d")
    if user["daily_orders"]["date"] != today:
        orders = [{"fruit": FRUITS[random.randint(0, len(FRUITS)-2)], "count": random.randint(1, 3)} for _ in range(3)]
        update_user(uid, {"daily_orders": {"date": today, "orders": orders, "completed": False}})
        user = get_user(uid)
    orders = user["daily_orders"]["orders"]
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("📦 تکمیل شده!", reply_markup=get_keyboard(uid)); return
    inv = user.get("inventory", {})
    text = "📦 **سفارشات:**\n\n"
    for i, o in enumerate(orders, 1):
        have = inv.get(o["fruit"], 0)
        text += f"{i}. {o['count']}× {o['fruit']} ({'✅' if have >= o['count'] else '❌'} {have})\n"
    kb = InlineKeyboardBuilder()
    kb.button("✅ تکمیل", callback_data="complete_orders")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def complete_orders(callback, user, uid):
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("قبلاً!", reply_markup=get_keyboard(uid)); return
    orders = user["daily_orders"]["orders"]
    inv = user.get("inventory", {})
    for o in orders:
        if inv.get(o["fruit"], 0) < o["count"]:
            await callback.message.edit_text(f"❌ کمبود {o['fruit']}", reply_markup=get_keyboard(uid)); return
    for o in orders:
        inv[o["fruit"]] -= o["count"]
        if inv[o["fruit"]] <= 0: del inv[o["fruit"]]
    bonus = int(sum(PRICES[FRUITS.index(o["fruit"])][1] * o["count"] * 1.5 for o in orders) * user["prestige_multiplier"])
    nc = user["coins"] + bonus
    update_user(uid, {"coins": nc, "inventory": inv, "daily_orders": {**user["daily_orders"], "completed": True}})
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await callback.message.edit_text(f"✅ +{bonus:,} سکه", reply_markup=get_keyboard(uid))

async def show_shop(callback, user, uid):
    level = user["level"]
    if level < 4 and user.get("prestige", 0) == 0:
        await callback.message.edit_text("🔒 لول ۴", reply_markup=get_keyboard(uid)); return
    prices = SHOP_PRICES.get(level, SHOP_PRICES[7])
    text = "🛒 **فروشگاه**\n\n💰 با توجه به لول شما، مقدار سکه‌ها متفاوت است.\n\n"
    for amt, c in prices.items():
        text += f"• {amt:,} تومان → {c:,} سکه"
        if amt == 50000: text += " + بذر"
        elif amt == 70000: text += " + 🦅"
        elif amt == 100000: text += " + بذر طلایی ✨"
        text += "\n"
    kb = InlineKeyboardBuilder()
    for amt in prices:
        label = f"{amt:,}"
        if amt == 70000: label += " 🦅"
        elif amt == 100000: label += " ✨"
        if amt == 70000 and user.get("phoenix_owned"): continue
        kb.button(label, callback_data=f"shop_{amt}")
    kb.button("🔙", callback_data="back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_shop(callback, user, uid, amount):
    level = user["level"] if user.get("prestige", 0) == 0 else 7
    prices = SHOP_PRICES.get(level, SHOP_PRICES[7])
    if amount not in prices: return
    coins = prices[amount]
    pr = amount * 10
    update_user(uid, {"pending_purchase": {"amount": amount, "coins": coins, "created_at": datetime.now().isoformat()}})
    if amount == 70000:
        payload = f"shop_{amount}_{coins}_phoenix"
        title = "ققنوس"
        desc = f"{coins:,} سکه + 🦅"
    else:
        payload = f"shop_{amount}_{coins}"
        title = f"{coins:,} سکه"
        desc = f"بسته {amount:,} تومانی"
    try:
        await bot.send_invoice(chat_id=uid, title=title, description=desc, payload=payload,
                                provider_token=PROVIDER_TOKEN, currency="IRR",
                                prices=[{"label": f"{coins:,} سکه", "amount": pr}])
        try: await callback.message.delete()
        except: pass
    except Exception as e:
        await callback.message.edit_text(f"❌ `{str(e)[:200]}`", reply_markup=get_keyboard(uid))

async def show_worker(callback, user, uid):
    w = user["worker"]; cost = 5000 * w["level"]
    text = f"👷 **کارگر**\nلول: {w['level']}\n{'فعال' if w['active'] else 'غیرفعال'}\nارتقاء: {cost:,}"
    kb = InlineKeyboardBuilder()
    kb.button("🔄", callback_data="worker_toggle")
    kb.button("⬆️", callback_data="worker_upgrade")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def toggle_worker(callback, user, uid):
    w = user["worker"]; w["active"] = not w["active"]
    update_user(uid, {"worker": w})
    await callback.message.edit_text(f"👷 {'فعال' if w['active'] else 'غیرفعال'}", reply_markup=get_keyboard(uid))

async def upgrade_worker(callback, user, uid):
    w = user["worker"]; cost = 5000 * w["level"]
    if user["coins"] < cost:
        await callback.message.edit_text(f"❌ {cost:,}", reply_markup=get_keyboard(uid)); return
    w["level"] += 1
    update_user(uid, {"coins": user["coins"] - cost, "worker": w})
    await callback.message.edit_text(f"✅ {w['level']}", reply_markup=get_keyboard(uid))

async def start_gift(callback, user, uid, state):
    await state.set_state(UserForm.gift_target)
    await callback.message.edit_text("🎁 نام یا کد کاربر:")

async def show_prestige(callback, user, uid):
    if user["level"] < 7:
        await callback.message.edit_text("🔒 لول ۷", reply_markup=get_keyboard(uid)); return
    if user["prestige"] >= 10:
        await callback.message.edit_text("⭐ حداکثر!", reply_markup=get_keyboard(uid)); return
    nxt = user["prestige"] + 1
    price = PRESTIGE_PRICES[nxt]
    text = f"⭐ **پرستیژ {nxt}**\nهزینه: {price:,}\nضریب: {user['prestige_multiplier']*1.5:.2f}x\n⚠️ ریست: سکه، لول، انبار، زمین‌ها"
    kb = InlineKeyboardBuilder()
    kb.button(f"⭐ ({price:,})", callback_data="buy_prestige")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_prestige(callback, user, uid):
    if user["prestige"] >= 10: return
    nxt = user["prestige"] + 1
    price = PRESTIGE_PRICES[nxt]
    if user["coins"] < price:
        await callback.message.edit_text(f"❌ {price:,}", reply_markup=get_keyboard(uid)); return
    nu = create_default_user(uid)
    nu["name"] = user["name"]
    nu["prestige"] = nxt
    nu["prestige_multiplier"] = user["prestige_multiplier"] * 1.5
    nu["referral_code"] = user["referral_code"]
    nu["gifts_given"] = user.get("gifts_given", 0)
    nu["gifts_received"] = user.get("gifts_received", 0)
    nu["achievements"] = user.get("achievements", [])
    nu["clan_id"] = user.get("clan_id")
    nu["phoenix_owned"] = user.get("phoenix_owned", False)
    if nu["phoenix_owned"]: nu["pet"] = PHOENIX_PET
    nu["last_seen_period"] = get_period_number()
    nu["current_period"] = get_period_number()
    nu["used_gift_codes"] = user.get("used_gift_codes", [])
    data = load_data()
    data["users"][str(uid)] = nu
    save_data(data)
    update_leaderboard(uid, user["name"], 1, 1, nxt)
    await callback.message.edit_text(f"⭐ پرستیژ {nxt}!\nضریب: {nu['prestige_multiplier']:.2f}x",
                                       reply_markup=get_keyboard(uid))

async def show_pet_menu(callback, user, uid):
    pet = user.get("pet")
    if pet:
        tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
        pt = f"{pet['emoji']} {pet['name']} (+{pet['value']}٪ {tfa.get(pet['type'], '')})"
    else: pt = "ندارد"
    if user.get("phoenix_owned"):
        text = f"🐾 **پت:** {pt}\n\n⚠️ ققنوس داری. اسپین ممکن نیست."
        kb = InlineKeyboardBuilder()
        kb.button("🔙", callback_data="back")
        await callback.message.edit_text(text, reply_markup=kb.as_markup()); return
    text = f"🐾 **پت:** {pt}\n\n🥚 **تخم‌ها:**\n"
    for k, egg in PET_EGGS.items():
        text += f"• {egg['name']}: {egg['price']:,}\n"
    text += "\n⚠️ اسپین، پت قبلی رو نابود می‌کنه!"
    kb = InlineKeyboardBuilder()
    for k, egg in PET_EGGS.items():
        short = {"common":"معمولی","uncommon":"غیرمعمولی","rare":"کمیاب",
                 "epic":"حماسی","legendary":"افسانه‌ای","mythic":"اساطیری"}[k]
        kb.button(short, callback_data=f"spin_{k}")
    kb.button("🔙", callback_data="back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def do_spin(callback, user, uid, egg_type):
    if user.get("phoenix_owned"):
        await callback.message.edit_text("🦅 ققنوس داری!", reply_markup=get_keyboard(uid)); return
    if egg_type not in PET_EGGS: return
    egg = PET_EGGS[egg_type]
    if user["coins"] < egg["price"]:
        await callback.message.edit_text(f"❌ {egg['price']:,}", reply_markup=get_keyboard(uid)); return
    np = spin_egg(egg_type)
    if not np: return
    nc = user["coins"] - egg["price"]
    update_user(uid, {"coins": nc, "pet": np})
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
    await callback.message.edit_text(f"🥚\n{np['emoji']} **{np['name']}**\n+{np['value']}٪ {tfa[np['type']]}\n💰 {nc:,}",
                                       reply_markup=get_keyboard(uid))

async def show_clan_menu(callback, user, uid):
    if not user.get("clan_id"):
        text = f"🏰 **بدون کلن**\n\nساخت: {CLAN_CREATE_COST:,}"
        kb = InlineKeyboardBuilder()
        kb.button("🏰 ساخت", callback_data="clan_create")
        kb.button("🔙", callback_data="back")
        kb.adjust(1)
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
    else: await show_clan_info(callback, user, uid)

async def show_clan_info(callback, user, uid):
    clan = get_clan(user["clan_id"])
    if not clan:
        await callback.message.edit_text("❌ یافت نشد", reply_markup=get_keyboard(uid)); return
    il = clan["leader_id"] == str(uid)
    text = (f"🏰 **{clan['name']}**\nلول: {clan['level']} | +{clan['level']*CLAN_BONUS_PER_LEVEL}٪\n"
            f"خزانه: {clan['treasury']:,}\nاعضا: {len(clan['members'])}/{CLAN_MAX_MEMBERS.get(clan['level'],10)}\n"
            f"لیدر: {clan['leader_name']}\n\n👥\n")
    for m in clan["members"][:20]:
        text += f"• {clan['member_names'].get(m, '?')}\n"
    kb = InlineKeyboardBuilder()
    kb.button("👤", callback_data="clan_invite")
    kb.button("💰", callback_data="clan_donate")
    kb.button("✉️", callback_data="clan_chat")
    if il:
        kb.button("⬆️", callback_data="clan_upgrade")
        kb.button("🗑", callback_data="clan_disband")
    else: kb.button("🚪", callback_data="clan_leave")
    kb.button("🔙", callback_data="back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def start_clan_create(callback, user, uid, state):
    if user["coins"] < CLAN_CREATE_COST:
        await callback.message.edit_text(f"❌ {CLAN_CREATE_COST:,}", reply_markup=get_keyboard(uid)); return
    await state.set_state(UserForm.clan_name)
    await callback.message.edit_text("🏰 نام کلن:")

async def upgrade_clan(callback, user, uid):
    clan = get_clan(user["clan_id"])
    if not clan or clan["level"] >= 10: return
    nxt = clan["level"] + 1; cost = CLAN_LEVEL_COSTS[nxt]
    if clan["treasury"] < cost:
        await callback.message.edit_text(f"❌ خزانه: {cost:,}", reply_markup=get_keyboard(uid)); return
    data = load_data()
    data["clans"][user["clan_id"]]["level"] = nxt
    data["clans"][user["clan_id"]]["treasury"] -= cost
    save_data(data)
    await callback.message.edit_text(f"✅ لول {nxt}!", reply_markup=get_keyboard(uid))

async def leave_clan(callback, user, uid):
    clan = get_clan(user["clan_id"])
    if not clan: return
    if clan["leader_id"] == str(uid):
        await callback.message.edit_text("❌ لیدر منحل کن.", reply_markup=get_keyboard(uid)); return
    data = load_data()
    data["clans"][user["clan_id"]]["members"].remove(str(uid))
    data["clans"][user["clan_id"]]["member_names"].pop(str(uid), None)
    save_data(data)
    update_user(uid, {"clan_id": None})
    await callback.message.edit_text("🚪 خارج شدی", reply_markup=get_keyboard(uid))

async def disband_clan(callback, user, uid):
    clan = get_clan(user["clan_id"])
    if not clan or clan["leader_id"] != str(uid): return
    data = load_data()
    for m in clan["members"]: update_user(int(m), {"clan_id": None})
    del data["clans"][user["clan_id"]]
    save_data(data)
    await callback.message.edit_text("🗑 منحل شد", reply_markup=get_keyboard(uid))

async def show_league_menu(callback, user, uid):
    pn = user.get("current_period", 1)
    lg = LEAGUE_FA.get(user.get("prestige", 0), "?")
    profit = user["coins"] - user.get("period_start_coins", 1)
    rank = get_user_league_rank(uid, user)
    text = f"🏅 **لیگ {lg}** — دوره {pn}\n\n💵 سود: {profit:,}\n📊 رتبه: {rank}\n\n🏆 ۱۰٪ برتر افتخار می‌گیرن!"
    kb = InlineKeyboardBuilder()
    kb.button("🎖️ افتخارات", callback_data="achievements")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def show_achievements(callback, user, uid):
    achs = user.get("achievements", [])
    if not achs: text = "🎖️ خالی!"
    else:
        text = f"🎖️ **افتخارات ({len(achs)})**\n\n"
        for a in achs[-20:]:
            ln = LEAGUE_FA.get(a.get("league", 0), "?")
            t = a.get("type")
            if t == "top_percent":
                text += f"🏅 {a['percent']}٪ برتر دوره {a['period']}، لیگ {ln}\n"
            elif t == "lone_eagle":
                text += f"🦅 عقاب تنهای {a['rank']} دوره {a['period']}، لیگ {ln}\n"
            elif t == "medal_gold":
                text += f"🥇 طلای دوره {a['period']}، لیگ {ln}\n"
            elif t == "medal_silver":
                text += f"🥈 نقره دوره {a['period']}، لیگ {ln}\n"
            elif t == "medal_bronze":
                text += f"🥉 برنز دوره {a['period']}، لیگ {ln}\n"
    await callback.message.edit_text(text, reply_markup=get_keyboard(uid))

# ==================== اجرا ====================
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print(f"🤖 ربات روشن شد... ادمین: {ADMIN_ID}")
    async def stop_delay():
        await asyncio.sleep(340 * 60)
        print("⏰ توقف...")
        try: await dp.stop_polling()
        except: pass
    asyncio.create_task(stop_delay())
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"متوقف: {e}")

if __name__ == "__main__":
    asyncio.run(main())
