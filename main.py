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
    raise ValueError("BOT_TOKEN not set!")
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
    2: {"fruits": [0, 1], "features": ["status", "pet", "leaderboard", "daily_orders"]},
    3: {"fruits": [0, 1, 2], "features": ["status", "pet", "leaderboard", "daily_orders", "upgrades"]},
    4: {"fruits": [0, 1, 2, 3], "features": ["status", "pet", "leaderboard", "daily_orders", "upgrades", "shop"]},
    5: {"fruits": [0, 1, 2, 3, 4], "features": ["status", "pet", "leaderboard", "daily_orders", "upgrades", "shop", "worker", "clan"]},
    6: {"fruits": [0, 1, 2, 3, 4, 5], "features": ["status", "pet", "leaderboard", "daily_orders", "upgrades", "shop", "worker", "clan", "gift"]},
    7: {"fruits": [0, 1, 2, 3, 4, 5, 6], "features": ["status", "pet", "leaderboard", "daily_orders", "upgrades", "shop", "worker", "clan", "gift", "prestige", "league"]},
}

ALL_FEATURES = ["status", "pet", "leaderboard", "daily_orders", "upgrades",
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

PHOENIX_PET = {"name": "ققنوس", "emoji": "🦅", "type": "sell", "value": 100, "speed_value": 70}

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

TEXT_COMMANDS = {
    "وضعیت": "status", "وضعیت من": "status", "پروفایل": "status", "status": "status",
    "پت": "pet_menu", "حیوان": "pet_menu", "حیوانات": "pet_menu", "pet": "pet_menu",
    "لیدربرد": "leaderboard", "رتبه": "leaderboard", "رتبه‌بندی": "leaderboard", "leaderboard": "leaderboard",
    "ارتقاء": "upgrades", "ارتقا": "upgrades", "ارتقاء ابزار": "upgrades", "upgrades": "upgrades",
    "سفارش": "daily_orders", "سفارشات": "daily_orders", "سفارشات روزانه": "daily_orders",
    "ماموریت": "daily_orders", "ماموریت‌ها": "daily_orders", "orders": "daily_orders",
    "فروشگاه": "shop", "فروشگاه سکه": "shop", "shop": "shop",
    "کارگر": "worker_menu", "کارگرها": "worker_menu", "worker": "worker_menu",
    "کلن": "clan_menu", "clan": "clan_menu",
    "هدیه": "gift", "هدیه دادن": "gift", "gift": "gift",
    "لیگ": "league_menu", "league": "league_menu",
    "افتخار": "achievements", "افتخارات": "achievements", "مدال": "achievements", "مدال‌ها": "achievements", "achievements": "achievements",
    "پرستیژ": "prestige_menu", "prestige": "prestige_menu",
    "زمین": "lands_menu", "زمین‌ها": "lands_menu", "زمینها": "lands_menu", "lands": "lands_menu",
    "انبار": "inventory_menu", "کیف": "inventory_menu", "inventory": "inventory_menu",
    "خرید بذر": "buy_seed_text", "بذر": "buy_seed_text",
    "برداشت": "harvest_text", "برداشت کن": "harvest_text",
}

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
    confirm_transfer = State()
    worker_plant_hours = State()
    worker_harvest_hours = State()

# ==================== دیتابیس ====================
def create_default_data():
    return {"game_start_time": datetime.now().isoformat(), "users": {},
            "leaderboard": [], "clans": {}, "leagues": {},
            "active_event": None, "gift_codes": {}, "banned": []}

def create_default_user(user_id):
    now = datetime.now().isoformat()
    return {
        "name": "", "level": 1, "xp": 0, "coins": 1,
        "plots": [{"fruit": 0, "state": "idle", "harvest_time": None}],
        "max_plots": 1, "current_fruit": 0, "inventory": {},
        "upgrades": {"auto_water": 0, "golden_pot": 0, "professional_seeder": 0},
        "workers": {
            "planting": {"active": False, "fruit": None, "hours": 0, "expires_at": None},
            "harvest_sell": {"active": False, "hours": 0, "expires_at": None},
        },
        "daily_orders": {"date": "", "orders": [], "completed": False},
        "prestige": 0, "prestige_multiplier": 1.0,
        "gifts_given": 0, "gifts_received": 0,
        "referral_code": f"REF{user_id}{random.randint(100,999)}",
        "pet": None, "phoenix_owned": False, "clan_id": None,
        "period_start_coins": 1, "period_start_time": now,
        "current_period": 1, "last_seen_period": 1,
        "achievements": [], "pending_purchase": None, "used_gift_codes": [],
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
    if "workers" not in u:
        u["workers"] = {
            "planting": {"active": False, "fruit": None, "hours": 0, "expires_at": None},
            "harvest_sell": {"active": False, "hours": 0, "expires_at": None},
        }
    u.pop("worker", None)
    if u.get("phoenix_owned") and u.get("pet", {}).get("name") == "ققنوس":
        if "speed_value" not in u["pet"]:
            u["pet"] = PHOENIX_PET
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

def get_active_event():
    data = load_data()
    ev = data.get("active_event")
    if not ev: return None
    try:
        end = datetime.fromisoformat(ev["end_time"])
        if datetime.now() >= end:
            data["active_event"] = None
            save_data(data); return None
    except: return None
    return ev

def get_inv_count(user): return sum(user.get("inventory", {}).values())
def get_inv_capacity(user): return INVENTORY_CAPACITY.get(user.get("level", 1), 1)

def add_to_inventory(user_id, fruit_name):
    user = get_user(user_id)
    if not user: return False
    if get_inv_count(user) >= get_inv_capacity(user): return False
    inv = user.get("inventory", {})
    inv[fruit_name] = inv.get(fruit_name, 0) + 1
    update_user(user_id, {"inventory": inv})
    return True

def get_plot_remaining(plot):
    if plot.get("state") != "growing": return None
    ht = plot.get("harvest_time")
    if not ht: return None
    try: return max(0, int((datetime.fromisoformat(ht) - datetime.now()).total_seconds()))
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
    if pet.get("type") == t:
        return pet.get("value", 0)
    if f"{t}_value" in pet:
        return pet[f"{t}_value"]
    return 0

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
        user.setdefault("achievements", []).append({"type": "lone_eagle", "rank": rank, "period": pn, "league": prestige, "date": ach_date})
        return
    if rank == 1:
        user.setdefault("achievements", []).append({"type": "medal_gold", "rank": 1, "period": pn, "league": prestige, "date": ach_date})
    elif rank == 2 and total >= 31:
        user.setdefault("achievements", []).append({"type": "medal_silver", "rank": 2, "period": pn, "league": prestige, "date": ach_date})
    elif rank == 3 and total >= 41:
        user.setdefault("achievements", []).append({"type": "medal_bronze", "rank": 3, "period": pn, "league": prestige, "date": ach_date})
    pct = max(1, int((rank / total) * 100))
    if pct <= 10:
        user.setdefault("achievements", []).append({"type": "top_percent", "percent": pct, "period": pn, "league": prestige, "date": ach_date})

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
    data["leagues"][pk][per_key]["members"][str(user_id)] = {"name": user.get("name", "?"), "profit": profit}
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
def is_banned(user_id): return str(user_id) in load_data().get("banned", [])

# ==================== پردازش کارگرها ====================
def process_workers(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user: return
    workers = user.get("workers", {})
    now = datetime.now()
    changed = False
    effects, _ = get_season_effects()

    pw = workers.get("planting", {})
    if pw.get("active"):
        try:
            expires = datetime.fromisoformat(pw["expires_at"])
            if now >= expires:
                pw["active"] = False; pw["fruit"] = None; pw["expires_at"] = None
                changed = True
            else:
                fi = pw.get("fruit")
                if fi is not None:
                    buy_price = int(PRICES[fi][0] * user["prestige_multiplier"] * effects["buy_mult"])
                    for plot in user.get("plots", []):
                        if plot["state"] != "idle": continue
                        if user["coins"] < buy_price: break
                        gt = GROWTH_TIMES[fi] * effects["growth_mult"]
                        if user["upgrades"].get("auto_water", 0) > 0: gt *= 0.8
                        sb = get_pet_effect(user, "speed")
                        if sb > 0: gt *= (1 - sb / 100)
                        ht = now + timedelta(minutes=gt)
                        plot["fruit"] = fi
                        plot["state"] = "growing"
                        plot["harvest_time"] = ht.isoformat()
                        user["coins"] -= buy_price
                        changed = True
        except Exception as e:
            print(f"Worker planting error: {e}")

    hw = workers.get("harvest_sell", {})
    if hw.get("active"):
        try:
            expires = datetime.fromisoformat(hw["expires_at"])
            if now >= expires:
                hw["active"] = False; hw["expires_at"] = None
                changed = True
            else:
                for plot in user.get("plots", []):
                    if plot["state"] != "harvested": continue
                    fn = FRUITS[plot.get("fruit", 0)]
                    inv = user.get("inventory", {})
                    if sum(inv.values()) >= get_inv_capacity(user): break
                    inv[fn] = inv.get(fn, 0) + 1
                    user["inventory"] = inv
                    plot["fruit"] = 0
                    plot["state"] = "idle"
                    plot["harvest_time"] = None
                    changed = True
                inv = user.get("inventory", {})
                for fn in list(inv.keys()):
                    if inv.get(fn, 0) <= 0: continue
                    if fn.startswith("طلایی_"): continue
                    try: cf = FRUITS.index(fn)
                    except: continue
                    bs = int(PRICES[cf][1] * user["prestige_multiplier"] * effects["sell_mult"])
                    sp = bs
                    pb = get_pet_effect(user, "sell")
                    if pb > 0: sp += int(bs * pb / 100)
                    cb = get_clan_bonus(user)
                    if cb > 0: sp += int(bs * cb / 100)
                    if user["upgrades"].get("golden_pot", 0) > 0:
                        sp = int(sp * (1 + 0.1 * user["upgrades"]["golden_pot"]))
                    commission = int(sp * 0.2)
                    final_sp = sp - commission
                    xp = int(xp_from_sale(fn) * user["prestige_multiplier"] * effects["xp_mult"])
                    px = get_pet_effect(user, "xp")
                    if px > 0: xp += int(xp * px / 100)
                    user["coins"] += final_sp
                    user["xp"] += xp
                    while user["level"] < 7 and user["xp"] >= xp_needed_for(user["level"]):
                        user["xp"] -= xp_needed_for(user["level"])
                        user["level"] += 1
                    inv[fn] -= 1
                    if inv[fn] <= 0: del inv[fn]
                    user["inventory"] = inv
                    changed = True
                    break
        except Exception as e:
            print(f"Worker harvest error: {e}")

    if changed:
        user["workers"] = workers
        data["users"][str(user_id)] = user
        save_data(data)
        update_leaderboard(user_id, user["name"], user["coins"], user["level"], user["prestige"])
        profit = user["coins"] - user.get("period_start_coins", 1)
        update_league_profit(user_id, user, profit)

# ==================== Fake ====================
class FakeMsg:
    def __init__(self, msg): self._msg = msg
    async def edit_text(self, text, **kw): return await self._msg.answer(text, **kw)
    async def delete(self):
        try: await self._msg.delete()
        except: pass
    async def answer(self, text, **kw): return await self._msg.answer(text, **kw)

class FakeCallback:
    def __init__(self, message, data):
        self.message = FakeMsg(message)
        self.from_user = message.from_user
        self.data = data
    async def answer(self, *a, **kw): pass

# ==================== کیبورد ====================
def get_keyboard(user_id):
    user = get_user(user_id)
    if not user: return InlineKeyboardBuilder().as_markup()
    prefix = f"owner_{user_id}_"
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
            kb.button(f"📦 برداشت {fruit}", callback_data=f"{prefix}harvest_0")
        else:
            kb.button("🌱 خرید بذر", callback_data=f"{prefix}buy_0")
        kb.adjust(2)
    else:
        kb.button("🏞️ زمین‌ها", callback_data=f"{prefix}lands_menu")
        kb.button("📦 انبار", callback_data=f"{prefix}inventory_menu")
        kb.adjust(2)
    kb.button("📊 وضعیت", callback_data=f"{prefix}status")
    if max_plots == 1:
        kb.button("📦 انبار", callback_data=f"{prefix}inventory_menu")
    if has_feature(user, "pet"): kb.button("🐾 پت", callback_data=f"{prefix}pet_menu")
    if has_feature(user, "leaderboard"): kb.button("🏆 لیدربرد", callback_data=f"{prefix}leaderboard")
    if has_feature(user, "daily_orders"): kb.button("📦 سفارشات روزانه", callback_data=f"{prefix}daily_orders")
    if has_feature(user, "upgrades"): kb.button("🔧 ارتقاء ابزار", callback_data=f"{prefix}upgrades")
    if has_feature(user, "shop"): kb.button("🛒 فروشگاه سکه", callback_data=f"{prefix}shop")
    if has_feature(user, "worker"): kb.button("👷 کارگرها", callback_data=f"{prefix}worker_menu")
    if has_feature(user, "clan"): kb.button("🏰 کلن", callback_data=f"{prefix}clan_menu")
    if has_feature(user, "gift"): kb.button("🎁 هدیه دادن", callback_data=f"{prefix}gift")
    if has_feature(user, "league"):
        kb.button("🏅 لیگ", callback_data=f"{prefix}league_menu")
        kb.button("🎖️ افتخارات", callback_data=f"{prefix}achievements")
    if has_feature(user, "prestige") and user["level"] >= 7:
        kb.button("⭐ پرستیژ", callback_data=f"{prefix}prestige_menu")
    if is_admin(user_id):
        kb.button("👑 Admin Panel", callback_data=f"{prefix}admin_panel")
    kb.adjust(2)
    return kb.as_markup()

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
    ev = get_active_event()
    if ev:
        try:
            end = datetime.fromisoformat(ev["end_time"])
            rem = end - datetime.now()
            h = int(rem.total_seconds() // 3600)
            m = int((rem.total_seconds() % 3600) // 60)
            text += f"🎉 **ایونت فعال!** ({h}s {m}d)\n"
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
            pet_text = f"{pet['emoji']} {pet['name']} (+{pet['value']}٪ {tfa.get(pet['type'], '')}"
            for k in ["sell", "speed", "xp"]:
                if k != pet.get("type") and f"{k}_value" in pet:
                    pet_text += f" | +{pet[f'{k}_value']}٪ {tfa[k]}"
            pet_text += ")"
        else: pet_text = "ندارد"
        text += f"🐾 پت: {pet_text}\n"
    text += f"📦 انبار: {inv_count}/{inv_cap}\n"
    text += f"🏞️ زمین‌ها: {user.get('max_plots', 1)}\n"
    if "worker" in feats:
        workers = user.get("workers", {})
        pw = workers.get("planting", {})
        hw = workers.get("harvest_sell", {})
        if pw.get("active"):
            try:
                exp = datetime.fromisoformat(pw["expires_at"])
                rem = exp - datetime.now()
                h = int(rem.total_seconds() // 3600)
                text += f"🌱 کارگر کاشت: فعال ({h}s)\n"
            except: text += f"🌱 کارگر کاشت: فعال\n"
        if hw.get("active"):
            try:
                exp = datetime.fromisoformat(hw["expires_at"])
                rem = exp - datetime.now()
                h = int(rem.total_seconds() // 3600)
                text += f"💼 کارگر برداشت/فروش: فعال ({h}s)\n"
            except: text += f"💼 کارگر برداشت/فروش: فعال\n"
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
                else: text += f"• زمین {i+1}: 🍅 {fruit}\n"
            elif p["state"] == "harvested":
                text += f"• زمین {i+1}: 📦 {fruit} (برداشت)\n"
            else: text += f"• زمین {i+1}: خالی\n"
    text += f"\n🌱 میوه انتخابی: {FRUITS[user['current_fruit']]}\n\n"
    text += f"🍎 **قیمت‌ها (خرید | فروش | XP):**\n"
    for i in get_available_fruits(user):
        bp = int(PRICES[i][0] * mult * effects["buy_mult"])
        sp = int(PRICES[i][1] * mult * effects["sell_mult"])
        if FRUITS[i] in XP_FROM_SALES:
            xp_min, xp_max = XP_FROM_SALES[FRUITS[i]]
            xp_text = f"{xp_min}" if xp_min == xp_max else f"{xp_min}-{xp_max}"
        else: xp_text = "0"
        mark = "✅ " if i == user["current_fruit"] else ""
        text += f"{mark}{FRUITS[i]}: {bp:,} | {sp:,} | ⭐{xp_text}\n"
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

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# ==================== ADMIN COMMANDS ====================
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied."); return
    text = ("👑 **ADMIN PANEL**\n\n"
            "**User Management:**\n"
            "`/user_info <user_id>`\n"
            "`/give_coins <user_id> <amount>`\n"
            "`/set_coins <user_id> <amount>`\n"
            "`/set_level <user_id> <level>`\n"
            "`/set_xp <user_id> <xp>`\n"
            "`/set_prestige <user_id> <prestige>`\n"
            "`/give_pet <user_id> <type>` (phoenix/sell/speed/xp)\n"
            "`/reset_user <user_id>`\n"
            "`/ban <user_id>` / `/unban <user_id>`\n\n"
            "**System:**\n"
            "`/stats` — Bot stats\n"
            "`/broadcast <message>`\n"
            "`/reset_season` / `/reset_league`\n"
            "`/events` / `/end_event`\n\n"
            "**Event:**\n"
            "`/event <buy> <sell> <growth> <xp> <hours> <msg>`\n\n"
            "**Gift Code:**\n"
            "`/giftcode <amount> <all|num> <hours> <code>`")
    await message.answer(text)

@dp.message(Command("user_info"))
async def cmd_user_info(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 2: await message.answer("❌ `/user_info <user_id>`"); return
    t = get_user(p[1])
    if not t: await message.answer("❌ User not found."); return
    pet_name = t.get('pet', {}).get('name', '-') if t.get('pet') else '-'
    await message.answer(f"👤 **{p[1]}**\nName: {t.get('name')}\n💰 {t['coins']:,}\n"
                          f"📈 Lv{t['level']} | XP {t['xp']}\n⭐ P{t.get('prestige',0)}\n"
                          f"📦 {get_inv_count(t)}/{get_inv_capacity(t)}\n🏞️ {t.get('max_plots',1)}\n"
                          f"🐾 {pet_name}")

@dp.message(Command("give_coins"))
async def cmd_give_coins(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 3: return
    try: amt = int(p[2])
    except: return
    t = get_user(p[1])
    if not t: await message.answer("❌"); return
    nc = t["coins"] + amt
    update_user(int(p[1]), {"coins": nc})
    update_leaderboard(int(p[1]), t["name"], nc, t["level"], t["prestige"])
    await message.answer(f"✅ +{amt:,} to {t['name']}\n💰 {nc:,}")

@dp.message(Command("set_coins"))
async def cmd_set_coins(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 3: return
    try: amt = int(p[2])
    except: return
    t = get_user(p[1])
    if not t: return
    update_user(int(p[1]), {"coins": amt})
    update_leaderboard(int(p[1]), t["name"], amt, t["level"], t["prestige"])
    await message.answer(f"✅ {t['name']} coins = {amt:,}")

@dp.message(Command("set_level"))
async def cmd_set_level(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 3: return
    try: lv = int(p[2])
    except: return
    if lv < 1 or lv > 7: await message.answer("❌ Level 1-7"); return
    t = get_user(p[1])
    if not t: return
    update_user(int(p[1]), {"level": lv})
    await message.answer(f"✅ {t['name']} Lv = {lv}")

@dp.message(Command("set_xp"))
async def cmd_set_xp(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 3: return
    try: xp = int(p[2])
    except: return
    t = get_user(p[1])
    if not t: return
    update_user(int(p[1]), {"xp": xp})
    await message.answer(f"✅ {t['name']} XP = {xp}")

@dp.message(Command("set_prestige"))
async def cmd_set_prestige(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 3: return
    try: pr = int(p[2])
    except: return
    if pr < 0 or pr > 10: return
    t = get_user(p[1])
    if not t: return
    m = 1.5 ** pr
    update_user(int(p[1]), {"prestige": pr, "prestige_multiplier": m})
    await message.answer(f"✅ {t['name']} Prestige = {pr} ({m:.2f}x)")

@dp.message(Command("give_pet"))
async def cmd_give_pet(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 3: await message.answer("❌ Types: phoenix/sell/speed/xp"); return
    t = get_user(p[1])
    if not t: return
    ty = p[2].lower()
    if ty == "phoenix":
        update_user(int(p[1]), {"pet": PHOENIX_PET, "phoenix_owned": True})
        await message.answer("✅ Phoenix given.")
    elif ty in ["sell", "speed", "xp"]:
        update_user(int(p[1]), {"pet": {"name": f"Pet-{ty}", "emoji": "🐾", "type": ty, "value": 50}})
        await message.answer(f"✅ Pet '{ty}' (50%) given.")
    else: await message.answer("❌ phoenix/sell/speed/xp")

@dp.message(Command("reset_user"))
async def cmd_reset_user(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 2: return
    t = get_user(p[1])
    if not t: return
    nu = create_default_user(int(p[1]))
    nu["name"] = t["name"]; nu["referral_code"] = t["referral_code"]
    nu["achievements"] = t.get("achievements", [])
    data = load_data(); data["users"][p[1]] = nu; save_data(data)
    await message.answer(f"✅ {t['name']} reset.")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 2: return
    data = load_data()
    if p[1] not in data.get("banned", []):
        data.setdefault("banned", []).append(p[1]); save_data(data)
    await message.answer(f"🚫 {p[1]} banned.")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split()
    if len(p) < 2: return
    data = load_data()
    if p[1] in data.get("banned", []):
        data["banned"].remove(p[1]); save_data(data)
    await message.answer(f"✅ {p[1]} unbanned.")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id): return
    data = load_data()
    users = data.get("users", {})
    tc = sum(u.get("coins", 0) for u in users.values())
    tp = sum(u.get("prestige", 0) for u in users.values())
    gf = len([c for c in data.get("gift_codes", {}).values() if datetime.now() < datetime.fromisoformat(c['end_time'])])
    await message.answer(f"📊 **Stats**\n👥 {len(users):,}\n💰 {tc:,}\n⭐ P {tp}\n"
                          f"🏰 {len(data.get('clans',{}))}\n🎟️ {gf}\n"
                          f"🎉 {'On' if get_active_event() else 'Off'}\n🚫 {len(data.get('banned',[]))}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id): return
    txt = message.text.replace("/broadcast", "", 1).strip()
    if not txt: await message.answer("❌ Empty"); return
    data = load_data(); s = 0; f = 0
    for u in data.get("users", {}).keys():
        try:
            await bot.send_message(int(u), f"📢 **Announcement:**\n\n{txt}"); s += 1
        except: f += 1
        await asyncio.sleep(0.05)
    await message.answer(f"✅ {s} | ❌ {f}")

@dp.message(Command("reset_season"))
async def cmd_reset_season(message: Message):
    if not is_admin(message.from_user.id): return
    data = load_data(); data["game_start_time"] = datetime.now().isoformat(); save_data(data)
    await message.answer("✅ Seasons reset.")

@dp.message(Command("reset_league"))
async def cmd_reset_league(message: Message):
    if not is_admin(message.from_user.id): return
    data = load_data(); data["leagues"] = {}; save_data(data)
    await message.answer("✅ Leagues reset.")

@dp.message(Command("event"))
async def cmd_event(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split(maxsplit=6)
    if len(p) < 7:
        await message.answer("❌ `/event <buy> <sell> <growth> <xp> <hours> <msg>`"); return
    try:
        bm = float(p[1]); sm = float(p[2]); gm = float(p[3]); xm = float(p[4]); h = float(p[5]); msg = p[6]
    except Exception as e:
        await message.answer(f"❌ {e}"); return
    end = datetime.now() + timedelta(hours=h)
    data = load_data()
    data["active_event"] = {"buy_mult": bm, "sell_mult": sm, "growth_mult": gm, "xp_mult": xm,
                             "end_time": end.isoformat(), "message": msg,
                             "created_at": datetime.now().isoformat()}
    save_data(data)
    await message.answer(f"✅ Event! Buy×{bm} Sell×{sm} Growth×{gm} XP×{xm} for {h}h\n📢 {msg}")
    bt = f"🎉 **Event!**\n\n{msg}\n\n💰×{bm} 💵×{sm} ⚡×{gm} ⭐×{xm}\n⏰ {h}h"
    for u in data.get("users", {}).keys():
        try: await bot.send_message(int(u), bt)
        except: pass
        await asyncio.sleep(0.05)

@dp.message(Command("end_event"))
async def cmd_end_event(message: Message):
    if not is_admin(message.from_user.id): return
    data = load_data(); data["active_event"] = None; save_data(data)
    await message.answer("✅ Event ended.")

@dp.message(Command("events"))
async def cmd_events(message: Message):
    if not is_admin(message.from_user.id): return
    ev = get_active_event()
    if not ev: await message.answer("No active event."); return
    end = datetime.fromisoformat(ev["end_time"])
    rem = end - datetime.now()
    h = int(rem.total_seconds() // 3600); m = int((rem.total_seconds() % 3600) // 60)
    await message.answer(f"🎉 **Event** ({h}h {m}m)\n💰×{ev['buy_mult']}\n💵×{ev['sell_mult']}\n"
                          f"⚡×{ev['growth_mult']}\n⭐×{ev['xp_mult']}\n📢 {ev['message']}")

@dp.message(Command("giftcode"))
async def cmd_giftcode(message: Message):
    if not is_admin(message.from_user.id): return
    p = message.text.split(maxsplit=4)
    if len(p) < 5:
        await message.answer("❌ `/giftcode <amount> <all|num> <hours> <code>`"); return
    try:
        amt = int(p[1]); ls = p[2].lower(); h = float(p[3]); code = p[4].strip()
    except Exception as e: await message.answer(f"❌ {e}"); return
    if not code.startswith("/"): await message.answer("❌ Code must start with `/`."); return
    if len(code) < 2: await message.answer("❌ Too short."); return
    if ls == "all": mu = "all"
    else:
        try: mu = int(ls)
        except: await message.answer("❌ all or number."); return
    end = datetime.now() + timedelta(hours=h)
    data = load_data()
    data.setdefault("gift_codes", {})[code] = {"amount": amt, "max_users": mu,
                                                "end_time": end.isoformat(),
                                                "used_by": [], "created_at": datetime.now().isoformat()}
    save_data(data)
    lt = "all" if mu == "all" else f"first {mu}"
    await message.answer(f"✅ Gift Code!\n🎟️ `{code}`\n💰 {amt:,}\n👥 {lt}\n⏰ {h}h")
    bt = f"🎟️ **Gift Code!**\n\nSend to get {amt:,} coins:\n`{code}`\n\n⏰ {h}h | 👥 {lt}"
    for u in data.get("users", {}).keys():
        try: await bot.send_message(int(u), bt)
        except: pass
        await asyncio.sleep(0.05)

# ==================== USER COMMANDS ====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.answer("🚫 You are banned."); return
    check_all_harvests(user_id)
    process_workers(user_id)
    check_period_reset(user_id)
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
    check_all_harvests(uid); process_workers(uid); check_period_reset(uid)
    user = get_user(uid)
    if not user: return
    await message.answer(build_status_text(user, uid), reply_markup=get_keyboard(uid))

@dp.message(Command("gift"))
async def cmd_gift(message: Message, state: FSMContext):
    uid = message.from_user.id
    check_all_harvests(uid); process_workers(uid)
    user = get_user(uid)
    if not user or not has_feature(user, "gift"):
        await message.answer("🔒 لول ۶ باز می‌شود."); return
    await state.set_state(UserForm.gift_target)
    await message.answer("🎁 نام یا کد کاربر مقصد:")

@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"🆔 آیدی عددی شما:\n`{message.from_user.id}`")

# ==================== FSM ====================
@dp.message(UserForm.name)
async def process_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    name = message.text.strip()
    if len(name) < 3 or " " in name:
        await message.answer("❌ حداقل ۳ حرف، بدون فاصله:"); return
    data = load_data()
    for _, u in data["users"].items():
        if u.get("name", "").lower() == name.lower():
            await message.answer("❌ تکراریه:"); return
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
        amt = int(message.text.strip())
        if amt <= 0: raise ValueError
    except:
        await message.answer("❌ عدد مثبت:"); return
    d = await state.get_data()
    tq = d.get("gift_target")
    if user["coins"] < amt:
        await state.clear()
        await message.answer(f"❌ موجودی کافی نیست. موجودی: {user['coins']:,}"); return
    tid, tg = find_user_by_name_or_code(tq)
    if not tid or tid == str(uid):
        await state.clear()
        await message.answer("❌ کاربر پیدا نشد یا نمی‌تونی به خودت هدیه بدی."); return
    await state.update_data(tr_type="gift", tr_target_id=tid,
                             tr_target_name=tg["name"], tr_amount=amt)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🎁 **تأیید هدیه**\n\n"
            f"👤 به: **{tg['name']}**\n"
            f"💰 مبلغ: **{amt:,}** سکه\n"
            f"💼 موجودی فعلی: {user['coins']:,}\n"
            f"💼 بعد از انتقال: {user['coins'] - amt:,}\n\n"
            f"⚠️ آیا مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())

@dp.message(UserForm.clan_name)
async def process_clan_name(message: Message, state: FSMContext):
    uid = message.from_user.id; user = get_user(uid)
    if not user: return
    name = message.text.strip()
    if len(name) < 3 or len(name) > 20 or " " in name:
        await message.answer("❌ ۳-۲۰ کاراکتر، بدون فاصله:"); return
    data = load_data()
    for c in data.get("clans", {}).values():
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
    uid = message.from_user.id; user = get_user(uid)
    if not user or not user.get("clan_id"): await state.clear(); return
    tid, tg = find_user_by_name_or_code(message.text.strip())
    if not tid: await message.answer("❌ پیدا نشد."); return
    if tg.get("clan_id"): await message.answer("❌ در کلن دیگه‌ایه."); return
    data = load_data(); clan = data["clans"].get(user["clan_id"])
    if not clan: await state.clear(); return
    if len(clan["members"]) >= CLAN_MAX_MEMBERS.get(clan["level"], 10):
        await message.answer("❌ کلن پر است!"); return
    clan["members"].append(str(tid)); clan["member_names"][str(tid)] = tg["name"]
    save_data(data); update_user(int(tid), {"clan_id": user["clan_id"]})
    await state.clear(); await message.answer(f"✅ {tg['name']} اضافه شد.")

@dp.message(UserForm.clan_donate)
async def process_clan_donate(message: Message, state: FSMContext):
    uid = message.from_user.id; user = get_user(uid)
    if not user or not user.get("clan_id"): await state.clear(); return
    try:
        amt = int(message.text.strip())
        if amt < 10000: raise ValueError
    except:
        await state.clear()
        await message.answer("❌ حداقل ۱۰,۰۰۰ سکه. عملیات لغو شد."); return
    if user["coins"] < amt:
        await state.clear()
        await message.answer(f"❌ موجودی کافی نیست. موجودی: {user['coins']:,}"); return
    clan = get_clan(user["clan_id"])
    if not clan: await state.clear(); return
    await state.update_data(tr_type="clan_donate", tr_amount=amt,
                             tr_clan_id=user["clan_id"], tr_clan_name=clan["name"])
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🏰 **تأیید اهدا به خزانه**\n\n"
            f"🏰 کلن: **{clan['name']}**\n"
            f"💰 مبلغ: **{amt:,}** سکه\n"
            f"💼 موجودی فعلی: {user['coins']:,}\n"
            f"💼 بعد از اهدا: {user['coins'] - amt:,}\n\n"
            f"⚠️ آیا مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())

@dp.message(UserForm.clan_chat)
async def process_clan_chat(message: Message, state: FSMContext):
    uid = message.from_user.id; user = get_user(uid)
    if not user or not user.get("clan_id"): await state.clear(); return
    clan = get_clan(user["clan_id"])
    if not clan: await state.clear(); return
    msg = f"🏰 **کلن - {user['name']}:**\n\n{message.text}"
    for m in clan["members"]:
        try: await bot.send_message(int(m), msg)
        except: pass
    await state.clear()

# ==================== کارگرها FSM ====================
@dp.message(UserForm.worker_plant_hours)
async def wp_hours_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 72:
            await message.answer("❌ عدد بین ۱ تا ۷۲ وارد کن:"); return
    except:
        await message.answer("❌ عدد وارد کن:"); return
    d = await state.get_data()
    fruit_idx = d.get("wp_fruit")
    if fruit_idx is None:
        await state.clear(); return
    eff, _ = get_season_effects()
    sp = int(PRICES[fruit_idx][1] * user["prestige_multiplier"] * eff["sell_mult"])
    total_cost = (sp // 3) * hours
    await state.update_data(wp_hours=hours, wp_cost=total_cost)
    text = (f"🌱 **تأیید اجاره‌ی کارگر کاشت**\n\n"
            f"🍎 میوه: {FRUITS[fruit_idx]}\n"
            f"⏰ مدت: {hours} ساعت\n"
            f"💰 هزینه: {total_cost:,} سکه\n\n"
            f"💵 موجودی: {user['coins']:,}\n"
            f"❗️ هزینه هم‌اکنون کسر می‌شود.")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="wp_confirm")
    kb.button("❌ لغو", callback_data="wp_cancel")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())

@dp.message(UserForm.worker_harvest_hours)
async def wh_hours_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 72:
            await message.answer("❌ عدد بین ۱ تا ۷۲:"); return
    except:
        await message.answer("❌ عدد وارد کن:"); return
    await state.update_data(wh_hours=hours)
    text = (f"💼 **تأیید اجاره‌ی کارگر برداشت و فروش**\n\n"
            f"⏰ مدت: {hours} ساعت\n"
            f"💰 هزینه: رایگان\n"
            f"📊 کمیسیون: ۲۰٪ از هر فروش\n\n"
            f"✅ تأیید می‌کنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="wh_confirm")
    kb.button("❌ لغو", callback_data="wh_cancel")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())

@dp.message(UserForm.confirm_transfer)
async def cancel_on_unexpected(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    await message.answer(
        "❌ **عملیات لغو شد.**\n"
        "چون به‌جای تأیید یا لغو، پیام دیگه‌ای فرستادی.",
        reply_markup=get_keyboard(uid))

# ==================== PAYMENT ====================
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
    gm = ""
    if len(parts) >= 4 and parts[3] == "phoenix":
        coins = int(parts[2])
        nc = user["coins"] + coins
        update_user(uid, {"coins": nc, "pet": PHOENIX_PET, "phoenix_owned": True, "pending_purchase": None})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        await message.answer(f"✅ پرداخت موفق!\n🪙 +{coins:,}\n🦅 ققنوس!", reply_markup=get_keyboard(uid))
        return
    try: coins = int(parts[2])
    except: return
    nc = user["coins"] + coins
    if amount == 50000:
        fi = random.choice(get_available_fruits(user))
        inv[FRUITS[fi]] = inv.get(FRUITS[fi], 0) + 1
        gm = f"\n🎁 {FRUITS[fi]}"
    elif amount == 100000:
        fi = random.randint(0, len(FRUITS)-1)
        inv[f"طلایی_{FRUITS[fi]}"] = inv.get(f"طلایی_{FRUITS[fi]}", 0) + 1
        gm = f"\n✨ طلایی {FRUITS[fi]}"
    update_user(uid, {"coins": nc, "inventory": inv, "pending_purchase": None})
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await message.answer(f"✅ پرداخت موفق!\n🪙 +{coins:,}\n💼 {nc:,}{gm}", reply_markup=get_keyboard(uid))

# ==================== GIFT CODES ====================
@dp.message(F.text.startswith("/"))
async def handle_gift_codes(message: Message, state: FSMContext):
    text = message.text.strip()
    uid = message.from_user.id
    data = load_data()
    codes = data.get("gift_codes", {})
    if text not in codes: return
    cd = codes[text]
    try:
        end = datetime.fromisoformat(cd["end_time"])
        if datetime.now() >= end:
            await message.answer("❌ این گیفت کد منقضی شده."); return
    except: return
    if str(uid) in cd.get("used_by", []):
        await message.answer("❌ قبلاً استفاده کرده‌ای."); return
    mu = cd["max_users"]
    if mu != "all" and len(cd.get("used_by", [])) >= mu:
        await message.answer("❌ ظرفیت پر شده."); return
    user = get_user(uid)
    if not user: await message.answer("❌ اول /start"); return
    amt = cd["amount"]; nc = user["coins"] + amt
    cd.setdefault("used_by", []).append(str(uid))
    data["users"][str(uid)]["coins"] = nc
    data["gift_codes"][text] = cd
    save_data(data)
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await message.answer(f"🎉 **تبریک!**\n✅ کد `{text}`\n💰 +{amt:,}\n💼 {nc:,}")

# ==================== TEXT COMMANDS ====================
@dp.message()
async def handle_text_commands(message: Message, state: FSMContext):
    if not message.text: return
    txt = message.text.strip()
    if txt.startswith("/"): return
    if txt not in TEXT_COMMANDS: return
    action = TEXT_COMMANDS[txt]
    uid = message.from_user.id
    if is_banned(uid): return
    check_all_harvests(uid); process_workers(uid); check_period_reset(uid)
    user = get_user(uid)
    if not user: return
    if action == "buy_seed_text":
        if user["max_plots"] == 1:
            fake = FakeCallback(message, data=f"owner_{uid}_buy_0")
            await buy_seed_for_plot(fake, user, uid, 0)
        else:
            fake = FakeCallback(message, data=f"owner_{uid}_lands_menu")
            await show_lands_menu(fake, user, uid)
        return
    if action == "harvest_text":
        if user["max_plots"] == 1:
            fake = FakeCallback(message, data=f"owner_{uid}_harvest_0")
            await harvest_plot(fake, user, uid, 0)
        else:
            fake = FakeCallback(message, data=f"owner_{uid}_lands_menu")
            await show_lands_menu(fake, user, uid)
        return
    fake = FakeCallback(message, data=f"owner_{uid}_{action}")
    try:
        await on_callback(fake, state)
    except Exception as e:
        print(f"Error: {e}")

# ==================== CONFIRM CALLBACKS ====================
@dp.callback_query(F.data == "confirm_yes")
async def confirm_transfer_yes(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    d = await state.get_data()
    tr_type = d.get("tr_type")
    amt = d.get("tr_amount")
    if not tr_type or amt is None:
        await state.clear()
        await callback.message.edit_text("❌ اطلاعات ناقص. لغو شد.", reply_markup=get_keyboard(uid))
        return
    if user["coins"] < amt:
        await state.clear()
        await callback.message.edit_text("❌ موجودی کافی نیست.", reply_markup=get_keyboard(uid)); return
    if tr_type == "gift":
        tid = d.get("tr_target_id"); tname = d.get("tr_target_name")
        target = get_user(tid)
        if not target:
            await state.clear()
            await callback.message.edit_text("❌ کاربر پیدا نشد.", reply_markup=get_keyboard(uid)); return
        update_user(uid, {"coins": user["coins"] - amt, "gifts_given": user.get("gifts_given", 0) + 1})
        update_user(int(tid), {"coins": target["coins"] + amt, "gifts_received": target.get("gifts_received", 0) + 1})
        update_leaderboard(uid, user["name"], user["coins"] - amt, user["level"], user["prestige"])
        update_leaderboard(int(tid), target["name"], target["coins"] + amt, target["level"], target["prestige"])
        await state.clear()
        await callback.message.edit_text(
            f"✅ **هدیه ارسال شد!**\n👤 {tname}\n💰 {amt:,}\n💼 {user['coins'] - amt:,}",
            reply_markup=get_keyboard(uid))
    elif tr_type == "clan_donate":
        cid = d.get("tr_clan_id"); cname = d.get("tr_clan_name")
        data = load_data(); clan = data["clans"].get(cid)
        if not clan:
            await state.clear()
            await callback.message.edit_text("❌ کلن پیدا نشد.", reply_markup=get_keyboard(uid)); return
        clan["treasury"] += amt; save_data(data)
        update_user(uid, {"coins": user["coins"] - amt})
        await state.clear()
        await callback.message.edit_text(
            f"✅ **اهدا انجام شد!**\n🏰 {cname}\n💰 {amt:,}\n💼 {user['coins'] - amt:,}\n🏦 {clan['treasury']:,}",
            reply_markup=get_keyboard(uid))

@dp.callback_query(F.data == "confirm_no")
async def confirm_transfer_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    await state.clear()
    await callback.message.edit_text("❌ **عملیات لغو شد.**", reply_markup=get_keyboard(uid))

@dp.callback_query(F.data == "wp_confirm")
async def wp_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    user = get_user(uid)
    if not user: return
    d = await state.get_data()
    fruit_idx = d.get("wp_fruit"); hours = d.get("wp_hours"); cost = d.get("wp_cost", 0)
    if fruit_idx is None or hours is None:
        await state.clear(); return
    if user["coins"] < cost:
        await state.clear()
        await callback.message.edit_text(f"❌ سکه کافی نیست. نیاز: {cost:,}", reply_markup=get_keyboard(uid)); return
    expires = datetime.now() + timedelta(hours=hours)
    workers = user.get("workers", {})
    workers["planting"] = {"active": True, "fruit": fruit_idx, "hours": hours, "expires_at": expires.isoformat()}
    update_user(uid, {"coins": user["coins"] - cost, "workers": workers})
    update_leaderboard(uid, user["name"], user["coins"] - cost, user["level"], user["prestige"])
    await state.clear()
    await callback.message.edit_text(
        f"✅ **کارگر کاشت اجاره شد!**\n🍎 {FRUITS[fruit_idx]}\n⏰ {hours} ساعت\n💰 {cost:,}",
        reply_markup=get_keyboard(uid))

@dp.callback_query(F.data == "wp_cancel")
async def wp_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ لغو شد.", reply_markup=get_keyboard(callback.from_user.id))

@dp.callback_query(F.data == "wh_confirm")
async def wh_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    user = get_user(uid)
    if not user: return
    d = await state.get_data()
    hours = d.get("wh_hours")
    if hours is None:
        await state.clear(); return
    expires = datetime.now() + timedelta(hours=hours)
    workers = user.get("workers", {})
    workers["harvest_sell"] = {"active": True, "hours": hours, "expires_at": expires.isoformat()}
    update_user(uid, {"workers": workers})
    await state.clear()
    await callback.message.edit_text(
        f"✅ **کارگر برداشت و فروش اجاره شد!**\n⏰ {hours} ساعت\n📊 کمیسیون ۲۰٪",
        reply_markup=get_keyboard(uid))

@dp.callback_query(F.data == "wh_cancel")
async def wh_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ لغو شد.", reply_markup=get_keyboard(callback.from_user.id))

# ==================== MAIN CALLBACK ====================
@dp.callback_query()
async def on_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    if is_banned(uid): return
    
    raw_data = callback.data or ""
    
    if raw_data.startswith("owner_"):
        parts = raw_data.split("_", 2)
        owner_id = parts[1]
        real_action = parts[2] if len(parts) > 2 else "noop"
        if str(uid) != owner_id:
            try:
                await callback.answer("⛔ این دکمه مال شما نیست!", show_alert=True)
            except: pass
            return
        data = real_action
    else:
        if raw_data in ["confirm_yes", "confirm_no", "wp_confirm", "wp_cancel", "wh_confirm", "wh_cancel"]:
            return
        data = raw_data
    
    check_all_harvests(uid); process_workers(uid); check_period_reset(uid)
    user = get_user(uid)
    if not user: return
    
    if data == "noop": return
    elif data == "status": await edit_status(callback, user, uid)
    elif data == "admin_panel": await show_admin_panel(callback, uid)
    elif data == "lands_menu": await show_lands_menu(callback, user, uid)
    elif data == "inventory_menu": await show_inventory(callback, user, uid)
    elif data.startswith("buy_"):
        await buy_seed_for_plot(callback, user, uid, int(data.split("_")[1]))
    elif data.startswith("harvest_"):
        await harvest_plot(callback, user, uid, int(data.split("_")[1]))
    elif data.startswith("sell_inv_"):
        await sell_from_inventory(callback, user, uid, data.replace("sell_inv_", ""))
    elif data.startswith("plant_plot_"):
        p = data.split("_"); await plant_in_plot(callback, user, uid, int(p[2]), int(p[3]))
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
    elif data == "hire_planting": await start_hire_planting(callback, user, uid)
    elif data == "hire_harvest":
        await state.set_state(UserForm.worker_harvest_hours)
        await start_hire_harvest(callback, user, uid)
    elif data.startswith("wp_fruit_"):
        fruit_idx = int(data.replace("wp_fruit_", ""))
        if fruit_idx not in get_available_fruits(user):
            await callback.message.edit_text("❌", reply_markup=get_keyboard(uid)); return
        await state.update_data(wp_fruit=fruit_idx)
        await state.set_state(UserForm.worker_plant_hours)
        await callback.message.edit_text(
            f"🌱 میوه: **{FRUITS[fruit_idx]}**\n\n"
            f"⏰ چند ساعت کار کنه؟ (عدد بفرست، مثلاً `5`)\n"
            f"حداکثر: ۷۲ ساعت",
            reply_markup=get_keyboard(uid))
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

# ==================== SHOW FUNCTIONS ====================
async def show_admin_panel(callback, uid):
    if not is_admin(uid): return
    text = "👑 **ADMIN PANEL**\n\nSend commands. Type `/admin` for full list."
    kb = InlineKeyboardBuilder()
    kb.button("🔙 Back", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def show_main_menu(message: Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user: return
    _, season = get_season_effects()
    p = f"⭐ پرستیژ {user['prestige']}" if user['prestige'] > 0 else "بدون پرستیژ"
    plots = user.get("plots", [])
    pt = ""
    for i, pl in enumerate(plots):
        fr = FRUITS[pl.get("fruit", 0)]
        if pl["state"] == "growing":
            rem = get_plot_remaining(pl)
            t = f"{rem//60}:{rem%60:02d}" if rem else "..."
            pt += f"🏞 {i+1}: {fr} ({t})\n"
        elif pl["state"] == "harvested":
            pt += f"🏞 {i+1}: 📦 {fr}\n"
        else: pt += f"🏞 {i+1}: خالی\n"
    et = ""
    ev = get_active_event()
    if ev: et = f"\n🎉 **ایونت فعال!** {ev['message']}\n"
    text = (f"🌾 **مزرعه‌ی {user['name']}**\n\n"
            f"🌤 فصل: {SEASON_FA[season]}\n💰 سکه: {user['coins']:,}\n"
            f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
            f"⭐ {p}\n📦 انبار: {get_inv_count(user)}/{get_inv_capacity(user)}\n"
            f"{et}\n{pt}\n"
            f"💡 **دستورات:** وضعیت، پت، لیدربرد، انبار، کارگرها، ...")
    await message.answer(text, reply_markup=get_keyboard(uid))

async def edit_status(callback, user, uid):
    await callback.message.edit_text(build_status_text(user, uid), reply_markup=get_keyboard(uid))

async def show_lands_menu(callback, user, uid):
    plots = user.get("plots", []); mp = user.get("max_plots", 1)
    prefix = f"owner_{uid}_"
    text = f"🏞️ **زمین‌های شما ({mp})**\n\n"
    kb = InlineKeyboardBuilder()
    for i, p in enumerate(plots):
        fr = FRUITS[p.get("fruit", 0)]
        if p["state"] == "growing":
            rem = get_plot_remaining(p)
            t = f"{rem//60}:{rem%60:02d}" if rem is not None else "..."
            text += f"🏞 {i+1}: ⏳ {fr} ({t})\n"
            kb.button(f"🏞{i+1} ⏳", callback_data="noop")
        elif p["state"] == "harvested":
            text += f"🏞 {i+1}: 📦 {fr}\n"
            kb.button(f"🏞{i+1} 📦 {fr}", callback_data=f"{prefix}harvest_{i}")
        else:
            text += f"🏞 {i+1}: خالی\n"
            kb.button(f"🏞{i+1} 🌱", callback_data=f"{prefix}buy_{i}")
    np = get_land_price(mp)
    if np:
        text += f"\n🛒 زمین {mp+1}: {np:,}"
        kb.button(f"🛒 ({np:,})", callback_data=f"{prefix}buy_land")
    kb.button("📦 انبار", callback_data=f"{prefix}inventory_menu")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def show_inventory(callback, user, uid):
    inv = user.get("inventory", {}); cap = get_inv_capacity(user); c = get_inv_count(user)
    prefix = f"owner_{uid}_"
    text = f"📦 **انبار ({c}/{cap})**\n\n"
    kb = InlineKeyboardBuilder()
    if not inv: text += "خالیه!"
    else:
        for fn, cnt in inv.items():
            if fn.startswith("طلایی_"):
                text += f"✨ {fn.replace('طلایی_','')} (طلایی): {cnt}\n"
            else:
                text += f"🍎 {fn}: {cnt}\n"
                kb.button(f"💰 {fn}", callback_data=f"{prefix}sell_inv_{fn}")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_land(callback, user, uid):
    mp = user.get("max_plots", 1); pr = get_land_price(mp)
    if pr is None: await callback.message.edit_text("✅ حداکثر!", reply_markup=get_keyboard(uid)); return
    if user["coins"] < pr: await callback.message.edit_text(f"❌ {pr:,}", reply_markup=get_keyboard(uid)); return
    plots = user.get("plots", [])
    plots.append({"fruit": 0, "state": "idle", "harvest_time": None})
    update_user(uid, {"coins": user["coins"] - pr, "plots": plots, "max_plots": mp + 1})
    update_leaderboard(uid, user["name"], user["coins"] - pr, user["level"], user["prestige"])
    await callback.message.edit_text(f"🎉 زمین {mp+1}!", reply_markup=get_keyboard(uid))

async def buy_seed_for_plot(callback, user, uid, idx):
    plots = user.get("plots", [])
    if idx >= len(plots): return
    plot = plots[idx]
    if plot["state"] == "growing": await callback.message.edit_text("⏳", reply_markup=get_keyboard(uid)); return
    if plot["state"] == "harvested": await callback.message.edit_text("📦 اول برداشت.", reply_markup=get_keyboard(uid)); return
    avail = get_available_fruits(user); eff, _ = get_season_effects(); m = user["prestige_multiplier"]
    prefix = f"owner_{uid}_"
    text = f"🌱 **کاشت زمین {idx+1}**\n\n"
    kb = InlineKeyboardBuilder()
    for i in avail:
        bp = int(PRICES[i][0] * m * eff["buy_mult"])
        text += f"• {FRUITS[i]}: {bp:,}\n"
        kb.button(f"🌱 {FRUITS[i]} ({bp:,})", callback_data=f"{prefix}plant_plot_{idx}_{i}")
    kb.button("🔙", callback_data=f"{prefix}lands_menu")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def plant_in_plot(callback, user, uid, pidx, fidx):
    plots = user.get("plots", [])
    if pidx >= len(plots) or fidx not in get_available_fruits(user): return
    eff, _ = get_season_effects()
    bp = int(PRICES[fidx][0] * user["prestige_multiplier"] * eff["buy_mult"])
    if user["coins"] < bp: await callback.message.edit_text(f"❌ {bp:,}", reply_markup=get_keyboard(uid)); return
    gt = GROWTH_TIMES[fidx] * eff["growth_mult"]
    if user["upgrades"].get("auto_water", 0) > 0: gt *= 0.8
    sb = get_pet_effect(user, "speed")
    if sb > 0: gt *= (1 - sb / 100)
    ht = datetime.now() + timedelta(minutes=gt)
    plots[pidx] = {"fruit": fidx, "state": "growing", "harvest_time": ht.isoformat()}
    update_user(uid, {"coins": user["coins"] - bp, "plots": plots, "current_fruit": fidx})
    mi = int(gt); se = int((gt - mi) * 60)
    await callback.message.edit_text(f"🌱 {FRUITS[fidx]}! ⏳ {mi}:{se:02d}", reply_markup=get_keyboard(uid))

async def harvest_plot(callback, user, uid, idx):
    plots = user.get("plots", [])
    if idx >= len(plots): return
    p = plots[idx]
    if p["state"] != "harvested": await callback.message.edit_text("⏳", reply_markup=get_keyboard(uid)); return
    fn = FRUITS[p.get("fruit", 0)]
    if not add_to_inventory(uid, fn):
        await callback.message.edit_text(f"📦 پره! ({get_inv_count(user)}/{get_inv_capacity(user)})", reply_markup=get_keyboard(uid)); return
    plots[idx] = {"fruit": 0, "state": "idle", "harvest_time": None}
    update_user(uid, {"plots": plots})
    await callback.message.edit_text(f"📦 {fn} به انبار!", reply_markup=get_keyboard(uid))

async def sell_from_inventory(callback, user, uid, fn):
    inv = user.get("inventory", {})
    if inv.get(fn, 0) < 1: await callback.message.edit_text("❌", reply_markup=get_keyboard(uid)); return
    try: cf = FRUITS.index(fn)
    except: await callback.message.edit_text("❌", reply_markup=get_keyboard(uid)); return
    inv[fn] -= 1
    if inv[fn] <= 0: del inv[fn]
    eff, _ = get_season_effects()
    bs = int(PRICES[cf][1] * user["prestige_multiplier"] * eff["sell_mult"])
    sp = bs
    pb = get_pet_effect(user, "sell")
    if pb > 0: sp += int(bs * pb / 100)
    cb = get_clan_bonus(user)
    if cb > 0: sp += int(bs * cb / 100)
    if user["upgrades"].get("golden_pot", 0) > 0: sp = int(sp * (1 + 0.1 * user["upgrades"]["golden_pot"]))
    g = random.random() < eff["golden_chance"]
    if g: sp *= 2
    xp = int(xp_from_sale(fn) * user["prestige_multiplier"] * eff["xp_mult"])
    px = get_pet_effect(user, "xp")
    if px > 0: xp += int(xp * px / 100)
    nc = user["coins"] + sp; nx = user["xp"] + xp; nl = user["level"]; lu = ""
    xn = xp_needed_for(nl)
    while nx >= xn and nl < 7:
        nx -= xn; nl += 1; xn = xp_needed_for(nl); lu = f"\n🎉 لول {nl}!"
    update_user(uid, {"coins": nc, "xp": nx, "level": nl, "inventory": inv})
    update_leaderboard(uid, user["name"], nc, nl, user["prestige"])
    upd = get_user(uid); update_league_profit(uid, upd, upd["coins"] - upd.get("period_start_coins", 1))
    gt = " ✨" if g else ""
    await callback.message.edit_text(f"✅ {fn}{gt}\n💰 +{sp:,}\n⭐ +{xp}\n📈 {nl}{lu}", reply_markup=get_keyboard(uid))

async def switch_fruit(callback, user, uid, idx):
    if idx not in get_available_fruits(user): await callback.message.edit_text("🔒", reply_markup=get_keyboard(uid)); return
    update_user(uid, {"current_fruit": idx})
    await callback.message.edit_text(f"✅ {FRUITS[idx]}", reply_markup=get_keyboard(uid))

async def show_leaderboard(callback, user, uid):
    data = load_data(); lb = data["leaderboard"][:10]
    text = "🏆 **لیدربرد:**\n\n"
    for i, it in enumerate(lb, 1):
        p = f"⭐{it['prestige']}" if it['prestige'] > 0 else ""
        text += f"{i}. {it['name']} {p} — لول {it['level']} | {it['coins']:,}\n"
    if not lb: text += "خالیه!"
    await callback.message.edit_text(text, reply_markup=get_keyboard(uid))

async def show_upgrades(callback, user, uid):
    u = user["upgrades"]; c1 = 1000*(u.get("auto_water",0)+1); c2 = 2000*(u.get("golden_pot",0)+1); c3 = 5000*(u.get("professional_seeder",0)+1)
    mp = user.get("max_plots", 1); lp = get_land_price(mp)
    prefix = f"owner_{uid}_"
    text = f"🔧 **ارتقاء:**\n💧 {c1:,}\n🏺 {c2:,}\n🌱 {c3:,}\n"
    kb = InlineKeyboardBuilder()
    kb.button(f"💧 ({c1:,})", callback_data=f"{prefix}upgrade_auto_water")
    kb.button(f"🏺 ({c2:,})", callback_data=f"{prefix}upgrade_golden_pot")
    kb.button(f"🌱 ({c3:,})", callback_data=f"{prefix}upgrade_professional_seeder")
    if lp:
        text += f"\n🏞️ زمین {mp+1}: {lp:,}"
        kb.button(f"🏞️ ({lp:,})", callback_data=f"{prefix}buy_land")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_upgrade(callback, user, uid, key):
    base = {"auto_water": 1000, "golden_pot": 2000, "professional_seeder": 5000}
    if key not in base: return
    cnt = user["upgrades"].get(key, 0); cost = base[key] * (cnt + 1)
    if user["coins"] < cost: await callback.message.edit_text(f"❌ {cost:,}", reply_markup=get_keyboard(uid)); return
    u = user["upgrades"]; u[key] = cnt + 1
    update_user(uid, {"coins": user["coins"] - cost, "upgrades": u})
    await callback.message.edit_text("✅ ارتقاء انجام شد!", reply_markup=get_keyboard(uid))

# ==================== ماموریت‌های ساعتی ====================
async def show_daily_orders(callback, user, uid):
    # ✅ ریست هر ساعت
    current_hour = datetime.now().strftime("%Y-%m-%d-%H")
    if user["daily_orders"]["date"] != current_hour:
        available = get_available_fruits(user)
        mission_fruits = [i for i in available if i < 6]
        if not mission_fruits: mission_fruits = [0]
        
        num_missions = min(3, len(mission_fruits))
        chosen_fruits = random.sample(mission_fruits, num_missions)
        orders = []
        for fi in chosen_fruits:
            orders.append({"fruit": FRUITS[fi], "count": random.randint(1, 3)})
        
        update_user(uid, {"daily_orders": {"date": current_hour, "orders": orders, "completed": False}})
        user = get_user(uid)
    
    orders = user["daily_orders"]["orders"]
    if user["daily_orders"]["completed"]:
        next_hour = (datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        rem = next_hour - datetime.now()
        m = int(rem.total_seconds() // 60)
        await callback.message.edit_text(
            f"📦 امروز تکمیل شده!\n⏰ ماموریت جدید تا {m} دقیقه دیگه میاد.",
            reply_markup=get_keyboard(uid))
        return
    
    inv = user.get("inventory", {})
    prefix = f"owner_{uid}_"
    text = ("📦 **ماموریت‌های ساعتی**\n\n"
            "💡 **با انجام ماموریت ×۱.۵ بیشتر سود کن!**\n\n")
    for i, o in enumerate(orders, 1):
        h = inv.get(o["fruit"], 0)
        text += f"{i}. {o['count']}× {o['fruit']} ({'✅' if h >= o['count'] else '❌'} داری: {h})\n"
    bonus = int(sum(PRICES[FRUITS.index(o["fruit"])][1] * o["count"] * 1.5 for o in orders) * user["prestige_multiplier"])
    text += f"\n💰 پاداش تقریبی: **{bonus:,}** سکه"
    
    next_hour = (datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    rem = next_hour - datetime.now()
    m = int(rem.total_seconds() // 60)
    text += f"\n⏰ ماموریت جدید: {m} دقیقه دیگه"
    
    kb = InlineKeyboardBuilder()
    kb.button("✅ تکمیل ماموریت‌ها", callback_data=f"{prefix}complete_orders")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def complete_orders(callback, user, uid):
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("قبلاً تکمیل شده!", reply_markup=get_keyboard(uid)); return
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
    current_hour = datetime.now().strftime("%Y-%m-%d-%H")
    update_user(uid, {
        "coins": nc,
        "inventory": inv,
        "daily_orders": {"date": current_hour, "orders": orders, "completed": True}
    })
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await callback.message.edit_text(f"✅ ماموریت‌ها تکمیل شد!\n💰 +{bonus:,} سکه", reply_markup=get_keyboard(uid))

async def show_shop(callback, user, uid):
    lv = user["level"]
    if lv < 4 and user.get("prestige", 0) == 0: await callback.message.edit_text("🔒 لول ۴", reply_markup=get_keyboard(uid)); return
    pr = SHOP_PRICES.get(lv, SHOP_PRICES[7])
    prefix = f"owner_{uid}_"
    text = "🛒 **فروشگاه**\n\n💰 با توجه به لول شما، مقدار سکه‌ها متفاوت است.\n\n"
    for amt, c in pr.items():
        text += f"• {amt:,} تومان → {c:,}"
        if amt == 50000: text += " + بذر"
        elif amt == 70000: text += " + 🦅"
        elif amt == 100000: text += " + ✨"
        text += "\n"
    kb = InlineKeyboardBuilder()
    for amt in pr:
        lbl = f"{amt:,}"
        if amt == 70000: lbl += " 🦅"
        elif amt == 100000: lbl += " ✨"
        if amt == 70000 and user.get("phoenix_owned"): continue
        kb.button(lbl, callback_data=f"{prefix}shop_{amt}")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_shop(callback, user, uid, amount):
    lv = user["level"] if user.get("prestige", 0) == 0 else 7
    pr = SHOP_PRICES.get(lv, SHOP_PRICES[7])
    if amount not in pr: return
    coins = pr[amount]; r = amount * 10
    update_user(uid, {"pending_purchase": {"amount": amount, "coins": coins, "created_at": datetime.now().isoformat()}})
    if amount == 70000: pl = f"shop_{amount}_{coins}_phoenix"; ti = "ققنوس"; de = f"{coins:,}+🦅"
    else: pl = f"shop_{amount}_{coins}"; ti = f"{coins:,}"; de = f"{amount:,} تومان"
    try:
        await bot.send_invoice(chat_id=uid, title=ti, description=de, payload=pl, provider_token=PROVIDER_TOKEN,
                                currency="IRR", prices=[{"label": f"{coins:,} سکه", "amount": r}])
        try: await callback.message.delete()
        except: pass
    except Exception as e: await callback.message.edit_text(f"❌ `{str(e)[:200]}`", reply_markup=get_keyboard(uid))

# ==================== کارگرها UI ====================
async def show_worker(callback, user, uid):
    workers = user.get("workers", {})
    pw = workers.get("planting", {})
    hw = workers.get("harvest_sell", {})
    prefix = f"owner_{uid}_"
    text = "👷 **کارگرها**\n\n"
    if pw.get("active"):
        try:
            exp = datetime.fromisoformat(pw["expires_at"])
            rem = exp - datetime.now()
            h = int(rem.total_seconds() // 3600)
            m = int((rem.total_seconds() % 3600) // 60)
            fname = FRUITS[pw["fruit"]] if pw.get("fruit") is not None else "?"
            text += f"🌱 **کارگر کاشت:** فعال ({fname})\n   ⏰ {h}s {m}d باقی\n\n"
        except: text += f"🌱 **کارگر کاشت:** فعال\n\n"
    else:
        text += f"🌱 **کارگر کاشت:** غیرفعال\n\n"
    if hw.get("active"):
        try:
            exp = datetime.fromisoformat(hw["expires_at"])
            rem = exp - datetime.now()
            h = int(rem.total_seconds() // 3600)
            m = int((rem.total_seconds() % 3600) // 60)
            text += f"💼 **کارگر برداشت و فروش:** فعال\n   ⏰ {h}s {m}d باقی\n\n"
        except: text += f"💼 **کارگر برداشت و فروش:** فعال\n\n"
    else:
        text += f"💼 **کارگر برداشت و فروش:** غیرفعال\n\n"
    text += ("💡 **کارگر کاشت:** فقط سیب به بالا. قیمت = ۱/۳ قیمت فروش × ساعت.\n"
             "💡 **کارگر برداشت و فروش:** رایگان، ولی ۲۰٪ از هر فروش رو می‌گیره.")
    kb = InlineKeyboardBuilder()
    if not pw.get("active"):
        kb.button("🌱 اجاره‌ی کارگر کاشت", callback_data=f"{prefix}hire_planting")
    if not hw.get("active"):
        kb.button("💼 اجاره‌ی کارگر برداشت و فروش", callback_data=f"{prefix}hire_harvest")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def start_hire_planting(callback, user, uid):
    available_planting = [i for i in get_available_fruits(user) if i >= 2]
    prefix = f"owner_{uid}_"
    if not available_planting:
        await callback.message.edit_text(
            "❌ برای اجاره‌ی کارگر کاشت، باید حداقل به لول ۳ برسی (سیب).",
            reply_markup=get_keyboard(uid))
        return
    eff, _ = get_season_effects()
    m = user["prestige_multiplier"]
    text = "🌱 **اجاره‌ی کارگر کاشت**\n\n🍎 میوه مورد نظر رو انتخاب کن:\n\n"
    kb = InlineKeyboardBuilder()
    for i in available_planting:
        sp = int(PRICES[i][1] * m * eff["sell_mult"])
        price_per_hour = sp // 3
        text += f"• {FRUITS[i]}: {price_per_hour:,} سکه/ساعت\n"
        kb.button(f"🌱 {FRUITS[i]}", callback_data=f"{prefix}wp_fruit_{i}")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}worker_menu")
    kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def start_hire_harvest(callback, user, uid):
    text = ("💼 **اجاره‌ی کارگر برداشت و فروش**\n\n"
            "📌 کارها:\n• میوه‌های رسیده رو به انبار می‌بره\n• از انبار می‌فروشه\n\n"
            "💰 هزینه: **رایگان**\n📊 کمیسیون: **۲۰٪ از هر فروش**\n\n"
            "⏰ چند ساعت کار کنه؟ (عدد بفرست، مثلاً `5`)\n"
            "حداکثر: ۷۲ ساعت")
    await callback.message.edit_text(text, reply_markup=get_keyboard(uid))

async def start_gift(callback, user, uid, state):
    await state.set_state(UserForm.gift_target)
    await callback.message.edit_text("🎁 نام یا کد کاربر:", reply_markup=get_keyboard(uid))

async def show_prestige(callback, user, uid):
    if user["level"] < 7: await callback.message.edit_text("🔒 لول ۷", reply_markup=get_keyboard(uid)); return
    if user["prestige"] >= 10: await callback.message.edit_text("⭐ حداکثر!", reply_markup=get_keyboard(uid)); return
    nx = user["prestige"] + 1; p = PRESTIGE_PRICES[nx]
    prefix = f"owner_{uid}_"
    text = f"⭐ **پرستیژ {nx}**\n{p:,}\nضریب: {user['prestige_multiplier']*1.5:.2f}x"
    kb = InlineKeyboardBuilder()
    kb.button(f"⭐ ({p:,})", callback_data=f"{prefix}buy_prestige")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_prestige(callback, user, uid):
    if user["prestige"] >= 10: return
    nx = user["prestige"] + 1; p = PRESTIGE_PRICES[nx]
    if user["coins"] < p: await callback.message.edit_text(f"❌ {p:,}", reply_markup=get_keyboard(uid)); return
    nu = create_default_user(uid)
    nu["name"] = user["name"]; nu["prestige"] = nx
    nu["prestige_multiplier"] = user["prestige_multiplier"] * 1.5
    nu["referral_code"] = user["referral_code"]
    nu["gifts_given"] = user.get("gifts_given", 0); nu["gifts_received"] = user.get("gifts_received", 0)
    nu["achievements"] = user.get("achievements", []); nu["clan_id"] = user.get("clan_id")
    nu["phoenix_owned"] = user.get("phoenix_owned", False)
    if nu["phoenix_owned"]: nu["pet"] = PHOENIX_PET
    nu["last_seen_period"] = get_period_number(); nu["current_period"] = get_period_number()
    nu["used_gift_codes"] = user.get("used_gift_codes", [])
    data = load_data(); data["users"][str(uid)] = nu; save_data(data)
    update_leaderboard(uid, user["name"], 1, 1, nx)
    await callback.message.edit_text(f"⭐ پرستیژ {nx}!\n{nu['prestige_multiplier']:.2f}x", reply_markup=get_keyboard(uid))

async def show_pet_menu(callback, user, uid):
    pet = user.get("pet")
    prefix = f"owner_{uid}_"
    if pet:
        tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
        pt = f"{pet['emoji']} {pet['name']} (+{pet['value']}٪ {tfa.get(pet['type'], '')}"
        for k in ["sell", "speed", "xp"]:
            if k != pet.get("type") and f"{k}_value" in pet:
                pt += f" | +{pet[f'{k}_value']}٪ {tfa[k]}"
        pt += ")"
    else: pt = "ندارد"
    if user.get("phoenix_owned"):
        text = f"🐾 {pt}\n\n⚠️ ققنوس داری. اسپین ممکن نیست."
        kb = InlineKeyboardBuilder(); kb.button("🔙", callback_data=f"{prefix}back")
        await callback.message.edit_text(text, reply_markup=kb.as_markup()); return
    text = f"🐾 {pt}\n\n🥚 **تخم‌ها:**\n"
    for k, e in PET_EGGS.items(): text += f"• {e['name']}: {e['price']:,}\n"
    text += "\n⚠️ اسپین پت قبلی رو نابود می‌کنه!"
    kb = InlineKeyboardBuilder()
    for k in PET_EGGS:
        s = {"common":"معمولی","uncommon":"غیرمعمولی","rare":"کمیاب","epic":"حماسی","legendary":"افسانه‌ای","mythic":"اساطیری"}[k]
        kb.button(s, callback_data=f"{prefix}spin_{k}")
    kb.button("🔙", callback_data=f"{prefix}back"); kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def do_spin(callback, user, uid, et):
    if user.get("phoenix_owned"): await callback.message.edit_text("🦅 ققنوس داری!", reply_markup=get_keyboard(uid)); return
    if et not in PET_EGGS: return
    e = PET_EGGS[et]
    if user["coins"] < e["price"]: await callback.message.edit_text(f"❌ {e['price']:,}", reply_markup=get_keyboard(uid)); return
    np = spin_egg(et)
    if not np: return
    nc = user["coins"] - e["price"]
    update_user(uid, {"coins": nc, "pet": np})
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
    await callback.message.edit_text(f"🥚\n{np['emoji']} **{np['name']}**\n+{np['value']}٪ {tfa[np['type']]}\n💰 {nc:,}", reply_markup=get_keyboard(uid))

async def show_clan_menu(callback, user, uid):
    prefix = f"owner_{uid}_"
    if not user.get("clan_id"):
        text = f"🏰 **بدون کلن**\n\nساخت: {CLAN_CREATE_COST:,}"
        kb = InlineKeyboardBuilder()
        kb.button("🏰 ساخت", callback_data=f"{prefix}clan_create")
        kb.button("🔙", callback_data=f"{prefix}back")
        kb.adjust(1)
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
    else: await show_clan_info(callback, user, uid)

async def show_clan_info(callback, user, uid):
    c = get_clan(user["clan_id"])
    prefix = f"owner_{uid}_"
    if not c: await callback.message.edit_text("❌", reply_markup=get_keyboard(uid)); return
    il = c["leader_id"] == str(uid)
    text = f"🏰 **{c['name']}**\nلول: {c['level']} | +{c['level']*CLAN_BONUS_PER_LEVEL}٪\nخزانه: {c['treasury']:,}\nاعضا: {len(c['members'])}/{CLAN_MAX_MEMBERS.get(c['level'],10)}\nلیدر: {c['leader_name']}\n\n👥\n"
    for m in c["members"][:20]: text += f"• {c['member_names'].get(m, '?')}\n"
    kb = InlineKeyboardBuilder()
    kb.button("👤", callback_data=f"{prefix}clan_invite")
    kb.button("💰", callback_data=f"{prefix}clan_donate")
    kb.button("✉️", callback_data=f"{prefix}clan_chat")
    if il:
        kb.button("⬆️", callback_data=f"{prefix}clan_upgrade")
        kb.button("🗑", callback_data=f"{prefix}clan_disband")
    else: kb.button("🚪", callback_data=f"{prefix}clan_leave")
    kb.button("🔙", callback_data=f"{prefix}back"); kb.adjust(2)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def start_clan_create(callback, user, uid, state):
    if user["coins"] < CLAN_CREATE_COST: await callback.message.edit_text(f"❌ {CLAN_CREATE_COST:,}", reply_markup=get_keyboard(uid)); return
    await state.set_state(UserForm.clan_name)
    await callback.message.edit_text("🏰 نام کلن:")

async def upgrade_clan(callback, user, uid):
    c = get_clan(user["clan_id"])
    if not c or c["level"] >= 10: return
    nx = c["level"] + 1; cost = CLAN_LEVEL_COSTS[nx]
    if c["treasury"] < cost: await callback.message.edit_text(f"❌ {cost:,}", reply_markup=get_keyboard(uid)); return
    data = load_data()
    data["clans"][user["clan_id"]]["level"] = nx
    data["clans"][user["clan_id"]]["treasury"] -= cost
    save_data(data)
    await callback.message.edit_text(f"✅ لول {nx}!", reply_markup=get_keyboard(uid))

async def leave_clan(callback, user, uid):
    c = get_clan(user["clan_id"])
    if not c: return
    if c["leader_id"] == str(uid): await callback.message.edit_text("❌ لیدر منحل کن.", reply_markup=get_keyboard(uid)); return
    data = load_data()
    data["clans"][user["clan_id"]]["members"].remove(str(uid))
    data["clans"][user["clan_id"]]["member_names"].pop(str(uid), None)
    save_data(data); update_user(uid, {"clan_id": None})
    await callback.message.edit_text("🚪", reply_markup=get_keyboard(uid))

async def disband_clan(callback, user, uid):
    c = get_clan(user["clan_id"])
    if not c or c["leader_id"] != str(uid): return
    data = load_data()
    for m in c["members"]: update_user(int(m), {"clan_id": None})
    del data["clans"][user["clan_id"]]; save_data(data)
    await callback.message.edit_text("🗑 منحل شد", reply_markup=get_keyboard(uid))

async def show_league_menu(callback, user, uid):
    pn = user.get("current_period", 1); lg = LEAGUE_FA.get(user.get("prestige", 0), "?")
    profit = user["coins"] - user.get("period_start_coins", 1)
    rank = get_user_league_rank(uid, user)
    prefix = f"owner_{uid}_"
    text = f"🏅 **لیگ {lg}** — دوره {pn}\n💵 سود: {profit:,}\n📊 رتبه: {rank}\n\n🏆 ۱۰٪ برتر افتخار!"
    kb = InlineKeyboardBuilder()
    kb.button("🎖️ افتخارات", callback_data=f"{prefix}achievements")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def show_achievements(callback, user, uid):
    a = user.get("achievements", [])
    if not a: text = "🎖️ خالی!"
    else:
        text = f"🎖️ **افتخارات ({len(a)})**\n\n"
        for x in a[-20:]:
            ln = LEAGUE_FA.get(x.get("league", 0), "?")
            t = x.get("type")
            if t == "top_percent": text += f"🏅 {x['percent']}٪ برتر دوره {x['period']}، لیگ {ln}\n"
            elif t == "lone_eagle": text += f"🦅 عقاب تنهای {x['rank']} دوره {x['period']}، لیگ {ln}\n"
            elif t == "medal_gold": text += f"🥇 طلای دوره {x['period']}، لیگ {ln}\n"
            elif t == "medal_silver": text += f"🥈 نقره دوره {x['period']}، لیگ {ln}\n"
            elif t == "medal_bronze": text += f"🥉 برنز دوره {x['period']}، لیگ {ln}\n"
    await callback.message.edit_text(text, reply_markup=get_keyboard(uid))

# ==================== MAIN ====================
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print(f"🤖 Bot started... Admin ID: {ADMIN_ID}")
    async def stop_delay():
        await asyncio.sleep(340 * 60)
        print("⏰ Stopping...")
        try: await dp.stop_polling()
        except: pass
    asyncio.create_task(stop_delay())
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Stopped: {e}")

if __name__ == "__main__":
    asyncio.run(main())
