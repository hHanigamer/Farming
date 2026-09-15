import json
import os
import random
import shutil
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from filelock import FileLock

from baleio import Bot, Dispatcher, md
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.filters import Command, CommandStart
from baleio.fsm import FSMContext, State, StatesGroup
from baleio.types import Message, CallbackQuery
from baleio.utils import InlineKeyboardBuilder

# ==================== تنظیمات ====================
TOKEN = os.getenv("BOT_TOKEN", "1527610539:q0H8Sf3QGfo6fAUwj1E5_H7SDET6tgjBboE
")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "WALLET-TEST-1111111111111111")
DATA_FILE = "data.json"
BACKUP_FILE = "data_backup.json"
LOCK_FILE = "data.lock"
lock = FileLock(LOCK_FILE, timeout=10)

# ==================== میوه‌ها ====================
FRUITS = ["توت‌فرنگی", "گوجه", "سیب", "پرتقال", "نارگیل", "آناناس", "میوه اژدها"]
PRICES = [(1, 3), (15, 38), (304, 760), (9120, 22800),
          (456000, 1140000), (27360000, 68400000), (2052000000, 5130000000)]
GROWTH_TIMES = [1, 2.5, 4, 5.5, 7, 8.5, 10]

# ==================== XP و لول ====================
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

PRESTIGE_PRICES = {1: 50_000_000_000, 2: 100_000_000_000, 3: 200_000_000_000,
                   4: 500_000_000_000, 5: 725_000_000_000, 6: 1_000_000_000_000,
                   7: 1_500_000_000_000, 8: 2_500_000_000_000,
                   9: 5_000_000_000_000, 10: 10_000_000_000_000}

SHOP_PRICES = {
    4: {5000: 114000, 10000: 228000, 20000: 456000, 50000: 1140000, 100000: 2280000},
    5: {5000: 5700000, 10000: 11400000, 20000: 22800000, 50000: 57000000, 100000: 114000000},
    6: {5000: 342000000, 10000: 684000000, 20000: 1368000000, 50000: 3420000000, 100000: 6840000000},
    7: {5000: 25650000000, 10000: 51300000000, 20000: 102600000000, 50000: 256500000000, 100000: 513000000000},
}

SEASON_CYCLE = ["spring", "summer", "autumn", "winter"]
SEASON_DURATION_MIN = 45
SEASON_FA = {"spring": "🌸 بهار", "summer": "☀️ تابستان", "autumn": "🍂 پاییز", "winter": "❄️ زمستان"}

# ==================== تخم‌های پت ====================
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

# ==================== کلن ====================
CLAN_CREATE_COST = 500000
CLAN_LEVEL_COSTS = {1: 0, 2: 1000000, 3: 5000000, 4: 25000000, 5: 100000000,
                    6: 500000000, 7: 2500000000, 8: 10000000000,
                    9: 50000000000, 10: 250000000000}
CLAN_MAX_MEMBERS = {1: 10, 2: 10, 3: 15, 4: 15, 5: 20, 6: 25, 7: 30, 8: 40, 9: 45, 10: 50}
CLAN_BONUS_PER_LEVEL = 2  # درصد سود اضافه به ازای هر لول

LEAGUE_FA = {0: "I", 1: "II", 2: "III", 3: "IV", 4: "V", 5: "VI",
             6: "VII", 7: "VIII", 8: "IX", 9: "X", 10: "XI"}

# ==================== FSM ====================
class UserForm(StatesGroup):
    name = State()
    gift_target = State()
    gift_amount = State()
    clan_name = State()
    clan_invite = State()
    clan_donate = State()
    clan_chat = State()

# ==================== دیتابیس ====================
def create_default_data():
    return {
        "game_start_time": datetime.now().isoformat(),
        "users": {},
        "leaderboard": [],
        "clans": {},
        "leagues": {},
    }

def create_default_user(user_id):
    now = datetime.now().isoformat()
    return {
        "name": "", "level": 1, "xp": 0, "coins": 1,
        "state": "idle", "current_fruit": 0, "inventory": [],
        "upgrades": {"auto_water": 0, "golden_pot": 0, "professional_seeder": 0},
        "worker": {"level": 1, "active": False},
        "daily_orders": {"date": "", "orders": [], "completed": False},
        "prestige": 0, "prestige_multiplier": 1.0,
        "gifts_given": 0, "gifts_received": 0,
        "referral_code": f"REF{user_id}{random.randint(100,999)}",
        "pet": None,
        "clan_id": None,
        "period_start_coins": 1,
        "period_start_time": now,
        "current_period": 1,
        "last_seen_period": 1,
        "achievements": [],
    }

def _ensure_keys(data):
    if not isinstance(data, dict):
        return create_default_data()
    defaults = create_default_data()
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    return data

def load_data():
    with lock:
        if not os.path.exists(DATA_FILE):
            if os.path.exists(BACKUP_FILE):
                try: shutil.copy(BACKUP_FILE, DATA_FILE)
                except: pass
            else:
                default = create_default_data()
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(default, f, ensure_ascii=False, indent=2)
                return default
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _ensure_keys(data)
        except Exception:
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return _ensure_keys(data)
                except: pass
            default = create_default_data()
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default

def save_data(data):
    with lock:
        data = _ensure_keys(data)
        temp_file = DATA_FILE + ".tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            return False
        if os.path.exists(DATA_FILE):
            try: shutil.copy(DATA_FILE, BACKUP_FILE)
            except: pass
        try:
            os.replace(temp_file, DATA_FILE)
            return True
        except Exception:
            if os.path.exists(BACKUP_FILE):
                shutil.copy(BACKUP_FILE, DATA_FILE)
            return False

def get_user(user_id):
    data = load_data()
    return data["users"].get(str(user_id))

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
        if u.get("name", "").lower() == q:
            return uid, u
        if u.get("referral_code", "").lower() == q:
            return uid, u
    return None, None

# ==================== فصل ====================
def get_current_season():
    data = load_data()
    start_str = data.get("game_start_time")
    if not start_str:
        data["game_start_time"] = datetime.now().isoformat()
        save_data(data)
        return "spring"
    start = datetime.fromisoformat(start_str)
    elapsed = (datetime.now() - start).total_seconds() / 60
    idx = int(elapsed // SEASON_DURATION_MIN) % len(SEASON_CYCLE)
    return SEASON_CYCLE[idx]

def get_season_effects():
    season = get_current_season()
    e = {"growth_mult": 1.0, "sell_mult": 1.0, "buy_mult": 1.0, "golden_chance": 0.02}
    if season == "spring":
        e["growth_mult"] = 1 / 1.2
    elif season == "summer":
        e["golden_chance"] = 0.02 * 1.75
    elif season == "autumn":
        e["sell_mult"] = random.uniform(1.25, 1.5)
    elif season == "winter":
        e["buy_mult"] = 1 / 1.2
    return e, season

# ==================== پت ====================
def get_pet_effect(user, effect_type):
    """بازگرداندن مقدار قابلیت پت بر اساس نوع"""
    pet = user.get("pet")
    if not pet:
        return 0
    if pet.get("type") == effect_type:
        return pet.get("value", 0)
    return 0

def spin_egg(egg_type):
    """اسپین تخم و برگرداندن پت تصادفی"""
    if egg_type not in PET_EGGS:
        return None
    pets = PET_EGGS[egg_type]["pets"]
    r = random.randint(1, 100)
    cumulative = 0
    for p in pets:
        cumulative += p["chance"]
        if r <= cumulative:
            return p
    return pets[-1]

# ==================== کلن ====================
def get_clan(clan_id):
    data = load_data()
    return data["clans"].get(clan_id)

def create_clan(clan_id, name, leader_id, leader_name):
    data = load_data()
    if clan_id in data["clans"]:
        return False
    data["clans"][clan_id] = {
        "name": name,
        "leader_id": leader_id,
        "leader_name": leader_name,
        "level": 1,
        "treasury": 0,
        "members": [leader_id],
        "member_names": {leader_id: leader_name},
        "created_at": datetime.now().isoformat(),
    }
    save_data(data)
    return True

def get_clan_bonus(user):
    """پاداش سود کلن بر اساس لول"""
    if not user.get("clan_id"):
        return 0
    clan = get_clan(user["clan_id"])
    if not clan:
        return 0
    return clan["level"] * CLAN_BONUS_PER_LEVEL

# ==================== لیگ و دوره ====================
def get_week_number(start_time_str, now=None):
    """محاسبه شماره هفته (دوره) از زمان شروع بازی"""
    start = datetime.fromisoformat(start_time_str)
    if now is None:
        now = datetime.now()
    elapsed = (now - start).total_seconds() / (7 * 24 * 3600)
    return int(elapsed) + 1

def get_period_number():
    """شماره دوره فعلی گلوبال"""
    data = load_data()
    start_str = data.get("game_start_time")
    if not start_str:
        return 1
    return get_week_number(start_str)

def check_period_reset(user_id):
    """بررسی ریست دوره و به‌روزرسانی کاربر"""
    data = load_data()
    current_period = get_period_number()
    user = data["users"].get(str(user_id))
    if not user:
        return False
    
    last_period = user.get("last_seen_period", current_period)
    if current_period > last_period:
        # پایان دوره(های) قبلی: پردازش جایزه‌ها
        for p in range(last_period, current_period):
            process_period_end(p, user)
        
        # شروع دوره جدید برای این کاربر
        user["period_start_coins"] = user["coins"]
        user["period_start_time"] = datetime.now().isoformat()
        user["current_period"] = current_period
        user["last_seen_period"] = current_period
        data["users"][str(user_id)] = user
        save_data(data)
        return True
    return False

def process_period_end(period_num, user):
    """پردازش پایان یه دوره و اعطای جایزه به این کاربر (اگر واجد شرایط باشه)"""
    # چک کردن لیگ
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0:
        return  # لیگ باز نشده
    
    prestige = user.get("prestige", 0)
    league_key = str(prestige)
    
    data = load_data()
    leagues = data.get("leagues", {})
    period_key = f"period_{period_num}"
    
    if league_key not in leagues:
        return
    if period_key not in leagues[league_key]:
        return
    
    league_data = leagues[league_key][period_key]
    members = league_data.get("members", {})
    user_id_str = None
    
    # پیدا کردن user_id
    for uid, u in data["users"].items():
        if u is user or u.get("name") == user.get("name"):
            user_id_str = uid
            break
    
    if not user_id_str or user_id_str not in members:
        return
    
    total = len(members)
    if total == 0:
        return
    
    # مرتب‌سازی بر اساس profit
    sorted_members = sorted(members.items(), key=lambda x: x[1].get("profit", 0), reverse=True)
    
    if total < 10:
        # مدال عقاب تنها
        rank = next((i+1 for i, (uid, _) in enumerate(sorted_members) if uid == user_id_str), 0)
        if rank > 0:
            ach = {
                "type": "lone_eagle",
                "rank": rank,
                "period": period_num,
                "league": prestige,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
            if "achievements" not in user:
                user["achievements"] = []
            user["achievements"].append(ach)
    else:
        # ۱۰٪ برتر
        rank = next((i+1 for i, (uid, _) in enumerate(sorted_members) if uid == user_id_str), 0)
        if rank == 0:
            return
        percent = int((rank / total) * 100)
        # اگه درصد رتبه کمتر یا مساوی ۱۰ بود، جایزه می‌گیره
        # مثلاً رتبه 1 از 100 → 1%، رتبه 5 از 50 → 10%
        if percent <= 10:
            if percent < 1:
                percent = 1
            ach = {
                "type": "top_percent",
                "percent": percent,
                "period": period_num,
                "league": prestige,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
            if "achievements" not in user:
                user["achievements"] = []
            user["achievements"].append(ach)

def update_league_profit(user_id, user, profit):
    """ثبت سود کاربر توی لیگ دوره فعلی"""
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0:
        return
    
    prestige = user.get("prestige", 0)
    league_key = str(prestige)
    period_num = user.get("current_period", 1)
    period_key = f"period_{period_num}"
    
    data = load_data()
    if "leagues" not in data:
        data["leagues"] = {}
    if league_key not in data["leagues"]:
        data["leagues"][league_key] = {}
    if period_key not in data["leagues"][league_key]:
        data["leagues"][league_key][period_key] = {
            "started_at": user.get("period_start_time"),
            "members": {}
        }
    
    data["leagues"][league_key][period_key]["members"][str(user_id)] = {
        "name": user.get("name", "?"),
        "profit": profit,
    }
    save_data(data)

# ==================== توابع کمکی ====================
def get_available_fruits(user):
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["fruits"]

def get_available_features(user):
    feats = list(LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["features"])
    # اگه پرستیژ بالای ۰ داره، لیگ از اول بازه
    if user.get("prestige", 0) > 0 and "league" not in feats:
        feats.append("league")
    return feats

def has_feature(user, feature):
    return feature in get_available_features(user)

def xp_needed_for(level):
    return XP_REQUIRED.get(level, 999999)

def xp_from_sale(fruit_name):
    return random.randint(*XP_FROM_SALES[fruit_name]) if fruit_name in XP_FROM_SALES else 0

# ==================== کیبورد ====================
def get_keyboard(user_id):
    user = get_user(user_id)
    if not user:
        return InlineKeyboardBuilder().as_markup()
    
    cf = user["current_fruit"]
    if cf not in get_available_fruits(user):
        cf = get_available_fruits(user)[0]
        update_user(user_id, {"current_fruit": cf})
    
    fruit = FRUITS[cf]
    kb = InlineKeyboardBuilder()
    
    if user["state"] == "growing":
        kb.button("⏳ در حال رشد...", callback_data="noop")
        kb.button("⏳ هنوز نرسیده!", callback_data="noop")
    elif user["state"] == "harvested":
        kb.button("🌱 بذر قبلاً کاشته شده", callback_data="noop")
        kb.button(f"💰 فروش {fruit}", callback_data="sell")
    else:
        kb.button(f"🌱 خرید بذر {fruit}", callback_data="buy")
        kb.button(f"💰 فروش {fruit}", callback_data="sell")
    
    kb.adjust(2)
    
    available = get_available_fruits(user)
    if len(available) > 1:
        for i in available:
            mark = "✅ " if i == cf else ""
            kb.button(f"{mark}{FRUITS[i]}", callback_data=f"switch_{i}")
        kb.adjust(3)
    
    kb.button("📊 وضعیت", callback_data="status")
    
    if has_feature(user, "pet"):
        kb.button("🐾 پت", callback_data="pet_menu")
    if has_feature(user, "leaderboard"):
        kb.button("🏆 لیدربرد", callback_data="leaderboard")
    if has_feature(user, "upgrades"):
        kb.button("🔧 ارتقاء ابزار", callback_data="upgrades")
    if has_feature(user, "daily_orders"):
        kb.button("📦 سفارشات روزانه", callback_data="daily_orders")
    if has_feature(user, "shop"):
        kb.button("🛒 فروشگاه سکه", callback_data="shop")
    if has_feature(user, "worker"):
        kb.button("👷 کارگر", callback_data="worker_menu")
    if has_feature(user, "clan"):
        kb.button("🏰 کلن", callback_data="clan_menu")
    if has_feature(user, "gift"):
        kb.button("🎁 هدیه دادن", callback_data="gift")
    if has_feature(user, "league"):
        kb.button("🏅 لیگ", callback_data="league_menu")
        kb.button("🎖️ افتخارات", callback_data="achievements")
    if has_feature(user, "prestige") and user["level"] >= 7:
        kb.button("⭐ پرستیژ", callback_data="prestige_menu")
    
    kb.adjust(2)
    return kb.as_markup()

# ==================== متن وضعیت ====================
def build_status_text(user, user_id):
    effects, season = get_season_effects()
    multiplier = user["prestige_multiplier"]
    
    pet = user.get("pet")
    pet_text = f"{pet['emoji']} {pet['name']}" if pet else "ندارد"
    
    clan_text = "بدون کلن"
    clan_bonus = 0
    if user.get("clan_id"):
        clan = get_clan(user["clan_id"])
        if clan:
            clan_text = f"🏰 {clan['name']} (لول {clan['level']})"
            clan_bonus = clan["level"] * CLAN_BONUS_PER_LEVEL
    
    profit = user["coins"] - user.get("period_start_coins", user["coins"])
    period_num = user.get("current_period", 1)
    
    league_rank = "—"
    if user.get("level", 1) >= 7 or user.get("prestige", 0) > 0:
        league_rank = get_user_league_rank(user_id, user)
    
    text = (
        f"📊 **وضعیت {user['name']}:**\n"
        f"💰 سکه: {user['coins']:,}\n"
        f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
        f"⭐ پرستیژ: {user['prestige']} | ضریب: {multiplier:.2f}x\n"
        f"🌤 فصل: {SEASON_FA[season]}\n"
        f"🐾 پت: {pet_text}\n"
        f"{clan_text}\n"
        f"💵 سود دوره {period_num}: {profit:,}\n"
        f"🏅 رتبه لیگ: {league_rank}\n"
        f"🌱 میوه فعلی: {FRUITS[user['current_fruit']]}\n"
        f"⏳ وضعیت: {user['state']}\n"
        f"🎁 هدیه: داده {user.get('gifts_given',0)} | گرفته {user.get('gifts_received',0)}\n"
        f"👷 کارگر: لول {user['worker']['level']} ({'فعال' if user['worker']['active'] else 'غیرفعال'})\n"
        f"🎖️ افتخارات: {len(user.get('achievements', []))}\n\n"
        f"🍎 **قیمت میوه‌های قابل‌دسترس:**\n"
    )
    
    for i in get_available_fruits(user):
        bp = int(PRICES[i][0] * multiplier * effects["buy_mult"])
        sp = int(PRICES[i][1] * multiplier * effects["sell_mult"])
        mark = "✅ " if i == user["current_fruit"] else ""
        text += f"{mark}{FRUITS[i]}: خرید {bp:,} | فروش {sp:,}\n"
    
    return text

def get_user_league_rank(user_id, user):
    """محاسبه رتبه کاربر در لیگ دوره فعلی"""
    prestige = user.get("prestige", 0)
    league_key = str(prestige)
    period_num = user.get("current_period", 1)
    period_key = f"period_{period_num}"
    
    data = load_data()
    leagues = data.get("leagues", {})
    if league_key not in leagues or period_key not in leagues[league_key]:
        return "—"
    
    members = leagues[league_key][period_key].get("members", {})
    if str(user_id) not in members:
        return "—"
    
    sorted_members = sorted(members.items(), key=lambda x: x[1].get("profit", 0), reverse=True)
    for i, (uid, _) in enumerate(sorted_members, 1):
        if uid == str(user_id):
            return f"#{i} از {len(members)}"
    return "—"

# ==================== راه‌اندازی ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# ==================== هندلرها ====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or user.get("name", "") == "":
        await state.set_state(UserForm.name)
        await message.answer("👤 لطفاً یک نام برای خود انتخاب کن (حداقل ۳ کاراکتر، بدون فاصله، تکراری نباشد):")
        return
    # بررسی ریست دوره
    check_period_reset(user_id)
    await show_main_menu(message)

@dp.message(Command("status"))
async def cmd_status(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user: return
    check_period_reset(user_id)
    user = get_user(user_id)
    await message.answer(build_status_text(user, user_id), reply_markup=get_keyboard(user_id))

@dp.message(Command("gift"))
async def cmd_gift(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not has_feature(user, "gift"):
        await message.answer("🔒 این ویژگی در لول ۶ باز می‌شود.")
        return
    await state.set_state(UserForm.gift_target)
    await message.answer("🎁 نام یا کد معرف کاربر مقصد را وارد کن:")

@dp.message(UserForm.name)
async def process_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    if len(name) < 3 or " " in name:
        await message.answer("❌ نام باید حداقل ۳ حرف و بدون فاصله باشد. دوباره تلاش کن:")
        return
    data = load_data()
    for uid, u in data["users"].items():
        if u.get("name", "").lower() == name.lower():
            await message.answer("❌ این نام قبلاً ثبت شده. نام دیگری انتخاب کن:")
            return
    update_user(user_id, {"name": name})
    await state.clear()
    await message.answer(f"✅ نام '{name}' ثبت شد! خوش آمدی.")
    await show_main_menu(message)

@dp.message(UserForm.gift_target)
async def process_gift_target(message: Message, state: FSMContext):
    await state.update_data(gift_target=message.text.strip())
    await state.set_state(UserForm.gift_amount)
    await message.answer("💰 مقدار سکه‌ای که می‌خواهی هدیه دهی را وارد کن:")

@dp.message(UserForm.gift_amount)
async def process_gift_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user: return
    try:
        amount = int(message.text.strip())
        if amount <= 0: raise ValueError
    except:
        await message.answer("❌ لطفاً یک عدد مثبت وارد کن.")
        return
    data = await state.get_data()
    target_q = data.get("gift_target")
    await state.clear()
    if user["coins"] < amount:
        await message.answer(f"❌ سکه کافی نیست. موجودی: {user['coins']:,}")
        return
    tid, target = find_user_by_name_or_code(target_q)
    if not tid or tid == str(user_id):
        await message.answer("❌ کاربر پیدا نشد یا نمی‌توانی به خودت هدیه دهی.")
        return
    update_user(user_id, {"coins": user["coins"] - amount,
                           "gifts_given": user.get("gifts_given", 0) + 1})
    update_user(int(tid), {"coins": target["coins"] + amount,
                            "gifts_received": target.get("gifts_received", 0) + 1})
    update_leaderboard(user_id, user["name"], user["coins"] - amount, user["level"], user["prestige"])
    update_leaderboard(int(tid), target["name"], target["coins"] + amount, target["level"], target["prestige"])
    await message.answer(f"✅ {amount:,} سکه به {target['name']} هدیه دادی!")

# ---------- کلن ----------
@dp.message(UserForm.clan_name)
async def process_clan_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user: return
    name = message.text.strip()
    if len(name) < 3 or len(name) > 20 or " " in name:
        await message.answer("❌ نام کلن باید ۳ تا ۲۰ کاراکتر و بدون فاصله باشد:")
        return
    data = load_data()
    for cid, c in data.get("clans", {}).items():
        if c.get("name", "").lower() == name.lower():
            await message.answer("❌ این نام کلن قبلاً ثبت شده:")
            return
    if user["coins"] < CLAN_CREATE_COST:
        await message.answer(f"❌ نیاز به {CLAN_CREATE_COST:,} سکه برای ساخت کلن.")
        await state.clear()
        return
    clan_id = f"clan_{user_id}"
    create_clan(clan_id, name, str(user_id), user["name"])
    update_user(user_id, {"clan_id": clan_id, "coins": user["coins"] - CLAN_CREATE_COST})
    await state.clear()
    await message.answer(f"🏰 کلن «{name}» ساخته شد!", reply_markup=get_keyboard(user_id))

@dp.message(UserForm.clan_invite)
async def process_clan_invite(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user.get("clan_id"): 
        await state.clear(); return
    target_q = message.text.strip()
    tid, target = find_user_by_name_or_code(target_q)
    if not tid:
        await message.answer("❌ کاربر پیدا نشد.")
        return
    if target.get("clan_id"):
        await message.answer("❌ این کاربر در کلن دیگری است.")
        return
    data = load_data()
    clan = data["clans"].get(user["clan_id"])
    if not clan:
        await state.clear(); return
    if len(clan["members"]) >= CLAN_MAX_MEMBERS.get(clan["level"], 10):
        await message.answer("❌ کلن پر است!")
        return
    # دعوت = اضافه کردن مستقیم (ساده)
    clan["members"].append(str(tid))
    clan["member_names"][str(tid)] = target["name"]
    save_data(data)
    update_user(int(tid), {"clan_id": user["clan_id"]})
    await state.clear()
    await message.answer(f"✅ {target['name']} به کلن اضافه شد.")

@dp.message(UserForm.clan_donate)
async def process_clan_donate(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user.get("clan_id"):
        await state.clear(); return
    try:
        amount = int(message.text.strip())
        if amount < 10000: raise ValueError
    except:
        await message.answer("❌ حداقل ۱۰,۰۰۰ سکه.")
        return
    if user["coins"] < amount:
        await message.answer("❌ سکه کافی نیست.")
        return
    data = load_data()
    clan = data["clans"].get(user["clan_id"])
    if not clan: 
        await state.clear(); return
    clan["treasury"] += amount
    save_data(data)
    update_user(user_id, {"coins": user["coins"] - amount})
    await state.clear()
    await message.answer(f"✅ {amount:,} سکه به خزانه اهدا شد.")

@dp.message(UserForm.clan_chat)
async def process_clan_chat(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user or not user.get("clan_id"):
        await state.clear(); return
    clan = get_clan(user["clan_id"])
    if not clan: 
        await state.clear(); return
    msg = f"🏰 **پیام کلن از {user['name']}:**\n\n{message.text}"
    for m in clan["members"]:
        try:
            await bot.send_message(int(m), msg)
        except Exception:
            pass
    await state.clear()

async def show_main_menu(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user: return
    _, season = get_season_effects()
    p = f"⭐ پرستیژ {user['prestige']}" if user['prestige'] > 0 else "بدون پرستیژ"
    text = (
        f"🌾 **مزرعه‌ی {user['name']}**\n\n"
        f"🌤 فصل: {SEASON_FA[season]}\n"
        f"💰 سکه: {user['coins']:,}\n"
        f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
        f"⭐ {p}\n"
        f"🍓 میوه: {FRUITS[user['current_fruit']]}\n"
    )
    await message.answer(text, reply_markup=get_keyboard(user_id))

# ==================== کال‌بک‌ها ====================
@dp.callback_query()
async def on_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = callback.data
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user: return
    
    # بررسی ریست دوره
    check_period_reset(user_id)
    user = get_user(user_id)
    if not user: return
    
    handlers = {
        "noop": None,
        "status": lambda: edit_status(callback, user, user_id),
        "buy": lambda: buy_seed(callback, user, user_id, bot),
        "sell": lambda: sell_fruit(callback, user, user_id),
        "leaderboard": lambda: show_leaderboard(callback, user, user_id),
        "upgrades": lambda: show_upgrades(callback, user, user_id),
        "daily_orders": lambda: show_daily_orders(callback, user, user_id),
        "complete_orders": lambda: complete_orders(callback, user, user_id),
        "shop": lambda: show_shop(callback, user, user_id),
        "worker_menu": lambda: show_worker(callback, user, user_id),
        "worker_toggle": lambda: toggle_worker(callback, user, user_id),
        "worker_upgrade": lambda: upgrade_worker(callback, user, user_id),
        "gift": lambda: start_gift(callback, user, user_id, state),
        "prestige_menu": lambda: show_prestige(callback, user, user_id),
        "buy_prestige": lambda: buy_prestige(callback, user, user_id),
        "pet_menu": lambda: show_pet_menu(callback, user, user_id),
        "clan_menu": lambda: show_clan_menu(callback, user, user_id),
        "league_menu": lambda: show_league_menu(callback, user, user_id),
        "achievements": lambda: show_achievements(callback, user, user_id),
        "back": lambda: back_to_menu(callback, user_id),
    }
    
    if data in handlers:
        if handlers[data]:
            await handlers[data]()
        return
    if data.startswith("switch_"):
        await switch_fruit(callback, user, user_id, int(data.split("_")[1]))
    elif data.startswith("upgrade_"):
        await buy_upgrade(callback, user, user_id, data.replace("upgrade_", ""))
    elif data.startswith("shop_"):
        await buy_shop(callback, user, user_id, int(data.split("_")[1]))
    elif data.startswith("spin_"):
        await do_spin(callback, user, user_id, data.replace("spin_", ""))
    elif data == "clan_create":
        await start_clan_create(callback, user, user_id, state)
    elif data == "clan_info":
        await show_clan_info(callback, user, user_id)
    elif data == "clan_invite":
        await state.set_state(UserForm.clan_invite)
        await callback.message.edit_text("👤 نام یا کد کاربر را وارد کن:", reply_markup=get_keyboard(user_id))
    elif data == "clan_donate":
        await state.set_state(UserForm.clan_donate)
        await callback.message.edit_text("💰 مقدار سکه برای اهدا (حداقل ۱۰,۰۰۰):", reply_markup=get_keyboard(user_id))
    elif data == "clan_chat":
        await state.set_state(UserForm.clan_chat)
        await callback.message.edit_text("✉️ پیام خود را برای همه اعضا بنویس:", reply_markup=get_keyboard(user_id))
    elif data == "clan_upgrade":
        await upgrade_clan(callback, user, user_id)
    elif data == "clan_leave":
        await leave_clan(callback, user, user_id)
    elif data == "clan_disband":
        await disband_clan(callback, user, user_id)

async def back_to_menu(callback, user_id):
    user = get_user(user_id)
    await callback.message.edit_text("🔙 منوی اصلی", reply_markup=get_keyboard(user_id))

async def edit_status(callback, user, user_id):
    await callback.message.edit_text(build_status_text(user, user_id), reply_markup=get_keyboard(user_id))

async def switch_fruit(callback, user, user_id, idx):
    if idx not in get_available_fruits(user):
        await callback.message.edit_text("🔒 قفل است!", reply_markup=get_keyboard(user_id))
        return
    update_user(user_id, {"current_fruit": idx})
    await callback.message.edit_text(f"✅ میوه فعلی: {FRUITS[idx]}", reply_markup=get_keyboard(user_id))

async def buy_seed(callback, user, user_id, bot):
    cf = user["current_fruit"]
    effects, _ = get_season_effects()
    buy_price = int(PRICES[cf][0] * user["prestige_multiplier"] * effects["buy_mult"])
    
    if user["state"] == "growing":
        await callback.message.edit_text("⏳ صبر کن.", reply_markup=get_keyboard(user_id)); return
    if user["state"] == "harvested":
        await callback.message.edit_text("🌱 اول بفروش.", reply_markup=get_keyboard(user_id)); return
    if user["coins"] < buy_price:
        await callback.message.edit_text(f"❌ نیاز به {buy_price:,} سکه.", reply_markup=get_keyboard(user_id)); return
    
    growth_time = GROWTH_TIMES[cf] * effects["growth_mult"]
    if user["upgrades"].get("auto_water", 0) > 0:
        growth_time *= 0.8
    # قابلیت سرعت پت
    speed_bonus = get_pet_effect(user, "speed")
    if speed_bonus > 0:
        growth_time *= (1 - speed_bonus / 100)
    
    update_user(user_id, {"coins": user["coins"] - buy_price, "state": "growing"})
    await callback.message.edit_text(f"🌱 {FRUITS[cf]} کاشته شد! {growth_time:.1f} دقیقه دیگه می‌رسه.", reply_markup=get_keyboard(user_id))
    asyncio.create_task(grow_complete(user_id, callback.message.chat.id, growth_time, bot))

async def grow_complete(user_id, chat_id, minutes, bot):
    await asyncio.sleep(minutes * 60)
    user = get_user(user_id)
    if user and user["state"] == "growing":
        update_user(user_id, {"state": "harvested"})
        try:
            await bot.send_message(chat_id, f"🍓 {FRUITS[user['current_fruit']]} رسید!", reply_markup=get_keyboard(user_id))
        except: pass

async def sell_fruit(callback, user, user_id):
    if user["state"] != "harvested":
        await callback.message.edit_text("⏳ هنوز نرسیده!", reply_markup=get_keyboard(user_id)); return
    
    cf = user["current_fruit"]
    effects, _ = get_season_effects()
    base_sell = int(PRICES[cf][1] * user["prestige_multiplier"] * effects["sell_mult"])
    sell_price = base_sell
    
    # پت سود
    pet_sell_bonus = get_pet_effect(user, "sell")
    if pet_sell_bonus > 0:
        sell_price += int(base_sell * pet_sell_bonus / 100)
    
    # کلن سود
    clan_bonus = get_clan_bonus(user)
    if clan_bonus > 0:
        sell_price += int(base_sell * clan_bonus / 100)
    
    # گلدان طلایی
    if user["upgrades"].get("golden_pot", 0) > 0:
        sell_price = int(sell_price * (1 + 0.1 * user["upgrades"]["golden_pot"]))
    
    # طلایی
    golden = random.random() < effects["golden_chance"]
    if golden:
        sell_price *= 2
    
    fruit_name = FRUITS[cf]
    xp_gain = int(xp_from_sale(fruit_name) * user["prestige_multiplier"])
    pet_xp_bonus = get_pet_effect(user, "xp")
    if pet_xp_bonus > 0:
        xp_gain += int(xp_gain * pet_xp_bonus / 100)
    
    new_coins = user["coins"] + sell_price
    new_xp = user["xp"] + xp_gain
    new_level = user["level"]
    level_up_msg = ""
    xp_needed = xp_needed_for(new_level)
    while new_xp >= xp_needed and new_level < 7:
        new_xp -= xp_needed
        new_level += 1
        xp_needed = xp_needed_for(new_level)
        level_up_msg = f"\n🎉 **لول آپ! لول {new_level}!**"
    
    update_user(user_id, {"coins": new_coins, "xp": new_xp, "level": new_level, "state": "idle"})
    update_leaderboard(user_id, user["name"], new_coins, new_level, user["prestige"])
    
    # به‌روزرسانی لیگ
    updated_user = get_user(user_id)
    profit = updated_user["coins"] - updated_user.get("period_start_coins", updated_user["coins"])
    update_league_profit(user_id, updated_user, profit)
    
    golden_text = " ✨(طلایی!)" if golden else ""
    await callback.message.edit_text(
        f"✅ {fruit_name} فروخته شد{golden_text}\n"
        f"💵 قیمت پایه: {base_sell:,}\n"
        f"💰 دریافت نهایی: +{sell_price:,}\n"
        f"⭐ +{xp_gain} XP\n"
        f"📈 لول {new_level} (XP: {new_xp}/{xp_needed_for(new_level)}){level_up_msg}",
        reply_markup=get_keyboard(user_id))

# ---------- لیدربرد ----------
async def show_leaderboard(callback, user, user_id):
    data = load_data()
    lb = data["leaderboard"][:10]
    text = "🏆 **لیدربرد کلی:**\n\n"
    for i, item in enumerate(lb, 1):
        p = f"⭐{item['prestige']}" if item['prestige'] > 0 else ""
        text += f"{i}. {item['name']} {p} — لول {item['level']} | {item['coins']:,}\n"
    if not lb: text += "هنوز کسی نیست!"
    await callback.message.edit_text(text, reply_markup=get_keyboard(user_id))

# ---------- ارتقاء ----------
async def show_upgrades(callback, user, user_id):
    u = user["upgrades"]
    c1 = 1000 * (u.get("auto_water", 0) + 1)
    c2 = 2000 * (u.get("golden_pot", 0) + 1)
    c3 = 5000 * (u.get("professional_seeder", 0) + 1)
    text = (f"🔧 **ارتقاء ابزار:**\n\n"
            f"💧 آبیاری خودکار — {c1:,} (خرید: {u.get('auto_water',0)})\n"
            f"🏺 گلدان طلایی — {c2:,} (خرید: {u.get('golden_pot',0)})\n"
            f"🌱 بذرپاش — {c3:,} (خرید: {u.get('professional_seeder',0)})\n")
    kb = InlineKeyboardBuilder()
    kb.button(f"💧 ({c1:,})", callback_data="upgrade_auto_water")
    kb.button(f"🏺 ({c2:,})", callback_data="upgrade_golden_pot")
    kb.button(f"🌱 ({c3:,})", callback_data="upgrade_professional_seeder")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_upgrade(callback, user, user_id, key):
    base = {"auto_water": 1000, "golden_pot": 2000, "professional_seeder": 5000}
    if key not in base: return
    count = user["upgrades"].get(key, 0)
    cost = base[key] * (count + 1)
    if user["coins"] < cost:
        await callback.message.edit_text(f"❌ نیاز به {cost:,}", reply_markup=get_keyboard(user_id)); return
    u = user["upgrades"]; u[key] = count + 1
    update_user(user_id, {"coins": user["coins"] - cost, "upgrades": u})
    await callback.message.edit_text(f"✅ ارتقاء انجام شد!", reply_markup=get_keyboard(user_id))

# ---------- سفارشات ----------
async def show_daily_orders(callback, user, user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if user["daily_orders"]["date"] != today:
        orders = [{"fruit": FRUITS[random.randint(0, len(FRUITS)-2)], "count": random.randint(1, 3)} for _ in range(3)]
        update_user(user_id, {"daily_orders": {"date": today, "orders": orders, "completed": False}})
        user = get_user(user_id)
    orders = user["daily_orders"]["orders"]
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("📦 امروز تکمیل شده!", reply_markup=get_keyboard(user_id)); return
    text = "📦 **سفارشات:**\n\n"
    for i, o in enumerate(orders, 1):
        text += f"{i}. {o['count']} عدد {o['fruit']}\n"
    kb = InlineKeyboardBuilder()
    kb.button("✅ تکمیل", callback_data="complete_orders")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def complete_orders(callback, user, user_id):
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("قبلاً تکمیل شده!", reply_markup=get_keyboard(user_id)); return
    orders = user["daily_orders"]["orders"]
    inv = user.get("inventory", [])
    for o in orders:
        if inv.count(o["fruit"]) < o["count"]:
            await callback.message.edit_text(f"❌ کمبود {o['fruit']}", reply_markup=get_keyboard(user_id)); return
    for o in orders:
        for _ in range(o["count"]): inv.remove(o["fruit"])
    bonus = int(sum(PRICES[FRUITS.index(o["fruit"])][1] * o["count"] * 1.5 for o in orders) * user["prestige_multiplier"])
    new_coins = user["coins"] + bonus
    update_user(user_id, {"coins": new_coins, "inventory": inv,
                           "daily_orders": {**user["daily_orders"], "completed": True}})
    update_leaderboard(user_id, user["name"], new_coins, user["level"], user["prestige"])
    await callback.message.edit_text(f"✅ +{bonus:,} سکه", reply_markup=get_keyboard(user_id))

# ---------- فروشگاه ----------
async def show_shop(callback, user, user_id):
    level = user["level"]
    if level < 4:
        await callback.message.edit_text("🔒 فروشگاه در لول ۴ باز می‌شود.", reply_markup=get_keyboard(user_id)); return
    prices = SHOP_PRICES.get(level, SHOP_PRICES[7])
    text = "🛒 **فروشگاه سکه**\n\n💰 با توجه به لول شما، مقدار سکه‌ها متفاوت است.\n\n"
    for amt, c in prices.items():
        text += f"• {amt:,} تومان → {c:,} سکه"
        if amt == 50000: text += " + بذر معمولی"
        elif amt == 100000: text += " + بذر طلایی ✨"
        text += "\n"
    kb = InlineKeyboardBuilder()
    kb.button("۵,۰۰۰", callback_data="shop_5000")
    kb.button("۱۰,۰۰۰", callback_data="shop_10000")
    kb.button("۲۰,۰۰۰", callback_data="shop_20000")
    kb.button("۵۰,۰۰۰", callback_data="shop_50000")
    kb.button("۱۰۰,۰۰۰ ✨", callback_data="shop_100000")
    kb.button("🔙", callback_data="back")
    kb.adjust(2, 2, 1, 1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_shop(callback, user, user_id, amount):
    prices = SHOP_PRICES.get(user["level"], SHOP_PRICES[7])
    if amount not in prices: return
    coins = prices[amount]
    inv = user.get("inventory", [])
    gm = ""
    if amount == 50000:
        fi = random.choice(get_available_fruits(user))
        inv.append(FRUITS[fi]); gm = f"\n🎁 بذر {FRUITS[fi]}"
    elif amount == 100000:
        fi = random.randint(0, len(FRUITS)-1)
        inv.append(f"طلایی_{FRUITS[fi]}"); gm = f"\n✨ بذر طلایی {FRUITS[fi]}"
    new_coins = user["coins"] + coins
    update_user(user_id, {"coins": new_coins, "inventory": inv})
    update_leaderboard(user_id, user["name"], new_coins, user["level"], user["prestige"])
    await callback.message.edit_text(f"✅ +{coins:,} سکه\nموجودی: {new_coins:,}{gm}", reply_markup=get_keyboard(user_id))

# ---------- کارگر ----------
async def show_worker(callback, user, user_id):
    w = user["worker"]; cost = 5000 * w["level"]
    text = f"👷 **کارگر**\nلول: {w['level']}\nوضعیت: {'فعال ✅' if w['active'] else 'غیرفعال ❌'}\nهزینه ارتقاء: {cost:,}"
    kb = InlineKeyboardBuilder()
    kb.button("🔄 فعال/غیرفعال", callback_data="worker_toggle")
    kb.button("⬆️ ارتقاء", callback_data="worker_upgrade")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def toggle_worker(callback, user, user_id):
    w = user["worker"]; w["active"] = not w["active"]
    update_user(user_id, {"worker": w})
    await callback.message.edit_text(f"👷 {'فعال' if w['active'] else 'غیرفعال'}", reply_markup=get_keyboard(user_id))

async def upgrade_worker(callback, user, user_id):
    w = user["worker"]; cost = 5000 * w["level"]
    if user["coins"] < cost:
        await callback.message.edit_text(f"❌ نیاز به {cost:,}", reply_markup=get_keyboard(user_id)); return
    w["level"] += 1
    update_user(user_id, {"coins": user["coins"] - cost, "worker": w})
    await callback.message.edit_text(f"✅ لول {w['level']}", reply_markup=get_keyboard(user_id))

# ---------- هدیه ----------
async def start_gift(callback, user, user_id, state):
    await state.set_state(UserForm.gift_target)
    await callback.message.edit_text("🎁 نام یا کد کاربر مقصد:", reply_markup=get_keyboard(user_id))

# ---------- پرستیژ ----------
async def show_prestige(callback, user, user_id):
    if user["level"] < 7:
        await callback.message.edit_text("🔒 پرستیژ در لول ۷ باز می‌شود.", reply_markup=get_keyboard(user_id)); return
    if user["prestige"] >= 10:
        await callback.message.edit_text("⭐ بالاترین پرستیژ!", reply_markup=get_keyboard(user_id)); return
    nxt = user["prestige"] + 1
    price = PRESTIGE_PRICES[nxt]
    text = (f"⭐ **پرستیژ {nxt}**\nهزینه: {price:,}\n"
            f"ضریب جدید: {user['prestige_multiplier']*1.5:.2f}x\n\n"
            f"⚠️ همه چیز ریست می‌شود (به‌جز نام و پرستیژ)")
    kb = InlineKeyboardBuilder()
    kb.button(f"⭐ خرید ({price:,})", callback_data="buy_prestige")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_prestige(callback, user, user_id):
    if user["prestige"] >= 10: return
    nxt = user["prestige"] + 1
    price = PRESTIGE_PRICES[nxt]
    if user["coins"] < price:
        await callback.message.edit_text(f"❌ نیاز به {price:,}", reply_markup=get_keyboard(user_id)); return
    new_user = create_default_user(user_id)
    new_user["name"] = user["name"]
    new_user["prestige"] = nxt
    new_user["prestige_multiplier"] = user["prestige_multiplier"] * 1.5
    new_user["referral_code"] = user["referral_code"]
    new_user["gifts_given"] = user.get("gifts_given", 0)
    new_user["gifts_received"] = user.get("gifts_received", 0)
    new_user["achievements"] = user.get("achievements", [])
    new_user["last_seen_period"] = get_period_number()
    new_user["current_period"] = get_period_number()
    data = load_data()
    data["users"][str(user_id)] = new_user
    save_data(data)
    update_leaderboard(user_id, user["name"], 1, 1, nxt)
    await callback.message.edit_text(
        f"⭐ **تبریک! پرستیژ {nxt}!**\nضریب: {new_user['prestige_multiplier']:.2f}x",
        reply_markup=get_keyboard(user_id))

# ---------- پت ----------
async def show_pet_menu(callback, user, user_id):
    pet = user.get("pet")
    pet_text = f"{pet['emoji']} {pet['name']} ({pet['value']}% {'سود' if pet['type']=='sell' else 'سرعت' if pet['type']=='speed' else 'XP'})" if pet else "ندارد"
    text = f"🐾 **پت شما:** {pet_text}\n\n🥚 **تخم‌ها:**\n"
    for k, egg in PET_EGGS.items():
        text += f"• {egg['name']}: {egg['price']:,} سکه\n"
    text += "\n⚠️ با هر اسپین، پت فعلی از بین می‌رود!"
    kb = InlineKeyboardBuilder()
    for k, egg in PET_EGGS.items():
        short = {"common":"معمولی","uncommon":"غیرمعمولی","rare":"کمیاب",
                 "epic":"حماسی","legendary":"افسانه‌ای","mythic":"اساطیری"}[k]
        kb.button(f"{short} ({egg['price']:,})", callback_data=f"spin_{k}")
    kb.button("🔙", callback_data="back")
    kb.adjust(2, 2, 2, 1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def do_spin(callback, user, user_id, egg_type):
    if egg_type not in PET_EGGS: return
    egg = PET_EGGS[egg_type]
    if user["coins"] < egg["price"]:
        await callback.message.edit_text(f"❌ نیاز به {egg['price']:,} سکه.", reply_markup=get_keyboard(user_id)); return
    
    new_pet = spin_egg(egg_type)
    if not new_pet: return
    
    # اسپین = حذف سکه + جایگزینی پت
    new_coins = user["coins"] - egg["price"]
    update_user(user_id, {"coins": new_coins, "pet": new_pet})
    update_leaderboard(user_id, user["name"], new_coins, user["level"], user["prestige"])
    
    type_fa = {"sell": "سود بیشتر", "speed": "رشد سریع‌تر", "xp": "XP بیشتر"}
    await callback.message.edit_text(
        f"🥚 **{egg['name']}** باز شد!\n\n"
        f"{new_pet['emoji']} **{new_pet['name']}**\n"
        f"قابلیت: {new_pet['value']}٪ {type_fa[new_pet['type']]}\n\n"
        f"💰 موجودی: {new_coins:,}",
        reply_markup=get_keyboard(user_id))

# ---------- کلن ----------
async def show_clan_menu(callback, user, user_id):
    if not user.get("clan_id"):
        text = (f"🏰 **کلن نداری**\n\n"
                f"ساخت کلن: {CLAN_CREATE_COST:,} سکه\n"
                f"مزایا: +۲٪ سود به ازای هر لول کلن")
        kb = InlineKeyboardBuilder()
        kb.button("🏰 ساخت کلن", callback_data="clan_create")
        kb.button("🔙", callback_data="back")
        kb.adjust(1)
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
    else:
        await show_clan_info(callback, user, user_id)

async def show_clan_info(callback, user, user_id):
    clan = get_clan(user["clan_id"])
    if not clan:
        await callback.message.edit_text("❌ کلن یافت نشد.", reply_markup=get_keyboard(user_id)); return
    is_leader = clan["leader_id"] == str(user_id)
    text = (f"🏰 **{clan['name']}**\n"
            f"لول: {clan['level']} | پاداش: +{clan['level']*CLAN_BONUS_PER_LEVEL}٪ سود\n"
            f"خزانه: {clan['treasury']:,} سکه\n"
            f"اعضا: {len(clan['members'])}/{CLAN_MAX_MEMBERS.get(clan['level'],10)}\n"
            f"لیدر: {clan['leader_name']}\n\n"
            f"👥 **اعضا:**\n")
    for m in clan["members"][:20]:
        mn = clan["member_names"].get(m, "?")
        text += f"• {mn}\n"
    kb = InlineKeyboardBuilder()
    kb.button("👤 دعوت", callback_data="clan_invite")
    kb.button("💰 اهدا", callback_data="clan_donate")
    kb.button("✉️ چت", callback_data="clan_chat")
    if is_leader:
        kb.button("⬆️ ارتقاء کلن", callback_data="clan_upgrade")
        kb.button("🗑 منحل", callback_data="clan_disband")
    else:
        kb.button("🚪 خروج", callback_data="clan_leave")
    kb.button("🔙", callback_data="back")
    kb.adjust(2, 2, 2, 1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def start_clan_create(callback, user, user_id, state):
    if user["coins"] < CLAN_CREATE_COST:
        await callback.message.edit_text(f"❌ نیاز به {CLAN_CREATE_COST:,} سکه.", reply_markup=get_keyboard(user_id)); return
    await state.set_state(UserForm.clan_name)
    await callback.message.edit_text("🏰 نام کلن را وارد کن (۳-۲۰ کاراکتر، بدون فاصله):")

async def upgrade_clan(callback, user, user_id):
    clan = get_clan(user["clan_id"])
    if not clan: return
    if clan["level"] >= 10:
        await callback.message.edit_text("⭐ کلن در بالاترین لول!", reply_markup=get_keyboard(user_id)); return
    nxt = clan["level"] + 1
    cost = CLAN_LEVEL_COSTS[nxt]
    if clan["treasury"] < cost:
        await callback.message.edit_text(f"❌ خزانه کافی نیست. نیاز: {cost:,}", reply_markup=get_keyboard(user_id)); return
    data = load_data()
    data["clans"][user["clan_id"]]["level"] = nxt
    data["clans"][user["clan_id"]]["treasury"] -= cost
    save_data(data)
    await callback.message.edit_text(f"✅ کلن به لول {nxt} ارتقاء یافت!", reply_markup=get_keyboard(user_id))

async def leave_clan(callback, user, user_id):
    clan = get_clan(user["clan_id"])
    if not clan: return
    if clan["leader_id"] == str(user_id):
        await callback.message.edit_text("❌ لیدر نمی‌تواند خارج شود. کلن را منحل کن.", reply_markup=get_keyboard(user_id)); return
    data = load_data()
    if str(user_id) in data["clans"][user["clan_id"]]["members"]:
        data["clans"][user["clan_id"]]["members"].remove(str(user_id))
    data["clans"][user["clan_id"]]["member_names"].pop(str(user_id), None)
    save_data(data)
    update_user(user_id, {"clan_id": None})
    await callback.message.edit_text("🚪 از کلن خارج شدی.", reply_markup=get_keyboard(user_id))

async def disband_clan(callback, user, user_id):
    clan = get_clan(user["clan_id"])
    if not clan: return
    if clan["leader_id"] != str(user_id):
        await callback.message.edit_text("❌ فقط لیدر می‌تواند.", reply_markup=get_keyboard(user_id)); return
    data = load_data()
    for m in clan["members"]:
        update_user(int(m), {"clan_id": None})
    del data["clans"][user["clan_id"]]
    save_data(data)
    await callback.message.edit_text("🗑 کلن منحل شد.", reply_markup=get_keyboard(user_id))

# ---------- لیگ ----------
async def show_league_menu(callback, user, user_id):
    period_num = user.get("current_period", 1)
    prestige = user.get("prestige", 0)
    league_name = LEAGUE_FA.get(prestige, "?")
    profit = user["coins"] - user.get("period_start_coins", user["coins"])
    rank = get_user_league_rank(user_id, user)
    
    # محاسبه زمان باقی‌مانده تا پایان دوره
    data = load_data()
    start_str = data.get("game_start_time")
    if start_str:
        start = datetime.fromisoformat(start_str)
        # زمان پایان دوره فعلی
        period_end = start + timedelta(days=period_num)
        remaining = period_end - datetime.now()
        if remaining.total_seconds() > 0:
            h = int(remaining.total_seconds() // 3600)
            m = int((remaining.total_seconds() % 3600) // 60)
            remaining_text = f"{h} ساعت و {m} دقیقه"
        else:
            remaining_text = "به‌زودی..."
    else:
        remaining_text = "?"
    
    text = (f"🏅 **لیگ {league_name}** — دوره {period_num}\n\n"
            f"💵 سود شما در این دوره: {profit:,}\n"
            f"📊 رتبه شما: {rank}\n"
            f"⏰ پایان دوره: {remaining_text} دیگر\n\n"
            f"🏆 ۱۰٪ برتر دوره، افتخار ویژه می‌گیرند!")
    kb = InlineKeyboardBuilder()
    kb.button("🎖️ افتخارات", callback_data="achievements")
    kb.button("🔙", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def show_achievements(callback, user, user_id):
    achs = user.get("achievements", [])
    if not achs:
        text = "🎖️ **افتخارات**\n\nهنوز افتخاری نداری!"
    else:
        text = f"🎖️ **افتخارات {user['name']}** ({len(achs)} عدد)\n\n"
        for a in achs[-20:]:
            league_name = LEAGUE_FA.get(a.get("league", 0), "?")
            if a["type"] == "top_percent":
                text += f"🏅 جزو {a['percent']}٪ برتر دوره {a['period']}، لیگ {league_name}\n"
            elif a["type"] == "lone_eagle":
                text += f"🦅 عقاب تنهای شماره {a['rank']} در دوره {a['period']}، لیگ {league_name}\n"
    await callback.message.edit_text(text, reply_markup=get_keyboard(user_id))

# ==================== اجرا ====================
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("🤖 ربات فارمینگ بله روشن شد...")
    
    async def stop_after_delay():
        await asyncio.sleep(340 * 60)
        print("⏰ توقف ربات...")
        try: await dp.stop_polling()
        except: pass
    
    asyncio.create_task(stop_after_delay())
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"ربات متوقف شد: {e}")

if __name__ == "__main__":
    asyncio.run(main())
