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

try:
    from baleio.types import LabeledPrice
    HAS_LABELED_PRICE = True
except ImportError:
    HAS_LABELED_PRICE = False

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not set!")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "WALLET-TEST-1111111111111111")

ADMIN_IDS_STR = os.getenv("ADMIN_ID", "0")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]

# ==================== دیتابیس split ====================
DATA_DIR = "data"
USERS_DIR = os.path.join(DATA_DIR, "users")
CLANS_DIR = os.path.join(DATA_DIR, "clans")
GLOBAL_FILE = os.path.join(DATA_DIR, "global.json")
LOCK_FILE = "data.lock"
lock = FileLock(LOCK_FILE, timeout=10)

_DATA_CACHE = None
_DATA_DIRTY = False
_SAVE_TRIGGER = None
_LAST_USER_JSON = {}
_LAST_CLAN_JSON = {}
_LAST_GLOBAL_JSON = ""

GLOBAL_KEYS = ["game_start_time", "first_run_time", "leaderboard", "leagues",
               "active_event", "gift_codes", "banned", "clan_requests", "market"]

# ==================== ثابت‌های بازی ====================
FRUITS = ["توت‌فرنگی", "گوجه", "سیب", "پرتقال", "نارگیل", "آناناس", "میوه اژدها"]
PRICES = [(1, 3), (15, 38), (304, 760), (9120, 22800),
          (456000, 1140000), (27360000, 68400000), (2052000000, 5130000000)]
GROWTH_TIMES = [1, 2.5, 4, 5.5, 7, 8.5, 10]
GOLDEN_MULT = 10

XP_REQUIRED = {1: 5, 2: 30, 3: 75, 4: 250, 5: 1000, 6: 5000}
XP_FROM_SALES = {"توت‌فرنگی": (1, 1), "گوجه": (2, 3), "سیب": (4, 6),
                 "پرتقال": (8, 12), "نارگیل": (20, 30), "آناناس": (35, 65)}

LEVEL_UNLOCKS = {
    1: {"fruits": [0], "features": ["status", "pet", "bank"]},
    2: {"fruits": [0, 1], "features": ["status", "pet", "bank", "leaderboard", "daily_orders"]},
    3: {"fruits": [0, 1, 2], "features": ["status", "pet", "bank", "leaderboard", "daily_orders", "upgrades", "market"]},
    4: {"fruits": [0, 1, 2, 3], "features": ["status", "pet", "bank", "leaderboard", "daily_orders", "upgrades", "market", "shop"]},
    5: {"fruits": [0, 1, 2, 3, 4], "features": ["status", "pet", "bank", "leaderboard", "daily_orders", "upgrades", "market", "shop", "worker", "clan"]},
    6: {"fruits": [0, 1, 2, 3, 4, 5], "features": ["status", "pet", "bank", "leaderboard", "daily_orders", "upgrades", "market", "shop", "worker", "clan"]},
    7: {"fruits": [0, 1, 2, 3, 4, 5, 6], "features": ["status", "pet", "bank", "leaderboard", "daily_orders", "upgrades", "market", "shop", "worker", "clan", "prestige", "league"]},
}
ALL_FEATURES = ["status", "pet", "bank", "leaderboard", "daily_orders", "upgrades",
                "market", "shop", "worker", "clan", "prestige", "league"]
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

MARKET_CURRENCIES = {
    "millet": {"name": "ارزن", "emoji": "🌱", "base_price": 5},
    "alfalfa": {"name": "یونجه", "emoji": "🌿", "base_price": 80},
    "wheat": {"name": "گندم", "emoji": "🌾", "base_price": 200},
    "barley": {"name": "جو", "emoji": "🪴", "base_price": 9000},
    "corn": {"name": "ذرت", "emoji": "🌽", "base_price": 32000},
}

BANK_DEPOSIT_COMMISSION = 0.05
BANK_DAILY_INTEREST = 0.10
LOAN_MULTIPLIER = 5
LOAN_PENALTY_MULTIPLIER = 1.5
JAIL_DURATION_DAYS = 7
JAIL_WORK_INTERVAL_MIN = 10
JAIL_WORKS_MIN = 12
JAIL_WORKS_MAX = 20

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
    "لیگ": "league_menu", "league": "league_menu",
    "افتخار": "achievements", "افتخارات": "achievements", "مدال": "achievements", "مدال‌ها": "achievements", "achievements": "achievements",
    "پرستیژ": "prestige_menu", "prestige": "prestige_menu",
    "زمین": "lands_menu", "زمین‌ها": "lands_menu", "زمینها": "lands_menu", "lands": "lands_menu",
    "انبار": "inventory_menu", "کیف": "inventory_menu", "inventory": "inventory_menu",
    "خرید بذر": "buy_seed_text", "بذر": "buy_seed_text",
    "برداشت": "harvest_text", "برداشت کن": "harvest_text",
    "بازار": "market_menu", "market": "market_menu",
    "بانک": "bank_menu", "bank": "bank_menu",
}


def is_admin(user_id):
    return int(user_id) in ADMIN_IDS and len(ADMIN_IDS) > 0


class UserForm(StatesGroup):
    name = State()
    clan_name = State()
    clan_invite = State()
    clan_donate = State()
    clan_chat = State()
    confirm_transfer = State()
    worker_plant_hours = State()
    worker_harvest_hours = State()
    clan_search = State()
    market_buy_amount = State()
    market_sell_amount = State()
    bank_deposit_amount = State()
    bank_withdraw_amount = State()
    bank_transfer_target = State()
    bank_transfer_amount = State()
    bank_loan_amount = State()
    bank_loan_hours = State()


# ==================== فرمت‌ها ====================
def format_time_remaining(rem_seconds):
    if rem_seconds < 0:
        rem_seconds = 0
    h = int(rem_seconds // 3600)
    m = int((rem_seconds % 3600) // 60)
    s = int(rem_seconds % 60)
    if h > 0:
        return f"{h} ساعت و {m} دقیقه"
    elif m > 0:
        return f"{m} دقیقه و {s} ثانیه"
    else:
        return f"{s} ثانیه"


def format_league_time(rem_seconds):
    if rem_seconds < 0:
        rem_seconds = 0
    d = int(rem_seconds // 86400)
    h = int((rem_seconds % 86400) // 3600)
    m = int((rem_seconds % 3600) // 60)
    parts = []
    if d > 0:
        parts.append(f"{d} روز")
    if h > 0:
        parts.append(f"{h} ساعت")
    if m > 0 or not parts:
        parts.append(f"{m} دقیقه")
    return " و ".join(parts)


def format_coins(amount):
    amount = int(amount)
    if abs(amount) < 1_000_000:
        return f"{amount:,} سکه"
    units = [(1_000_000_000_000, "تریلیون"), (1_000_000_000, "میلیارد"), (1_000_000, "میلیون")]
    parts = []
    remaining = abs(amount)
    for value, name in units:
        if remaining >= value:
            count = remaining // value
            parts.append(f"{count:,} {name}")
            remaining = remaining % value
    result = " و ".join(parts)
    if remaining > 0:
        result += f" و {remaining:,}"
    if amount < 0:
        return f"-{result} سکه"
    return f"{result} سکه"


def format_market_price(p):
    if p >= 1000:
        return f"{p:,.2f}"
    elif p >= 100:
        return f"{p:.2f}"
    elif p >= 1:
        return f"{p:.3f}"
    else:
        return f"{p:.4f}"


async def safe_answer(callback):
    try:
        await callback.answer()
    except Exception:
        pass


async def safe_edit(callback, text, **kwargs):
    try:
        return await callback.message.edit_text(text, **kwargs)
    except Exception:
        try:
            return await bot.send_message(callback.from_user.id, text, **kwargs)
        except Exception:
            pass


# ==================== دیتابیس ====================
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(CLANS_DIR, exist_ok=True)


def _write_json(path, data):
    tf = path + ".tmp"
    try:
        with open(tf, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tf, path)
        return True
    except Exception as e:
        print(f"write error {path}: {e}")
        return False


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def create_default_market():
    return {
        "state": "normal",
        "last_update": datetime.now().isoformat(),
        "currencies": {
            cid: {"base_price": float(c["base_price"]),
                  "price": float(c["base_price"]),
                  "mode": "normal",
                  "last_change": 0.0}
            for cid, c in MARKET_CURRENCIES.items()
        }
    }


def create_default_data():
    now = datetime.now().isoformat()
    return {"game_start_time": now, "first_run_time": now, "users": {},
            "leaderboard": [], "clans": {}, "leagues": {},
            "active_event": None, "gift_codes": {}, "banned": [],
            "clan_requests": {}, "market": create_default_market()}


def create_default_bank():
    return {
        "account_number": None,
        "balance": 0,
        "last_interest": datetime.now().isoformat(),
        "balance_history": [],
        "history": [],
        "loan": None,
        "loan_banned_until": None,
        "in_jail": False,
        "jail_until": None,
        "jail_work_count": 0,
        "jail_target_works": random.randint(JAIL_WORKS_MIN, JAIL_WORKS_MAX),
        "jail_last_work": None,
        "jail_ready_to_pay": False,
        "jail_reason": None,
    }


def create_default_user(user_id):
    now = datetime.now().isoformat()
    return {
        "name": "", "level": 1, "xp": 0, "coins": 1,
        "plots": [{"fruit": 0, "state": "idle", "harvest_time": None}],
        "max_plots": 1, "current_fruit": 0, "inventory": {},
        "upgrades": {"auto_water": 0, "golden_pot": 0, "professional_seeder": 0},
        "workers": {
            "planting": {"active": False, "fruit": None, "hours": 0, "expires_at": None, "paused": False, "paused_at": None},
            "harvest_sell": {"active": False, "hours": 0, "expires_at": None, "paused": False, "paused_at": None},
        },
        "daily_orders": {"orders": [], "completed": False, "completed_at": None, "next_at": None},
        "prestige": 0, "prestige_multiplier": 1.0,
        "referral_code": f"REF{user_id}{random.randint(100,999)}",
        "pet": None, "phoenix_owned": False, "clan_id": None,
        "period_start_coins": 1, "period_start_time": now,
        "current_period": 1, "last_seen_period": 1,
        "achievements": [], "pending_purchase": None, "used_gift_codes": [],
        "market_holdings": {},
        "bank": create_default_bank(),
    }


def _ensure_keys(data):
    if not isinstance(data, dict):
        return create_default_data()
    for k, v in create_default_data().items():
        if k not in data:
            data[k] = v
    if not data.get("first_run_time"):
        data["first_run_time"] = data.get("game_start_time") or datetime.now().isoformat()
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
            "planting": {"active": False, "fruit": None, "hours": 0, "expires_at": None, "paused": False, "paused_at": None},
            "harvest_sell": {"active": False, "hours": 0, "expires_at": None, "paused": False, "paused_at": None},
        }
    for wk in ["planting", "harvest_sell"]:
        if wk in u["workers"]:
            if "paused" not in u["workers"][wk]:
                u["workers"][wk]["paused"] = False
            if "paused_at" not in u["workers"][wk]:
                u["workers"][wk]["paused_at"] = None
    u.pop("worker", None)
    if u.get("phoenix_owned") and u.get("pet", {}).get("name") == "ققنوس":
        if "speed_value" not in u["pet"]:
            u["pet"] = PHOENIX_PET
    if "bank" not in u:
        u["bank"] = create_default_bank()
    else:
        default_bank = create_default_bank()
        for k, v in default_bank.items():
            if k not in u["bank"]:
                u["bank"][k] = v
    do = u.get("daily_orders", {})
    if isinstance(do, dict):
        if "completed_at" not in do:
            do["completed_at"] = None
        if "next_at" not in do:
            do["next_at"] = None
        u["daily_orders"] = do
    defaults = {
        "max_plots": 1, "current_fruit": 0, "pet": None, "phoenix_owned": False,
        "clan_id": None, "achievements": [], "pending_purchase": None,
        "period_start_coins": 1, "period_start_time": gst,
        "current_period": 1, "last_seen_period": 1,
        "used_gift_codes": [], "market_holdings": {},
    }
    for k, v in defaults.items():
        if k not in u:
            u[k] = v


def load_data():
    global _DATA_CACHE, _LAST_USER_JSON, _LAST_CLAN_JSON, _LAST_GLOBAL_JSON
    if _DATA_CACHE is not None:
        return _DATA_CACHE

    with lock:
        _ensure_dirs()

        # GitHub Actions: اگه data.json هست، migrate کن (بدون پاک کردن)
        if (not os.path.exists(GLOBAL_FILE) and not os.listdir(USERS_DIR)
                and os.path.exists("data.json")):
            try:
                with open("data.json", "r", encoding="utf-8") as f:
                    old = json.load(f)
                for uid, u in old.get("users", {}).items():
                    _write_json(os.path.join(USERS_DIR, f"{uid}.json"), u)
                for cid, c in old.get("clans", {}).items():
                    _write_json(os.path.join(CLANS_DIR, f"{cid}.json"), c)
                global_data = {k: old.get(k) for k in GLOBAL_KEYS}
                _write_json(GLOBAL_FILE, global_data)
                print(f"📦 Loaded from data.json ({len(old.get('users', {}))} users)")
            except Exception as e:
                print(f"❌ Migration error: {e}")

        global_data = _read_json(GLOBAL_FILE) or {}

        users = {}
        if os.path.isdir(USERS_DIR):
            for fname in os.listdir(USERS_DIR):
                if fname.endswith(".json"):
                    uid = fname[:-5]
                    u = _read_json(os.path.join(USERS_DIR, fname))
                    if u:
                        users[uid] = u

        clans = {}
        if os.path.isdir(CLANS_DIR):
            for fname in os.listdir(CLANS_DIR):
                if fname.endswith(".json"):
                    cid = fname[:-5]
                    c = _read_json(os.path.join(CLANS_DIR, fname))
                    if c:
                        clans[cid] = c

        if not global_data and not users:
            data = create_default_data()
        else:
            data = create_default_data()
            data.update(global_data)
            data["users"] = users
            data["clans"] = clans

        data = _ensure_keys(data)
        gst = data.get("game_start_time", datetime.now().isoformat())
        for uid, u in data.get("users", {}).items():
            _migrate_user(u, gst)

        _LAST_USER_JSON = {}
        for uid, u in data["users"].items():
            try:
                _LAST_USER_JSON[uid] = json.dumps(u, ensure_ascii=False, sort_keys=True)
            except Exception:
                _LAST_USER_JSON[uid] = ""
        _LAST_CLAN_JSON = {}
        for cid, c in data["clans"].items():
            try:
                _LAST_CLAN_JSON[cid] = json.dumps(c, ensure_ascii=False, sort_keys=True)
            except Exception:
                _LAST_CLAN_JSON[cid] = ""
        try:
            _LAST_GLOBAL_JSON = json.dumps(
                {k: data.get(k) for k in GLOBAL_KEYS},
                ensure_ascii=False, sort_keys=True)
        except Exception:
            _LAST_GLOBAL_JSON = ""

        _DATA_CACHE = data
        return data


def save_data(data):
    global _DATA_CACHE, _DATA_DIRTY, _SAVE_TRIGGER
    _DATA_CACHE = _ensure_keys(data)
    _DATA_DIRTY = True
    if _SAVE_TRIGGER is not None:
        try:
            _SAVE_TRIGGER.set()
        except Exception:
            pass
    return True


def _write_to_disk():
    global _DATA_DIRTY, _LAST_USER_JSON, _LAST_CLAN_JSON, _LAST_GLOBAL_JSON
    if _DATA_CACHE is None or not _DATA_DIRTY:
        return
    with lock:
        data = _DATA_CACHE

        try:
            global_snap = {k: data.get(k) for k in GLOBAL_KEYS}
            global_json = json.dumps(global_snap, ensure_ascii=False, sort_keys=True)
            if global_json != _LAST_GLOBAL_JSON:
                _write_json(GLOBAL_FILE, global_snap)
                _LAST_GLOBAL_JSON = global_json
        except Exception as e:
            print(f"global write error: {e}")

        for uid, u in data.get("users", {}).items():
            try:
                uj = json.dumps(u, ensure_ascii=False, sort_keys=True)
            except Exception:
                continue
            if uj != _LAST_USER_JSON.get(uid):
                _write_json(os.path.join(USERS_DIR, f"{uid}.json"), u)
                _LAST_USER_JSON[uid] = uj

        for cid, c in data.get("clans", {}).items():
            try:
                cj = json.dumps(c, ensure_ascii=False, sort_keys=True)
            except Exception:
                continue
            if cj != _LAST_CLAN_JSON.get(cid):
                _write_json(os.path.join(CLANS_DIR, f"{cid}.json"), c)
                _LAST_CLAN_JSON[cid] = cj

        _DATA_DIRTY = False


def merge_to_single_file():
    """همه split files رو توی data.json جمع می‌کنه (برای git push)"""
    data = load_data()
    single = {}
    for k in GLOBAL_KEYS:
        single[k] = data.get(k)
    single["users"] = data.get("users", {})
    single["clans"] = data.get("clans", {})
    try:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(single, f, ensure_ascii=False, separators=(",", ":"))
        print(f"✅ Merged: {len(single['users'])} users, {len(single['clans'])} clans")
        return True
    except Exception as e:
        print(f"❌ Merge error: {e}")
        return False


async def saver_loop():
    global _SAVE_TRIGGER
    _SAVE_TRIGGER = asyncio.Event()
    while True:
        try:
            await asyncio.wait_for(_SAVE_TRIGGER.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass
        _SAVE_TRIGGER.clear()
        await asyncio.sleep(0.3)
        if _DATA_DIRTY:
            try:
                await asyncio.to_thread(_write_to_disk)
            except Exception as e:
                print(f"❌ saver error: {e}")


async def sync_to_single_loop():
    """هر ۱۰ دقیقه data.json محلی رو آپدیت کن"""
    await asyncio.sleep(600)
    while True:
        try:
            await asyncio.to_thread(merge_to_single_file)
        except Exception as e:
            print(f"❌ Sync error: {e}")
        await asyncio.sleep(600)


def trim_old_data():
    data = load_data()
    now = datetime.now()
    changed = False

    gc = data.get("gift_codes", {})
    expired = []
    for code, cd in gc.items():
        try:
            end = datetime.fromisoformat(cd.get("end_time", ""))
            if (now - end).days > 7:
                expired.append(code)
        except Exception:
            pass
    for code in expired:
        del gc[code]
        changed = True

    for uid, user in data.get("users", {}).items():
        bank = user.get("bank", {})
        hist = bank.get("history", [])
        if len(hist) > 30:
            bank["history"] = hist[-30:]
            user["bank"] = bank
            changed = True

    reqs = data.get("clan_requests", {})
    old = []
    for uid, r in reqs.items():
        try:
            created = datetime.fromisoformat(r.get("created_at", ""))
            if (now - created).days > 3:
                old.append(uid)
        except Exception:
            pass
    for uid in old:
        del reqs[uid]
        changed = True

    if changed:
        save_data(data)


# ==================== توابع کمکی ====================
def get_user(user_id):
    return load_data()["users"].get(str(user_id))


def update_user(user_id, updates):
    data = load_data()
    uid_str = str(user_id)
    if uid_str not in data["users"]:
        data["users"][uid_str] = create_default_user(user_id)
    data["users"][uid_str].update(updates)
    save_data(data)


def update_leaderboard(user_id, name, coins, level, prestige):
    data = load_data()
    data["leaderboard"] = [i for i in data["leaderboard"] if i.get("user_id") != str(user_id)]
    data["leaderboard"].append({"user_id": str(user_id), "name": name,
                                 "coins": coins, "level": level, "prestige": prestige})
    data["leaderboard"].sort(
        key=lambda x: (x.get("prestige", 0), x.get("level", 1), x.get("coins", 0)),
        reverse=True)
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


def find_user_by_account(acc):
    data = load_data()
    for uid, u in data["users"].items():
        if u.get("bank", {}).get("account_number") == acc:
            return uid, u
    return None, None


def generate_account_number():
    data = load_data()
    existing = set()
    for u in data["users"].values():
        acc = u.get("bank", {}).get("account_number")
        if acc:
            existing.add(acc)
    for _ in range(100):
        num = str(random.randint(100000, 999999))
        if num not in existing:
            return num
    return str(random.randint(1000000, 9999999))


def ensure_account_number(user_id, user):
    bank = user.get("bank", create_default_bank())
    if not bank.get("account_number"):
        bank["account_number"] = generate_account_number()
        user["bank"] = bank
        update_user(user_id, {"bank": bank})
    return user


def get_active_event():
    data = load_data()
    ev = data.get("active_event")
    if not ev:
        return None
    try:
        end = datetime.fromisoformat(ev["end_time"])
        if datetime.now() >= end:
            data["active_event"] = None
            save_data(data)
            return None
    except Exception:
        return None
    return ev


def get_inv_count(user):
    return sum(user.get("inventory", {}).values())


def get_inv_capacity(user):
    return INVENTORY_CAPACITY.get(user.get("level", 1), 1)


def add_to_inventory(user_id, fruit_name):
    user = get_user(user_id)
    if not user:
        return False
    if get_inv_count(user) >= get_inv_capacity(user):
        return False
    inv = user.get("inventory", {})
    inv[fruit_name] = inv.get(fruit_name, 0) + 1
    update_user(user_id, {"inventory": inv})
    return True


def get_plot_remaining(plot):
    if plot.get("state") != "growing":
        return None
    ht = plot.get("harvest_time")
    if not ht:
        return None
    try:
        return max(0, int((datetime.fromisoformat(ht) - datetime.now()).total_seconds()))
    except Exception:
        return None


def check_all_harvests(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user:
        return False
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
                except Exception:
                    pass
    if changed:
        save_data(data)
    return changed


def get_current_season():
    data = load_data()
    s = data.get("game_start_time", datetime.now().isoformat())
    try:
        start = datetime.fromisoformat(s)
        elapsed = (datetime.now() - start).total_seconds() / 60
        return SEASON_CYCLE[int(elapsed // SEASON_DURATION_MIN) % len(SEASON_CYCLE)]
    except Exception:
        return "spring"


def get_season_effects():
    season = get_current_season()
    e = {"growth_mult": 1.0, "sell_mult": 1.0, "buy_mult": 1.0, "golden_chance": 0.02, "xp_mult": 1.0}
    if season == "spring":
        e["growth_mult"] = 1 / 1.2
    elif season == "summer":
        e["golden_chance"] = 0.02 * 1.75
    elif season == "autumn":
        e["sell_mult"] = random.uniform(1.25, 1.5)
    elif season == "winter":
        e["buy_mult"] = 1 / 1.2
    ev = get_active_event()
    if ev:
        e["buy_mult"] *= ev.get("buy_mult", 1.0)
        e["sell_mult"] *= ev.get("sell_mult", 1.0)
        e["growth_mult"] *= ev.get("growth_mult", 1.0)
        e["xp_mult"] *= ev.get("xp_mult", 1.0)
    return e, season


def get_pet_effect(user, t):
    pet = user.get("pet")
    if not pet:
        return 0
    if pet.get("type") == t:
        return pet.get("value", 0)
    if f"{t}_value" in pet:
        return pet[f"{t}_value"]
    return 0


def spin_egg(egg_type):
    if egg_type not in PET_EGGS:
        return None
    pets = PET_EGGS[egg_type]["pets"]
    r = random.randint(1, 100)
    c = 0
    for p in pets:
        c += p["chance"]
        if r <= c:
            return p
    return pets[-1]


def get_clan(clan_id):
    return load_data()["clans"].get(clan_id)


def create_clan(clan_id, name, lid, lname):
    data = load_data()
    if clan_id in data["clans"]:
        return False
    data["clans"][clan_id] = {"name": name, "leader_id": lid, "leader_name": lname,
        "level": 1, "treasury": 0, "members": [lid],
        "member_names": {lid: lname}, "created_at": datetime.now().isoformat()}
    save_data(data)
    return True


def get_clan_bonus(user):
    if not user.get("clan_id"):
        return 0
    clan = get_clan(user["clan_id"])
    return clan["level"] * CLAN_BONUS_PER_LEVEL if clan else 0


def get_clan_leaderboard():
    data = load_data()
    clans = data.get("clans", {})
    sorted_clans = sorted(
        clans.items(),
        key=lambda x: (x[1].get("level", 1), x[1].get("treasury", 0)),
        reverse=True)
    return sorted_clans[:20]


def get_week_number(s, now=None):
    start = datetime.fromisoformat(s)
    if now is None:
        now = datetime.now()
    return int((now - start).total_seconds() / (7 * 24 * 3600)) + 1


def get_period_number():
    data = load_data()
    s = data.get("first_run_time") or data.get("game_start_time")
    return get_week_number(s) if s else 1


def get_period_end_datetime(period_num):
    data = load_data()
    s = data.get("first_run_time") or data.get("game_start_time")
    if not s:
        return None
    try:
        start = datetime.fromisoformat(s)
        return start + timedelta(days=7 * period_num)
    except Exception:
        return None


def ensure_user_in_league(user_id, user):
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0:
        return
    pk = str(user.get("prestige", 0))
    pn = user.get("current_period", 1)
    per_key = f"period_{pn}"
    data = load_data()
    data.setdefault("leagues", {}).setdefault(pk, {}).setdefault(per_key,
        {"started_at": user.get("period_start_time", datetime.now().isoformat()), "members": {}})
    profit = user["coins"] - user.get("period_start_coins", 1)
    data["leagues"][pk][per_key]["members"][str(user_id)] = {
        "name": user.get("name", "?"), "profit": profit}
    save_data(data)


def process_period_end(pn, user, uid_str):
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0:
        return
    pk = str(user.get("prestige", 0))
    data = load_data()
    leagues = data.get("leagues", {})
    per_key = f"period_{pn}"
    if pk not in leagues or per_key not in leagues[pk]:
        return
    members = leagues[pk][per_key].get("members", {})
    if uid_str not in members:
        return
    total = len(members)
    if total == 0:
        return
    sm = sorted(members.items(), key=lambda x: x[1].get("profit", 0), reverse=True)
    rank = next((i+1 for i, (uid, _) in enumerate(sm) if uid == uid_str), 0)
    if rank == 0:
        return
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
    if not user:
        return False
    lp = user.get("last_seen_period", cp)
    if cp > lp:
        for p in range(lp, cp):
            process_period_end(p, user, str(user_id))
        user["period_start_coins"] = user["coins"]
        user["period_start_time"] = datetime.now().isoformat()
        user["current_period"] = cp
        user["last_seen_period"] = cp
        save_data(data)
        return True
    return False


def update_league_profit(user_id, user, profit):
    if user.get("level", 1) < 7 and user.get("prestige", 0) == 0:
        return
    pk = str(user.get("prestige", 0))
    pn = user.get("current_period", 1)
    per_key = f"period_{pn}"
    data = load_data()
    data.setdefault("leagues", {}).setdefault(pk, {}).setdefault(per_key,
        {"started_at": user.get("period_start_time"), "members": {}})
    data["leagues"][pk][per_key]["members"][str(user_id)] = {"name": user.get("name", "?"), "profit": profit}
    save_data(data)


def get_available_fruits(user):
    if user.get("prestige", 0) > 0:
        return ALL_FRUITS
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["fruits"]


def get_available_features(user):
    if user.get("prestige", 0) > 0:
        return ALL_FEATURES
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["features"]


def has_feature(user, f):
    return f in get_available_features(user)


def xp_needed_for(l):
    return XP_REQUIRED.get(l, 999999)


def xp_from_sale(f):
    return random.randint(*XP_FROM_SALES[f]) if f in XP_FROM_SALES else 0


def get_land_price(cp):
    if cp >= MAX_PLOTS:
        return None
    return LAND_PRICES[cp - 1]


def is_banned(user_id):
    return str(user_id) in load_data().get("banned", [])


def get_initial_coins_for_prestige(user):
    mult = user.get("prestige_multiplier", 1.0)
    return max(1, int(PRICES[0][0] * mult))


def get_min_coin_reserve(user):
    mult = user.get("prestige_multiplier", 1.0)
    return max(1, int(PRICES[0][0] * mult))


# ==================== ارتقاء ابزار ====================
def upgrade_price(key, current_level):
    base = {"auto_water": 1000, "golden_pot": 2000, "professional_seeder": 5000}
    if key not in base:
        return None
    return base[key] * (100 ** current_level)


def get_growth_mult(user):
    lvl = user["upgrades"].get("auto_water", 0)
    if lvl > 0:
        return 0.8 ** lvl
    return 1.0


def get_seed_price(fruit_idx, user, effects):
    bp = int(PRICES[fruit_idx][0] * user["prestige_multiplier"] * effects["buy_mult"])
    lvl = user["upgrades"].get("professional_seeder", 0)
    if lvl > 0:
        discount = min(0.5, 0.1 * lvl)
        bp = int(bp * (1 - discount))
    return max(1, bp)


def get_sell_bonus(user):
    lvl = user["upgrades"].get("golden_pot", 0)
    return 1 + 0.1 * lvl


# ==================== بانک ====================
def update_bank_interest(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user:
        return
    _apply_interest_to_user(user, datetime.now())
    save_data(data)


def _apply_interest_to_user(user, now):
    bank = user.get("bank", create_default_bank())
    last_str = bank.get("last_interest")
    if not last_str:
        bank["last_interest"] = now.isoformat()
        user["bank"] = bank
        return
    try:
        last = datetime.fromisoformat(last_str)
    except Exception:
        bank["last_interest"] = now.isoformat()
        user["bank"] = bank
        return
    elapsed_days = (now - last).total_seconds() / 86400
    if elapsed_days >= 1:
        days = int(elapsed_days)
        balance = bank.get("balance", 0)
        new_balance = int(balance * ((1 + BANK_DAILY_INTEREST) ** days))
        added = new_balance - balance
        bank["balance"] = new_balance
        bank["last_interest"] = (last + timedelta(days=days)).isoformat()
        history = bank.get("history", [])
        history.append({"type": "interest", "amount": added,
                        "time": now.isoformat(), "days": days})
        bank["history"] = history[-50:]
    user["bank"] = bank


def apply_interest_all_users():
    data = load_data()
    now = datetime.now()
    changed = False
    for uid, user in data.get("users", {}).items():
        try:
            bank_before = user.get("bank", {}).get("last_interest")
            _apply_interest_to_user(user, now)
            if user.get("bank", {}).get("last_interest") != bank_before:
                changed = True
        except Exception as e:
            print(f"Interest error {uid}: {e}")
    if changed:
        save_data(data)
        print(f"✅ Bank interest at {now.strftime('%H:%M')}")


def check_overdue_loans():
    data = load_data()
    now = datetime.now()
    notifications = []
    for uid, user in data.get("users", {}).items():
        try:
            bank = user.get("bank", {})
            loan = bank.get("loan")
            if not loan:
                continue
            try:
                due = datetime.fromisoformat(loan["due_time"])
            except Exception:
                continue
            remaining = (due - now).total_seconds()
            total_due = loan.get("total_due", 0)

            if 0 < remaining <= 15 * 60 and not loan.get("warning_sent"):
                loan["warning_sent"] = True
                bank["loan"] = loan
                notifications.append((uid,
                    f"⚠️ **هشدار وام**\n\n"
                    f"⏰ فقط **{format_time_remaining(remaining)}** تا سررسید!\n"
                    f"💵 بازپرداخت: {format_coins(total_due)}\n\n"
                    f"❌ اگه پرداخت نکنی، **۱.۵ برابر** جریمه می‌شی!"))
                continue

            if remaining <= 0:
                penalty = int(total_due * LOAN_PENALTY_MULTIPLIER)
                coins = user.get("coins", 0)
                if coins >= penalty:
                    user["coins"] = coins - penalty
                    bank["loan"] = None
                    bank["loan_banned_until"] = (now + timedelta(days=7)).isoformat()
                    notifications.append((uid,
                        f"💸 **وام معوق!**\n\n"
                        f"💰 جریمه (۱.۵ برابر): **{format_coins(penalty)}**\n"
                        f"💼 سکه‌هات: {format_coins(user['coins'])}\n\n"
                        f"🚫 تا **۷ روز** نمی‌تونی وام بگیری."))
                else:
                    user["coins"] = 0
                    bank["loan"] = None
                    bank["in_jail"] = True
                    bank["jail_until"] = (now + timedelta(days=JAIL_DURATION_DAYS)).isoformat()
                    bank["jail_work_count"] = 0
                    bank["jail_target_works"] = random.randint(JAIL_WORKS_MIN, JAIL_WORKS_MAX)
                    bank["jail_last_work"] = None
                    bank["jail_ready_to_pay"] = False
                    bank["loan_banned_until"] = None
                    bank["jail_reason"] = "loan_overdue"
                    notifications.append((uid,
                        f"🔒 **به زندان افتادی!**\n\n"
                        f"💸 وامت رو پرداخت نکردی و پول کافی نداشتی.\n\n"
                        f"⏰ مدت: **{JAIL_DURATION_DAYS} روز**\n"
                        f"🔨 با کار کردن می‌تونی زودتر آزاد شی.\n"
                        f"🚫 بعد از آزادی، **۷ روز** منع وام."))
        except Exception as e:
            print(f"Loan check {uid}: {e}")
    if notifications:
        save_data(data)
    return notifications


def get_avg_balance_24h(user):
    bank = user.get("bank", {})
    hist = bank.get("balance_history", [])
    if not hist:
        return bank.get("balance", 0)
    balances = [h["balance"] for h in hist]
    return sum(balances) // len(balances)


def calculate_loan_due(amount, hours):
    periods = int(hours * 2)
    return amount + int(amount * 0.40 * periods)


# ==================== بازار ====================
def update_market_prices():
    data = load_data()
    market = data.get("market")
    if not market:
        market = create_default_market()
        data["market"] = market
        save_data(data)
        return
    last_str = market.get("last_update")
    if not last_str:
        market["last_update"] = datetime.now().isoformat()
        save_data(data)
        return
    try:
        last = datetime.fromisoformat(last_str)
    except Exception:
        market["last_update"] = datetime.now().isoformat()
        save_data(data)
        return
    elapsed = (datetime.now() - last).total_seconds()
    minutes = int(elapsed // 60)
    if minutes < 1:
        return
    minutes = min(minutes, 120)

    state = market.get("state", "normal")
    if state == "profit":
        drift = 1.005
    elif state == "loss":
        drift = 0.9995
    else:
        drift = 1.0

    for _ in range(minutes):
        for cid, cdata in market["currencies"].items():
            base = cdata["base_price"] * drift
            cdata["base_price"] = round(base, 4)
            change = random.uniform(-5, 5) / 100
            new_price = base * (1 + change)
            cdata["price"] = round(new_price, 4)
            cdata["last_change"] = round(change * 100, 2)

    market["last_update"] = datetime.now().isoformat()
    data["market"] = market
    save_data(data)


def get_market_data():
    data = load_data()
    market = data.get("market")
    if not market:
        market = create_default_market()
        data["market"] = market
        save_data(data)
    return market


def get_market_state_fa(s):
    return {"normal": "عادی", "profit": "سود 📈", "loss": "ضرر 📉"}.get(s, "عادی")


# ==================== کارگرها ====================
def process_workers(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user:
        return
    workers = user.get("workers", {})
    now = datetime.now()
    changed = False
    effects, _ = get_season_effects()
    pw = workers.get("planting", {})
    if pw.get("active") and not pw.get("paused"):
        try:
            expires = datetime.fromisoformat(pw["expires_at"])
            if now >= expires:
                pw["active"] = False
                pw["fruit"] = None
                pw["expires_at"] = None
                pw["paused"] = False
                pw["paused_at"] = None
                changed = True
            else:
                fi = pw.get("fruit")
                if fi is not None:
                    for plot in user.get("plots", []):
                        if plot["state"] != "idle":
                            continue
                        buy_price = get_seed_price(fi, user, effects)
                        if user["coins"] < buy_price:
                            break
                        gt = GROWTH_TIMES[fi] * effects["growth_mult"] * get_growth_mult(user)
                        sb = get_pet_effect(user, "speed")
                        if sb > 0:
                            gt *= (1 - sb / 100)
                        ht = now + timedelta(minutes=gt)
                        plot["fruit"] = fi
                        plot["state"] = "growing"
                        plot["harvest_time"] = ht.isoformat()
                        user["coins"] -= buy_price
                        changed = True
        except Exception as e:
            print(f"Worker plant error: {e}")
    hw = workers.get("harvest_sell", {})
    if hw.get("active") and not hw.get("paused"):
        try:
            expires = datetime.fromisoformat(hw["expires_at"])
            if now >= expires:
                hw["active"] = False
                hw["expires_at"] = None
                hw["paused"] = False
                hw["paused_at"] = None
                changed = True
            else:
                for plot in user.get("plots", []):
                    if plot["state"] != "harvested":
                        continue
                    fn = FRUITS[plot.get("fruit", 0)]
                    inv = user.get("inventory", {})
                    if sum(inv.values()) >= get_inv_capacity(user):
                        break
                    inv[fn] = inv.get(fn, 0) + 1
                    user["inventory"] = inv
                    plot["fruit"] = 0
                    plot["state"] = "idle"
                    plot["harvest_time"] = None
                    changed = True
                inv = user.get("inventory", {})
                sold_count = 0
                MAX_PER_CALL = 50
                for fn in list(inv.keys()):
                    if sold_count >= MAX_PER_CALL:
                        break
                    if inv.get(fn, 0) <= 0:
                        continue
                    is_golden = fn.startswith("طلایی_")
                    real_name = fn.replace("طلایی_", "") if is_golden else fn
                    try:
                        cf = FRUITS.index(real_name)
                    except Exception:
                        continue
                    bs = int(PRICES[cf][1] * user["prestige_multiplier"] * effects["sell_mult"])
                    if is_golden:
                        bs *= GOLDEN_MULT
                    sp = bs
                    pb = get_pet_effect(user, "sell")
                    if pb > 0:
                        sp += int(bs * pb / 100)
                    cb = get_clan_bonus(user)
                    if cb > 0:
                        sp += int(bs * cb / 100)
                    if user["upgrades"].get("golden_pot", 0) > 0:
                        sp = int(sp * get_sell_bonus(user))
                    commission = int(sp * 0.2)
                    final_sp = sp - commission
                    xp = int(xp_from_sale(real_name) * user["prestige_multiplier"] * effects["xp_mult"])
                    if is_golden:
                        xp *= GOLDEN_MULT
                    px = get_pet_effect(user, "xp")
                    if px > 0:
                        xp += int(xp * px / 100)
                    user["coins"] += final_sp
                    user["xp"] += xp
                    while user["level"] < 7 and user["xp"] >= xp_needed_for(user["level"]):
                        user["xp"] -= xp_needed_for(user["level"])
                        user["level"] += 1
                    inv[fn] -= 1
                    if inv[fn] <= 0:
                        del inv[fn]
                    user["inventory"] = inv
                    changed = True
                    sold_count += 1
        except Exception as e:
            print(f"Worker harvest error: {e}")
    if changed:
        user["workers"] = workers
        save_data(data)
        update_leaderboard(user_id, user["name"], user["coins"], user["level"], user["prestige"])
        profit = user["coins"] - user.get("period_start_coins", 1)
        update_league_profit(user_id, user, profit)


# ==================== توابع کمکی پیام ====================
class FakeMsg:
    def __init__(self, msg):
        self._msg = msg
    async def edit_text(self, text, **kw):
        return await self._msg.answer(text, **kw)
    async def delete(self):
        try:
            await self._msg.delete()
        except Exception:
            pass
    async def answer(self, text, **kw):
        return await self._msg.answer(text, **kw)


class FakeCallback:
    def __init__(self, message, data):
        self.message = FakeMsg(message)
        self.from_user = message.from_user
        self.data = data
    async def answer(self, *a, **kw):
        pass


def get_keyboard(user_id):
    user = get_user(user_id)
    if not user:
        return InlineKeyboardBuilder().as_markup()
    prefix = f"owner_{user_id}_"
    kb = InlineKeyboardBuilder()
    plots = user.get("plots", [])
    max_plots = user.get("max_plots", 1)
    if max_plots == 1 and plots:
        plot = plots[0]
        cf = plot.get("fruit", 0)
        fruit = FRUITS[cf]
        if plot["state"] == "growing":
            rem = get_plot_remaining(plot)
            if rem is not None and rem > 0:
                mins = rem // 60
                secs = rem % 60
                kb.button(f"⏳ در حال رشد ({mins}:{secs:02d})", callback_data="noop")
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
    if has_feature(user, "pet"):
        kb.button("🐾 پت", callback_data=f"{prefix}pet_menu")
    if has_feature(user, "bank"):
        kb.button("🏦 بانک", callback_data=f"{prefix}bank_menu")
    if has_feature(user, "leaderboard"):
        kb.button("🏆 لیدربرد", callback_data=f"{prefix}leaderboard")
    if has_feature(user, "daily_orders"):
        kb.button("📦 ماموریت‌ها", callback_data=f"{prefix}daily_orders")
    if has_feature(user, "upgrades"):
        kb.button("🔧 ارتقاء ابزار", callback_data=f"{prefix}upgrades")
    if has_feature(user, "market"):
        kb.button("💹 بازار", callback_data=f"{prefix}market_menu")
    if has_feature(user, "shop"):
        kb.button("🛒 فروشگاه سکه", callback_data=f"{prefix}shop")
    if has_feature(user, "worker"):
        kb.button("👷 کارگرها", callback_data=f"{prefix}worker_menu")
    if has_feature(user, "clan"):
        kb.button("🏰 کلن", callback_data=f"{prefix}clan_menu")
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
            f"💰 سکه: {format_coins(user['coins'])}\n"
            f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
            f"🌤 فصل: {SEASON_FA[season]}\n")
    ev = get_active_event()
    if ev:
        try:
            end = datetime.fromisoformat(ev["end_time"])
            rem = end - datetime.now()
            text += f"🎉 **ایونت فعال!** ({format_time_remaining(rem.total_seconds())})\n"
        except Exception:
            pass
    if "prestige" in feats:
        text += f"⭐ پرستیژ: {user['prestige']} | ضریب: {mult:.2f}x\n"
    if "league" in feats:
        text += f"💵 سود دوره {pn}: {format_coins(profit)}\n"
    if "pet" in feats:
        pet = user.get("pet")
        if pet:
            tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
            pet_text = f"{pet['emoji']} {pet['name']} (+{pet['value']}٪ {tfa.get(pet['type'], '')}"
            for k in ["sell", "speed", "xp"]:
                if k != pet.get("type") and f"{k}_value" in pet:
                    pet_text += f" | +{pet[f'{k}_value']}٪ {tfa[k]}"
            pet_text += ")"
        else:
            pet_text = "ندارد"
        text += f"🐾 پت: {pet_text}\n"
    if "bank" in feats:
        bank = user.get("bank", {})
        acc = bank.get("account_number") or "—"
        text += f"🏦 حساب: `{acc}` | سپرده: {format_coins(bank.get('balance', 0))}\n"
    text += f"📦 انبار: {inv_count}/{inv_cap}\n"
    text += f"🏞️ زمین‌ها: {user.get('max_plots', 1)}\n"
    if "worker" in feats:
        workers = user.get("workers", {})
        pw = workers.get("planting", {})
        hw = workers.get("harvest_sell", {})
        if pw.get("active"):
            try:
                exp = datetime.fromisoformat(pw["expires_at"])
                rem = (exp - datetime.now()).total_seconds()
                st = "⏸" if pw.get("paused") else "▶️"
                text += f"🌱 کارگر کاشت: {st} ({format_time_remaining(rem)})\n"
            except Exception:
                text += f"🌱 کارگر کاشت: فعال\n"
        if hw.get("active"):
            try:
                exp = datetime.fromisoformat(hw["expires_at"])
                rem = (exp - datetime.now()).total_seconds()
                st = "⏸" if hw.get("paused") else "▶️"
                text += f"💼 کارگر برداشت/فروش: {st} ({format_time_remaining(rem)})\n"
            except Exception:
                text += f"💼 کارگر برداشت/فروش: فعال\n"
    if "clan" in feats:
        if user.get("clan_id"):
            clan = get_clan(user["clan_id"])
            if clan:
                text += f"🏰 کلن: {clan['name']} (لول {clan['level']})\n"
            else:
                text += f"🏰 کلن: بدون کلن\n"
        else:
            text += f"🏰 کلن: بدون کلن\n"
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
                else:
                    text += f"• زمین {i+1}: 🍅 {fruit}\n"
            elif p["state"] == "harvested":
                text += f"• زمین {i+1}: 📦 {fruit} (برداشت)\n"
            else:
                text += f"• زمین {i+1}: خالی\n"
    text += f"\n🌱 میوه انتخابی: {FRUITS[user['current_fruit']]}\n\n"
    text += f"🍎 **قیمت‌ها (خرید | فروش | XP):**\n"
    for i in get_available_fruits(user):
        bp = get_seed_price(i, user, effects)
        sp = int(PRICES[i][1] * mult * effects["sell_mult"])
        if FRUITS[i] in XP_FROM_SALES:
            xp_min, xp_max = XP_FROM_SALES[FRUITS[i]]
            xp_text = f"{xp_min}" if xp_min == xp_max else f"{xp_min}-{xp_max}"
        else:
            xp_text = "0"
        mark = "✅ " if i == user["current_fruit"] else ""
        text += f"{mark}{FRUITS[i]}: {format_coins(bp)} | {format_coins(sp)} | ⭐{xp_text}\n"
    return text


def get_user_league_rank(user_id, user):
    if user.get("level", 1) >= 7 or user.get("prestige", 0) > 0:
        ensure_user_in_league(user_id, user)
    pk = str(user.get("prestige", 0))
    pn = user.get("current_period", 1)
    per_key = f"period_{pn}"
    data = load_data()
    leagues = data.get("leagues", {})
    if pk not in leagues or per_key not in leagues[pk]:
        return "—"
    members = leagues[pk][per_key].get("members", {})
    if str(user_id) not in members:
        return "—"
    sm = sorted(members.items(), key=lambda x: x[1].get("profit", 0), reverse=True)
    for i, (uid, _) in enumerate(sm, 1):
        if uid == str(user_id):
            return f"#{i} از {len(members)}"
    return "—"


# ==================== ربات ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()


async def check_jail_and_block(message_or_callback, user, uid):
    bank = user.get("bank", {})
    if not bank.get("in_jail"):
        return False
    jail_until_str = bank.get("jail_until")
    if jail_until_str:
        try:
            jail_until = datetime.fromisoformat(jail_until_str)
            if datetime.now() >= jail_until:
                bank["in_jail"] = False
                bank["jail_until"] = None
                bank["jail_work_count"] = 0
                bank["jail_ready_to_pay"] = False
                if bank.get("jail_reason") == "loan_overdue":
                    bank["loan_banned_until"] = (datetime.now() + timedelta(days=7)).isoformat()
                    bank["jail_reason"] = None
                user["bank"] = bank
                user["coins"] = get_initial_coins_for_prestige(user)
                update_user(uid, {"bank": bank, "coins": user["coins"]})
                return False
        except Exception:
            pass
    await show_jail_page(message_or_callback, user, uid)
    return True


async def show_jail_page(message_or_callback, user, uid):
    bank = user.get("bank", {})
    prefix = f"owner_{uid}_"
    jail_until_str = bank.get("jail_until")
    time_left = "?"
    if jail_until_str:
        try:
            jail_until = datetime.fromisoformat(jail_until_str)
            rem = (jail_until - datetime.now()).total_seconds()
            time_left = format_time_remaining(rem)
        except Exception:
            pass
    work_count = bank.get("jail_work_count", 0)
    target = bank.get("jail_target_works", 15)
    ready = bank.get("jail_ready_to_pay", False)
    text = (f"🔒 **زندان**\n\n"
            f"⏰ زمان باقی‌مونده: {time_left}\n"
            f"🔨 کارهای انجام‌شده: **{work_count}/{target}**\n\n")
    if ready:
        text += "✅ کارهای لازم رو انجام دادی! می‌تونی آزاد شی."
    else:
        text += "💡 با کار کردن می‌تونی زودتر آزاد شی."
    kb = InlineKeyboardBuilder()
    if ready:
        kb.button("🎉 آزادی", callback_data=f"{prefix}jail_pay")
    else:
        can_work = True
        last_work_str = bank.get("jail_last_work")
        if last_work_str:
            try:
                last = datetime.fromisoformat(last_work_str)
                if (datetime.now() - last).total_seconds() < JAIL_WORK_INTERVAL_MIN * 60:
                    can_work = False
                    rem = JAIL_WORK_INTERVAL_MIN * 60 - (datetime.now() - last).total_seconds()
                    text += f"\n⏳ کار بعدی: {format_time_remaining(rem)} دیگه"
            except Exception:
                pass
        if can_work:
            kb.button("🔨 کار کردن", callback_data=f"{prefix}jail_work")
        else:
            kb.button("⏳ صبر کن...", callback_data="noop")
    kb.adjust(1)
    if hasattr(message_or_callback, "message"):
        try:
            await message_or_callback.message.edit_text(text, reply_markup=kb.as_markup())
        except Exception:
            try:
                await bot.send_message(uid, text, reply_markup=kb.as_markup())
            except Exception:
                pass
    else:
        try:
            await message_or_callback.reply_text(text, reply_markup=kb.as_markup())
        except Exception:
            try:
                await bot.send_message(uid, text, reply_markup=kb.as_markup())
            except Exception:
                pass


# ==================== ADMIN COMMANDS ====================
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ دسترسی ندارید."); return
    market = get_market_data()
    avg_base = sum(c["base_price"] for c in market["currencies"].values()) / len(market["currencies"])
    text = ("👑 **پنل ادمین**\n\n"
            "**User:**\n"
            "`/user_info <id>` | `/give_coins <id> <amt>`\n"
            "`/set_coins <id> <amt>` | `/set_level <id> <lv>`\n"
            "`/set_xp <id> <xp>` | `/set_prestige <id> <p>`\n"
            "`/give_pet <id> <type>` | `/reset_user <id>`\n"
            "`/ban <id>` / `/unban <id>`\n\n"
            "**System:**\n"
            "`/stats` | `/broadcast <msg>`\n"
            "`/reset_season` | `/reset_league`\n"
            "`/event <buy> <sell> <growth> <xp> <h> <msg>`\n"
            "`/events` | `/end_event`\n"
            "`/giftcode <amt> <all|num> <h> <code>`\n\n"
            "**Market:**\n"
            "`/market profit` | `/market normal` | `/market loss`\n\n"
            f"💰 میانگین پایه: **{avg_base:,.2f}**")
    await message.answer(text)


@dp.message(Command("user_info"))
async def cmd_user_info(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 2:
        await message.answer("❌ `/user_info <user_id>`"); return
    t = get_user(p[1])
    if not t:
        await message.answer("❌ کاربر پیدا نشد."); return
    pet_name = t.get('pet', {}).get('name', '-') if t.get('pet') else '-'
    acc = t.get("bank", {}).get("account_number", "—")
    await message.answer(f"👤 **{p[1]}**\nنام: {t.get('name')}\n💰 {format_coins(t['coins'])}\n"
                          f"📈 لول {t['level']} | XP {t['xp']}\n⭐ پرستیژ {t.get('prestige',0)}\n"
                          f"📦 {get_inv_count(t)}/{get_inv_capacity(t)}\n🏞️ {t.get('max_plots',1)}\n"
                          f"🐾 {pet_name}\n🏦 حساب: `{acc}`")


@dp.message(Command("give_coins"))
async def cmd_give_coins(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 3:
        return
    try:
        amt = int(p[2])
    except Exception:
        return
    t = get_user(p[1])
    if not t:
        await message.answer("❌"); return
    nc = t["coins"] + amt
    update_user(int(p[1]), {"coins": nc})
    update_leaderboard(int(p[1]), t["name"], nc, t["level"], t["prestige"])
    await message.answer(f"✅ +{amt:,} به {t['name']}\n💰 {format_coins(nc)}")


@dp.message(Command("set_coins"))
async def cmd_set_coins(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 3:
        return
    try:
        amt = int(p[2])
    except Exception:
        return
    t = get_user(p[1])
    if not t:
        return
    update_user(int(p[1]), {"coins": amt})
    update_leaderboard(int(p[1]), t["name"], amt, t["level"], t["prestige"])
    await message.answer(f"✅ سکه {t['name']} = {format_coins(amt)}")


@dp.message(Command("set_level"))
async def cmd_set_level(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 3:
        return
    try:
        lv = int(p[2])
    except Exception:
        return
    if lv < 1 or lv > 7:
        await message.answer("❌ لول ۱ تا ۷"); return
    t = get_user(p[1])
    if not t:
        return
    update_user(int(p[1]), {"level": lv})
    await message.answer(f"✅ لول {t['name']} = {lv}")


@dp.message(Command("set_xp"))
async def cmd_set_xp(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 3:
        return
    try:
        xp = int(p[2])
    except Exception:
        return
    t = get_user(p[1])
    if not t:
        return
    update_user(int(p[1]), {"xp": xp})
    await message.answer(f"✅ XP {t['name']} = {xp}")


@dp.message(Command("set_prestige"))
async def cmd_set_prestige(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 3:
        return
    try:
        pr = int(p[2])
    except Exception:
        return
    if pr < 0 or pr > 10:
        return
    t = get_user(p[1])
    if not t:
        return
    m = 1.5 ** pr
    update_user(int(p[1]), {"prestige": pr, "prestige_multiplier": m})
    await message.answer(f"✅ پرستیژ {t['name']} = {pr} ({m:.2f}x)")


@dp.message(Command("give_pet"))
async def cmd_give_pet(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 3:
        await message.answer("❌ phoenix/sell/speed/xp"); return
    t = get_user(p[1])
    if not t:
        return
    ty = p[2].lower()
    if ty == "phoenix":
        update_user(int(p[1]), {"pet": PHOENIX_PET, "phoenix_owned": True})
        await message.answer("✅ ققنوس داده شد.")
    elif ty in ["sell", "speed", "xp"]:
        update_user(int(p[1]), {"pet": {"name": f"Pet-{ty}", "emoji": "🐾", "type": ty, "value": 50}})
        await message.answer(f"✅ پت {ty} داده شد.")
    else:
        await message.answer("❌ phoenix/sell/speed/xp")


@dp.message(Command("reset_user"))
async def cmd_reset_user(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 2:
        return
    t = get_user(p[1])
    if not t:
        return
    nu = create_default_user(int(p[1]))
    nu["name"] = t["name"]
    nu["referral_code"] = t["referral_code"]
    nu["achievements"] = t.get("achievements", [])
    nu["bank"]["account_number"] = t.get("bank", {}).get("account_number") or generate_account_number()
    data = load_data()
    data["users"][p[1]] = nu
    save_data(data)
    await message.answer(f"✅ {t['name']} ریست شد.")


@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 2:
        return
    data = load_data()
    if p[1] not in data.get("banned", []):
        data.setdefault("banned", []).append(p[1])
        save_data(data)
    await message.answer(f"🚫 {p[1]} بن شد.")


@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split()
    if len(p) < 2:
        return
    data = load_data()
    if p[1] in data.get("banned", []):
        data["banned"].remove(p[1])
        save_data(data)
    await message.answer(f"✅ {p[1]} آنبن شد.")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    data = load_data()
    users = data.get("users", {})
    tc = sum(u.get("coins", 0) for u in users.values())
    tp = sum(u.get("prestige", 0) for u in users.values())
    await message.answer(f"📊 **آمار**\n👥 {len(users):,}\n💰 {format_coins(tc)}\n⭐ P {tp}\n"
                          f"🏰 {len(data.get('clans',{}))}\n🚫 {len(data.get('banned',[]))}")


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return
    txt = message.text.replace("/broadcast", "", 1).strip()
    if not txt:
        await message.answer("❌ خالی"); return
    data = load_data()
    s = 0
    f = 0
    for u in data.get("users", {}).keys():
        try:
            await bot.send_message(int(u), f"📢 **اعلان:**\n\n{txt}")
            s += 1
        except Exception:
            f += 1
        await asyncio.sleep(0.05)
    await message.answer(f"✅ {s} | ❌ {f}")


@dp.message(Command("reset_season"))
async def cmd_reset_season(message: Message):
    if not is_admin(message.from_user.id):
        return
    data = load_data()
    data["game_start_time"] = datetime.now().isoformat()
    save_data(data)
    await message.answer("✅ فصل‌ها ریست شد.")


@dp.message(Command("reset_league"))
async def cmd_reset_league(message: Message):
    if not is_admin(message.from_user.id):
        return
    data = load_data()
    data["leagues"] = {}
    save_data(data)
    await message.answer("✅ لیگ‌ها ریست شد.")


@dp.message(Command("event"))
async def cmd_event(message: Message):
    if not is_admin(message.from_user.id):
        return
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
    await message.answer(f"✅ ایونت! Buy×{bm} Sell×{sm} Growth×{gm} XP×{xm} برای {h}h\n📢 {msg}")
    bt = f"🎉 **ایونت!**\n\n{msg}\n\n💰×{bm} 💵×{sm} ⚡×{gm} ⭐×{xm}\n⏰ {h}h"
    for u in data.get("users", {}).keys():
        try:
            await bot.send_message(int(u), bt)
        except Exception:
            pass
        await asyncio.sleep(0.05)


@dp.message(Command("end_event"))
async def cmd_end_event(message: Message):
    if not is_admin(message.from_user.id):
        return
    data = load_data()
    data["active_event"] = None
    save_data(data)
    await message.answer("✅ ایونت پایان یافت.")


@dp.message(Command("events"))
async def cmd_events(message: Message):
    if not is_admin(message.from_user.id):
        return
    ev = get_active_event()
    if not ev:
        await message.answer("ایونت فعالی نیست."); return
    end = datetime.fromisoformat(ev["end_time"])
    rem = end - datetime.now()
    h = int(rem.total_seconds() // 3600)
    m = int((rem.total_seconds() % 3600) // 60)
    await message.answer(f"🎉 **ایونت** ({h}h {m}m)\n💰×{ev['buy_mult']}\n💵×{ev['sell_mult']}\n"
                          f"⚡×{ev['growth_mult']}\n⭐×{ev['xp_mult']}\n📢 {ev['message']}")


@dp.message(Command("giftcode"))
async def cmd_giftcode(message: Message):
    if not is_admin(message.from_user.id):
        return
    p = message.text.split(maxsplit=4)
    if len(p) < 5:
        await message.answer("❌ `/giftcode <amount> <all|num> <hours> <code>`"); return
    try:
        amt = int(p[1]); ls = p[2].lower(); h = float(p[3]); code = p[4].strip()
    except Exception as e:
        await message.answer(f"❌ {e}"); return
    if amt <= 0:
        await message.answer("❌ مقدار باید مثبت باشه."); return
    if not code.startswith("/"):
        await message.answer("❌ کد باید با / شروع بشه."); return
    if len(code) < 2:
        await message.answer("❌ کد کوتاهه."); return
    if ls == "all":
        mu = "all"
    else:
        try:
            mu = int(ls)
        except Exception:
            await message.answer("❌ all یا عدد."); return
    end = datetime.now() + timedelta(hours=h)
    data = load_data()
    data.setdefault("gift_codes", {})[code] = {"amount": amt, "max_users": mu,
                                                "end_time": end.isoformat(),
                                                "used_by": [], "created_at": datetime.now().isoformat()}
    save_data(data)
    lt = "همه" if mu == "all" else f"اول {mu} نفر"
    await message.answer(f"✅ گیفت کد!\n🎟️ `{code}`\n💰 {format_coins(amt)}\n👥 {lt}\n⏰ {h}h")
    bt = f"🎟️ **گیفت کد!**\n\nبرای دریافت {format_coins(amt)} ارسال کن:\n`{code}`\n\n⏰ {h}h | 👥 {lt}"
    for u in data.get("users", {}).keys():
        try:
            await bot.send_message(int(u), bt)
        except Exception:
            pass
        await asyncio.sleep(0.05)


@dp.message(Command("market"))
async def cmd_market(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ دسترسی ندارید."); return
    p = message.text.split()
    if len(p) < 2:
        market = get_market_data()
        avg_base = sum(c["base_price"] for c in market["currencies"].values()) / len(market["currencies"])
        await message.answer(
            f"💹 **مدیریت بازار**\n\n"
            f"💰 میانگین پایه: **{avg_base:,.2f}**\n\n"
            f"`/market profit` — صعودی (+۰.۵٪ در دقیقه)\n"
            f"`/market normal` — توقف\n"
            f"`/market loss` — نزولی (-۰.۰۵٪ در دقیقه)")
        return
    mode = p[1].lower()
    if mode not in ["profit", "normal", "loss"]:
        await message.answer("❌ profit / normal / loss"); return
    data = load_data()
    market = data.get("market", create_default_market())
    market["state"] = mode
    market["last_update"] = datetime.now().isoformat()
    data["market"] = market
    save_data(data)
    avg_base = sum(c["base_price"] for c in market["currencies"].values()) / len(market["currencies"])
    note = {"profit": "📈 صعودی", "loss": "📉 نزولی", "normal": "⏸ توقف"}[mode]
    await message.answer(f"✅ بازار: **{note}**\n💰 میانگین: {avg_base:,.2f}")


# ==================== USER COMMANDS ====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    if is_banned(user_id):
        await message.answer("🚫 شما بن شده‌اید."); return
    check_all_harvests(user_id)
    process_workers(user_id)
    check_period_reset(user_id)
    update_market_prices()
    user = get_user(user_id)
    if not user or user.get("name", "") == "":
        await state.set_state(UserForm.name)
        await message.answer("👤 لطفاً یک نام انتخاب کن (حداقل ۳ کاراکتر، بدون فاصله، تکراری نباشد):")
        return
    update_bank_interest(user_id)
    user = get_user(user_id)
    user = ensure_account_number(user_id, user)
    if await check_jail_and_block(message, user, user_id):
        return
    await show_main_menu(message)


@dp.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    if is_banned(uid):
        return
    check_all_harvests(uid)
    process_workers(uid)
    check_period_reset(uid)
    update_market_prices()
    update_bank_interest(uid)
    user = get_user(uid)
    if not user:
        return
    user = ensure_account_number(uid, user)
    if await check_jail_and_block(message, user, uid):
        return
    await message.answer(build_status_text(user, uid), reply_markup=get_keyboard(uid))


@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"🆔 آیدی عددی شما:\n`{message.from_user.id}`")


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ عملیات لغو شد.", reply_markup=get_keyboard(message.from_user.id))


# ==================== FSM: NAME ====================
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
    acc = generate_account_number()
    bank = create_default_bank()
    bank["account_number"] = acc
    update_user(uid, {"name": name, "bank": bank})
    await state.clear()
    await message.answer(f"✅ نام '{name}' ثبت شد!\n🏦 شماره حساب: `{acc}`")
    await show_main_menu(message)


# ==================== FSM: BANK ====================
@dp.message(UserForm.bank_deposit_amount)
async def bank_deposit_amount_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    txt = message.text.strip().replace(",", "")
    try:
        coins = int(txt)
        if coins <= 0:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ عدد مثبت.", reply_markup=get_keyboard(uid)); return
    if user["coins"] < coins:
        await state.clear()
        await message.answer(f"❌ موجودی: {format_coins(user['coins'])}", reply_markup=get_keyboard(uid)); return
    commission = int(coins * BANK_DEPOSIT_COMMISSION)
    final_amount = coins - commission
    await state.update_data(tr_type="bank_deposit", tr_amount=coins, tr_final=final_amount, tr_commission=commission)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🏦 **تأیید سپرده**\n\n💰 **{format_coins(coins)}**\n"
            f"📊 کمیسیون ۵٪: **{format_coins(commission)}**\n"
            f"✅ واریز: **{format_coins(final_amount)}**\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.bank_withdraw_amount)
async def bank_withdraw_amount_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    bank = user.get("bank", {})
    txt = message.text.strip().replace(",", "")
    if txt.lower() in ["همه", "all"]:
        coins = bank.get("balance", 0)
    else:
        try:
            coins = int(txt)
            if coins <= 0:
                raise ValueError
        except Exception:
            await state.clear()
            await message.answer("❌ عدد مثبت یا «همه».", reply_markup=get_keyboard(uid)); return
    if bank.get("balance", 0) < coins:
        await state.clear()
        await message.answer(f"❌ موجودی بانک: {format_coins(bank.get('balance', 0))}", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="bank_withdraw", tr_amount=coins)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🏦 **تأیید برداشت**\n\n💰 **{format_coins(coins)}**\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.bank_transfer_target)
async def bank_transfer_target_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    acc = message.text.strip()
    if not acc.isdigit() or len(acc) != 6:
        await state.clear()
        await message.answer("❌ شماره حساب باید ۶ رقم باشه.", reply_markup=get_keyboard(uid)); return
    tid, tg = find_user_by_account(acc)
    if not tid:
        await state.clear()
        await message.answer("❌ حساب پیدا نشد.", reply_markup=get_keyboard(uid)); return
    if tid == str(uid):
        await state.clear()
        await message.answer("❌ به خودت نمی‌تونی انتقال بدی.", reply_markup=get_keyboard(uid)); return
    await state.update_data(bank_transfer_target=tid, bank_transfer_target_name=tg.get("name", "?"), bank_transfer_acc=acc)
    await state.set_state(UserForm.bank_transfer_amount)
    await message.answer(f"💰 به **{tg.get('name','?')}** چقدر؟\n\n❌ /cancel")


@dp.message(UserForm.bank_transfer_amount)
async def bank_transfer_amount_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    d = await state.get_data()
    tid = d.get("bank_transfer_target")
    tname = d.get("bank_transfer_target_name")
    acc = d.get("bank_transfer_acc")
    txt = message.text.strip().replace(",", "")
    try:
        coins = int(txt)
        if coins <= 0:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ عدد مثبت.", reply_markup=get_keyboard(uid)); return
    bank = user.get("bank", {})
    if bank.get("balance", 0) < coins:
        await state.clear()
        await message.answer(f"❌ موجودی بانک: {format_coins(bank.get('balance', 0))}", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="bank_transfer", tr_target_id=tid,
                             tr_target_name=tname, tr_amount=coins, tr_acc=acc)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🏦 **تأیید انتقال**\n\n👤 به: **{tname}**\n🆔 `{acc}`\n"
            f"💰 **{format_coins(coins)}**\n"
            f"💼 بعد: {format_coins(bank.get('balance', 0) - coins)}\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.bank_loan_amount)
async def bank_loan_amount_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    bank = user.get("bank", {})
    if bank.get("loan"):
        await state.clear()
        await message.answer("❌ شما وام فعال دارید.", reply_markup=get_keyboard(uid)); return
    banned_until = bank.get("loan_banned_until")
    if banned_until:
        try:
            bu = datetime.fromisoformat(banned_until)
            if datetime.now() < bu:
                rem = (bu - datetime.now()).total_seconds()
                await state.clear()
                await message.answer(f"❌ تا {format_time_remaining(rem)} نمی‌تونی وام بگیری.", reply_markup=get_keyboard(uid)); return
        except Exception:
            pass
    avg = get_avg_balance_24h(user)
    max_loan = int(avg * LOAN_MULTIPLIER)
    txt = message.text.strip().replace(",", "")
    try:
        amount = int(txt)
        if amount <= 0:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ عدد مثبت.", reply_markup=get_keyboard(uid)); return
    if amount > max_loan:
        await state.clear()
        await message.answer(f"❌ حداکثر {format_coins(max_loan)}.", reply_markup=get_keyboard(uid)); return
    if amount < 1000:
        await state.clear()
        await message.answer("❌ حداقل ۱۰۰۰ سکه.", reply_markup=get_keyboard(uid)); return
    await state.update_data(bank_loan_amount=amount)
    await state.set_state(UserForm.bank_loan_hours)
    await message.answer(f"⏰ چند ساعت؟ (۱-۷۲)\n(هر ۳۰ دقیقه ۴۰٪ سود)\n\n❌ /cancel")


@dp.message(UserForm.bank_loan_hours)
async def bank_loan_hours_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 72:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ عدد صحیح بین ۱ تا ۷۲ ساعت.", reply_markup=get_keyboard(uid)); return
    period_end = get_period_end_datetime(user.get("current_period", 1))
    if period_end:
        loan_end = datetime.now() + timedelta(hours=hours)
        if loan_end > period_end:
            await state.clear()
            await message.answer("❌ بعد از اتمام دوره تلاش کنید.", reply_markup=get_keyboard(uid)); return
    d = await state.get_data()
    amount = d.get("bank_loan_amount", 0)
    total_due = calculate_loan_due(amount, hours)
    await state.update_data(tr_type="bank_loan", tr_amount=amount,
                             tr_hours=hours, tr_total_due=total_due)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🏦 **تأیید وام**\n\n💰 **{format_coins(amount)}**\n"
            f"⏰ **{hours} ساعت**\n📈 سود: ۴۰٪ هر ۳۰ دقیقه\n"
            f"💵 بازپرداخت: **{format_coins(total_due)}**\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.confirm_transfer)
async def cancel_on_unexpected(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    await message.answer("❌ **لغو شد.**", reply_markup=get_keyboard(uid))


# ==================== FSM: WORKER ====================
@dp.message(UserForm.worker_plant_hours)
async def wp_hours_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 72:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ ۱-۷۲.", reply_markup=get_keyboard(uid)); return
    d = await state.get_data()
    fruit_idx = d.get("wp_fruit")
    if fruit_idx is None:
        await state.clear(); return
    eff, _ = get_season_effects()
    sp = int(PRICES[fruit_idx][1] * user["prestige_multiplier"] * eff["sell_mult"])
    total_cost = (sp // 3) * hours
    await state.update_data(tr_type="worker_plant", tr_fruit=fruit_idx, tr_hours=hours, tr_cost=total_cost)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🌱 **تأیید کارگر کاشت**\n\n🍎 {FRUITS[fruit_idx]}\n"
            f"⏰ {hours} ساعت\n💰 {format_coins(total_cost)}\n\n"
            f"💵 موجودی: {format_coins(user['coins'])}")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.worker_harvest_hours)
async def wh_hours_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 72:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ ۱-۷۲.", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="worker_harvest", tr_hours=hours)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"💼 **تأیید کارگر برداشت/فروش**\n\n⏰ {hours} ساعت\n"
            f"💰 رایگان\n📊 کمیسیون ۲۰٪\n\n✅ تأیید؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


# ==================== FSM: CLAN ====================
@dp.message(UserForm.clan_name)
async def process_clan_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    name = message.text.strip()
    if len(name) < 3 or len(name) > 20 or " " in name:
        await message.answer("❌ ۳-۲۰ کاراکتر، بدون فاصله:"); return
    data = load_data()
    for c in data.get("clans", {}).values():
        if c.get("name", "").lower() == name.lower():
            await message.answer("❌ تکراریه:"); return
    if user["coins"] < CLAN_CREATE_COST:
        await state.clear()
        await message.answer(f"❌ نیاز به {format_coins(CLAN_CREATE_COST)}", reply_markup=get_keyboard(uid)); return
    cid = f"clan_{uid}"
    create_clan(cid, name, str(uid), user["name"])
    update_user(uid, {"clan_id": cid, "coins": user["coins"] - CLAN_CREATE_COST})
    await state.clear()
    await message.answer(f"🏰 کلن «{name}» ساخته شد!", reply_markup=get_keyboard(uid))


@dp.message(UserForm.clan_search)
async def process_clan_search(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    query = message.text.strip()
    await state.clear()
    if len(query) < 2:
        await message.answer("❌ کوتاه.", reply_markup=get_keyboard(uid)); return
    data = load_data()
    found_clan = None
    found_cid = None
    for cid, c in data.get("clans", {}).items():
        if query.lower() in c.get("name", "").lower():
            found_clan = c
            found_cid = cid
            break
    if not found_clan:
        await message.answer("❌ پیدا نشد.", reply_markup=get_keyboard(uid)); return
    if len(found_clan["members"]) >= CLAN_MAX_MEMBERS.get(found_clan["level"], 10):
        await message.answer("❌ پره.", reply_markup=get_keyboard(uid)); return
    if str(uid) in found_clan["members"]:
        await message.answer("قبلاً عضو.", reply_markup=get_keyboard(uid)); return
    text = (f"🏰 **کلن پیدا شد!**\n\n📛 {found_clan['name']}\n"
            f"📊 لول: {found_clan['level']}\n"
            f"👥 {len(found_clan['members'])}/{CLAN_MAX_MEMBERS.get(found_clan['level'],10)}\n"
            f"👑 {found_clan['leader_name']}\n\n✅ درخواست بدی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ ارسال درخواست", callback_data=f"clan_req_{found_cid}")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.clan_invite)
async def process_clan_invite(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("clan_id"):
        await state.clear(); return
    query = message.text.strip()
    tid, tg = find_user_by_name_or_code(query)
    if not tid:
        await state.clear()
        await message.answer("❌ پیدا نشد.", reply_markup=get_keyboard(uid)); return
    if tg.get("clan_id"):
        await state.clear()
        await message.answer("❌ در کلن دیگه‌ایه.", reply_markup=get_keyboard(uid)); return
    data = load_data()
    clan = data["clans"].get(user["clan_id"])
    if not clan:
        await state.clear(); return
    if len(clan["members"]) >= CLAN_MAX_MEMBERS.get(clan["level"], 10):
        await state.clear()
        await message.answer("❌ پر است!", reply_markup=get_keyboard(uid)); return
    clan["members"].append(str(tid))
    clan["member_names"][str(tid)] = tg["name"]
    save_data(data)
    update_user(int(tid), {"clan_id": user["clan_id"]})
    await state.clear()
    await message.answer(f"✅ {tg['name']} اضافه شد.", reply_markup=get_keyboard(uid))


@dp.message(UserForm.clan_donate)
async def process_clan_donate(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("clan_id"):
        await state.clear(); return
    try:
        amt = int(message.text.strip().replace(",", ""))
        if amt < 10000:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ حداقل ۱۰,۰۰۰.", reply_markup=get_keyboard(uid)); return
    if user["coins"] < amt:
        await state.clear()
        await message.answer(f"❌ موجودی: {format_coins(user['coins'])}", reply_markup=get_keyboard(uid)); return
    clan = get_clan(user["clan_id"])
    if not clan:
        await state.clear(); return
    await state.update_data(tr_type="clan_donate", tr_amount=amt,
                             tr_clan_id=user["clan_id"], tr_clan_name=clan["name"])
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🏰 **تأیید اهدا**\n\n🏰 {clan['name']}\n💰 **{format_coins(amt)}**\n"
            f"💼 بعد: {format_coins(user['coins'] - amt)}\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.clan_chat)
async def process_clan_chat(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user or not user.get("clan_id"):
        await state.clear(); return
    clan = get_clan(user["clan_id"])
    if not clan:
        await state.clear(); return
    msg = f"🏰 **کلن - {user['name']}:**\n\n{message.text}"
    for m in clan["members"]:
        try:
            await bot.send_message(int(m), msg)
        except Exception:
            pass
    await state.clear()
    await message.answer("✅ ارسال شد.", reply_markup=get_keyboard(uid))


# ==================== FSM: MARKET ====================
@dp.message(UserForm.market_buy_amount)
async def market_buy_amount_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    d = await state.get_data()
    cid = d.get("market_buy_cid")
    if not cid or cid not in MARKET_CURRENCIES:
        await state.clear(); return
    txt = message.text.strip().replace(",", "")
    try:
        coins = int(txt)
        if coins <= 0:
            raise ValueError
    except Exception:
        await state.clear()
        await message.answer("❌ عدد مثبت.", reply_markup=get_keyboard(uid)); return
    min_reserve = get_min_coin_reserve(user)
    if user["coins"] - coins < min_reserve:
        await state.clear()
        await message.answer(f"❌ حداقل {format_coins(min_reserve)} بمونه.", reply_markup=get_keyboard(uid)); return
    market = get_market_data()
    price = market["currencies"][cid]["price"]
    amount_currency = coins / price
    cur = MARKET_CURRENCIES[cid]
    await state.update_data(tr_type="market_buy", tr_cid=cid, tr_coins=coins)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"💹 **تأیید خرید {cur['emoji']} {cur['name']}**\n\n"
            f"💰 **{format_coins(coins)}**\n📊 قیمت: {format_market_price(price)}\n"
            f"📦 مقدار: **{amount_currency:.4f}**\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@dp.message(UserForm.market_sell_amount)
async def market_sell_amount_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    if await check_jail_and_block(message, user, uid):
        await state.clear(); return
    d = await state.get_data()
    cid = d.get("market_sell_cid")
    if not cid or cid not in MARKET_CURRENCIES:
        await state.clear(); return
    holdings = user.get("market_holdings", {})
    h = holdings.get(cid)
    if not h or h.get("amount", 0) <= 0:
        await state.clear()
        await message.answer("❌ نداری.", reply_markup=get_keyboard(uid)); return
    txt = message.text.strip().replace(",", "")
    market = get_market_data()
    price = market["currencies"][cid]["price"]
    total_value = h["amount"] * price
    cur = MARKET_CURRENCIES[cid]
    if txt.lower() in ["همه", "all"]:
        sell_amount = h["amount"]
        coins_get = int(sell_amount * price)
        final_all = True
    else:
        try:
            coins_want = int(txt)
            if coins_want <= 0:
                raise ValueError
        except Exception:
            await state.clear()
            await message.answer("❌ عدد مثبت یا «همه».", reply_markup=get_keyboard(uid)); return
        if coins_want > total_value:
            await state.clear()
            await message.answer(f"❌ حداکثر {format_coins(int(total_value))}", reply_markup=get_keyboard(uid)); return
        sell_amount = coins_want / price
        coins_get = coins_want
        final_all = False
    await state.update_data(tr_type="market_sell", tr_cid=cid,
                             tr_sell_amount=sell_amount, tr_coins_get=coins_get, tr_final_all=final_all)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"💹 **تأیید فروش {cur['emoji']} {cur['name']}**\n\n"
            f"📦 **{sell_amount:.4f}**\n💰 دریافت: **{format_coins(coins_get)}**\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


# ==================== PAYMENT ====================
@dp.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery):
    try:
        await query.answer(ok=True)
    except Exception:
        pass


@dp.message(F.successful_payment)
async def on_successful_payment(message: Message, state: FSMContext):
    await state.clear()
    sp = message.successful_payment
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        return
    parts = sp.invoice_payload.split("_")
    try:
        amount = int(parts[1])
    except Exception:
        return
    inv = user.get("inventory", {})
    gm = ""
    if len(parts) >= 4 and parts[3] == "phoenix":
        coins = int(parts[2])
        nc = user["coins"] + coins
        update_user(uid, {"coins": nc, "pet": PHOENIX_PET, "phoenix_owned": True, "pending_purchase": None})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        await message.answer(f"✅ پرداخت!\n🪙 +{format_coins(coins)}\n🦅 ققنوس!", reply_markup=get_keyboard(uid))
        return
    try:
        coins = int(parts[2])
    except Exception:
        return
    nc = user["coins"] + coins
    if amount == 50000:
        fi = random.choice(get_available_fruits(user))
        inv[FRUITS[fi]] = inv.get(FRUITS[fi], 0) + 1
        gm = f"\n🎁 {FRUITS[fi]}"
    elif amount == 100000:
        fi = random.randint(0, len(FRUITS) - 1)
        inv[f"طلایی_{FRUITS[fi]}"] = inv.get(f"طلایی_{FRUITS[fi]}", 0) + 1
        gm = f"\n✨ طلایی {FRUITS[fi]}"
    update_user(uid, {"coins": nc, "inventory": inv, "pending_purchase": None})
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await message.answer(f"✅ پرداخت!\n🪙 +{format_coins(coins)}\n💼 {format_coins(nc)}{gm}", reply_markup=get_keyboard(uid))


# ==================== GIFT CODES ====================
@dp.message(F.text.startswith("/"))
async def handle_gift_codes(message: Message, state: FSMContext):
    text = message.text.strip()
    uid = message.from_user.id
    known = ["/start", "/status", "/admin", "/user_info", "/give_coins",
             "/set_coins", "/set_level", "/set_xp", "/set_prestige", "/give_pet",
             "/reset_user", "/ban", "/unban", "/stats", "/broadcast",
             "/reset_season", "/reset_league", "/event", "/end_event", "/events",
             "/giftcode", "/myid", "/cancel", "/market"]
    if text.split()[0] in known:
        return
    data = load_data()
    codes = data.get("gift_codes", {})
    if text not in codes:
        return
    cd = codes[text]
    try:
        end = datetime.fromisoformat(cd["end_time"])
        if datetime.now() >= end:
            await message.answer("❌ منقضی شده."); return
    except Exception:
        return
    if str(uid) in cd.get("used_by", []):
        await message.answer("❌ قبلاً استفاده کرده‌ای."); return
    mu = cd["max_users"]
    if mu != "all" and len(cd.get("used_by", [])) >= mu:
        await message.answer("❌ ظرفیت پر."); return
    user = get_user(uid)
    if not user:
        await message.answer("❌ اول /start"); return
    amt = cd["amount"]
    nc = user["coins"] + amt
    cd.setdefault("used_by", []).append(str(uid))
    data["users"][str(uid)]["coins"] = nc
    data["gift_codes"][text] = cd
    save_data(data)
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await message.answer(f"🎉 **تبریک!**\n✅ `{text}`\n💰 +{format_coins(amt)}\n💼 {format_coins(nc)}")


# ==================== CLAN ACCEPT/REJECT ====================
@dp.callback_query(F.data.startswith("clan_accept_"))
async def clan_accept(callback: CallbackQuery):
    await safe_answer(callback)
    leader_id = callback.from_user.id
    target_id = callback.data.replace("clan_accept_", "")
    data = load_data()
    req = data.get("clan_requests", {}).get(target_id)
    if not req:
        await safe_edit(callback, "❌ پیدا نشد."); return
    cid = req["clan_id"]
    clan = data["clans"].get(cid)
    if not clan:
        await safe_edit(callback, "❌ کلن."); return
    if clan["leader_id"] != str(leader_id):
        await safe_edit(callback, "❌ لیدر نیستی."); return
    if len(clan["members"]) >= CLAN_MAX_MEMBERS.get(clan["level"], 10):
        await safe_edit(callback, "❌ پره."); return
    target_user = get_user(target_id)
    if not target_user:
        await safe_edit(callback, "❌ کاربر."); return
    if target_user.get("clan_id"):
        await safe_edit(callback, "❌ در کلنه."); return
    clan["members"].append(target_id)
    clan["member_names"][target_id] = target_user["name"]
    data["users"][target_id]["clan_id"] = cid
    del data["clan_requests"][target_id]
    save_data(data)
    await safe_edit(callback, f"✅ **{target_user['name']}** اضافه شد.", reply_markup=get_keyboard(leader_id))
    try:
        await bot.send_message(int(target_id),
            f"🎉 به کلن **{clan['name']}** اضافه شدی!",
            reply_markup=get_keyboard(int(target_id)))
    except Exception:
        pass


@dp.callback_query(F.data.startswith("clan_reject_"))
async def clan_reject(callback: CallbackQuery):
    await safe_answer(callback)
    target_id = callback.data.replace("clan_reject_", "")
    data = load_data()
    req = data.get("clan_requests", {}).pop(target_id, None)
    save_data(data)
    if req:
        await safe_edit(callback, "❌ رد شد.")
        try:
            await bot.send_message(int(target_id),
                f"❌ درخواست رد شد.",
                reply_markup=get_keyboard(int(target_id)))
        except Exception:
            pass


@dp.callback_query(F.data.startswith("clan_req_"))
async def clan_request(callback: CallbackQuery):
    await safe_answer(callback)
    uid = callback.from_user.id
    user = get_user(uid)
    if not user:
        await safe_edit(callback, "❌ اول /start"); return
    cid = callback.data.replace("clan_req_", "")
    data = load_data()
    clan = data["clans"].get(cid)
    if not clan:
        await safe_edit(callback, "❌ پیدا نشد.", reply_markup=get_keyboard(uid)); return
    if len(clan["members"]) >= CLAN_MAX_MEMBERS.get(clan["level"], 10):
        await safe_edit(callback, "❌ پره.", reply_markup=get_keyboard(uid)); return
    if str(uid) in clan["members"]:
        await safe_edit(callback, "قبلاً عضو.", reply_markup=get_keyboard(uid)); return
    if user.get("clan_id"):
        await safe_edit(callback, "❌ در کلن دیگه‌ای.", reply_markup=get_keyboard(uid)); return
    data.setdefault("clan_requests", {})[str(uid)] = {
        "clan_id": cid, "clan_name": clan["name"], "user_name": user["name"],
        "created_at": datetime.now().isoformat()}
    save_data(data)
    await safe_edit(callback, f"✅ درخواست ارسال شد.", reply_markup=get_keyboard(uid))
    leader_id = clan["leader_id"]
    kb = InlineKeyboardBuilder()
    kb.button(f"✅ تأیید {user['name']}", callback_data=f"clan_accept_{uid}")
    kb.button("❌ رد", callback_data=f"clan_reject_{uid}")
    kb.adjust(2)
    try:
        await bot.send_message(int(leader_id),
            f"🏰 **درخواست عضویت**\n\n👤 {user['name']}\n🆔 `{uid}`\n🏰 {clan['name']}",
            reply_markup=kb.as_markup())
    except Exception as e:
        print(f"Error: {e}")


# ==================== CONFIRM YES ====================
@dp.callback_query(F.data == "confirm_yes")
async def confirm_transfer_yes(callback: CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    uid = callback.from_user.id
    user = get_user(uid)
    if not user:
        await state.clear(); return
    d = await state.get_data()
    tr_type = d.get("tr_type")
    if tr_type == "clan_donate":
        amt = d.get("tr_amount")
        cid = d.get("tr_clan_id")
        cname = d.get("tr_clan_name")
        if user["coins"] < amt:
            await state.clear()
            await safe_edit(callback, "❌ کمبود.", reply_markup=get_keyboard(uid)); return
        data = load_data()
        clan = data["clans"].get(cid)
        if not clan:
            await state.clear()
            await safe_edit(callback, "❌ کلن.", reply_markup=get_keyboard(uid)); return
        clan["treasury"] += amt
        data["users"][str(uid)]["coins"] = user["coins"] - amt
        save_data(data)
        await state.clear()
        await safe_edit(callback, f"✅ **اهدا!**\n🏰 {cname}\n💰 {format_coins(amt)}\n🏦 {format_coins(clan['treasury'])}", reply_markup=get_keyboard(uid))
    elif tr_type == "buy_land":
        mp = user.get("max_plots", 1)
        pr = get_land_price(mp)
        if pr is None or user["coins"] < pr:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        plots = user.get("plots", [])
        plots.append({"fruit": 0, "state": "idle", "harvest_time": None})
        update_user(uid, {"coins": user["coins"] - pr, "plots": plots, "max_plots": mp + 1})
        update_leaderboard(uid, user["name"], user["coins"] - pr, user["level"], user["prestige"])
        await state.clear()
        await safe_edit(callback, f"🎉 **زمین {mp+1}!**\n💰 {format_coins(pr)}", reply_markup=get_keyboard(uid))
    elif tr_type == "upgrade":
        key = d.get("tr_key")
        cnt = d.get("tr_count", 0)
        cost = d.get("tr_cost", 0)
        if key not in ["auto_water", "golden_pot", "professional_seeder"] or user["coins"] < cost:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        u = user["upgrades"]
        u[key] = cnt + 1
        update_user(uid, {"coins": user["coins"] - cost, "upgrades": u})
        await state.clear()
        names = {"auto_water": "آبیاری", "golden_pot": "گلدان", "professional_seeder": "بذرپاش"}
        await safe_edit(callback, f"✅ **{names[key]}** → سطح {cnt + 1}\n💰 {format_coins(cost)}", reply_markup=get_keyboard(uid))
    elif tr_type == "prestige":
        nx = user["prestige"] + 1
        p = PRESTIGE_PRICES.get(nx)
        if not p or user["coins"] < p:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        nu = create_default_user(uid)
        nu["name"] = user["name"]
        nu["prestige"] = nx
        nu["prestige_multiplier"] = user["prestige_multiplier"] * 1.5
        nu["referral_code"] = user["referral_code"]
        nu["achievements"] = user.get("achievements", [])
        nu["clan_id"] = user.get("clan_id")
        nu["phoenix_owned"] = user.get("phoenix_owned", False)
        if nu["phoenix_owned"]:
            nu["pet"] = PHOENIX_PET
        nu["last_seen_period"] = get_period_number()
        nu["current_period"] = get_period_number()
        old_acc = user.get("bank", {}).get("account_number")
        if old_acc:
            nu["bank"]["account_number"] = old_acc
        nu["coins"] = get_initial_coins_for_prestige(nu)
        data = load_data()
        data["users"][str(uid)] = nu
        save_data(data)
        update_leaderboard(uid, user["name"], nu["coins"], 1, nx)
        await state.clear()
        await safe_edit(callback, f"⭐ **پرستیژ {nx}!**\nضریب: {nu['prestige_multiplier']:.2f}x\n💰 {format_coins(nu['coins'])}", reply_markup=get_keyboard(uid))
    elif tr_type == "spin":
        et = d.get("tr_egg_type")
        if et not in PET_EGGS:
            await state.clear(); return
        e = PET_EGGS[et]
        if user["coins"] < e["price"] or user.get("phoenix_owned"):
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        np = spin_egg(et)
        if not np:
            await state.clear(); return
        nc = user["coins"] - e["price"]
        update_user(uid, {"coins": nc, "pet": np})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        await state.clear()
        tfa = {"sell": "سود", "speed": "سرعت", "xp": "XP"}
        await safe_edit(callback, f"🥚 **{e['name']}** باز شد!\n\n{np['emoji']} **{np['name']}**\n+{np['value']}٪ {tfa[np['type']]}\n💰 {format_coins(nc)}", reply_markup=get_keyboard(uid))
    elif tr_type == "plant":
        pidx = d.get("tr_plot_idx")
        fidx = d.get("tr_fruit_idx")
        if pidx is None or fidx is None:
            await state.clear(); return
        plots = user.get("plots", [])
        if pidx >= len(plots):
            await state.clear(); return
        eff, _ = get_season_effects()
        bp = get_seed_price(fidx, user, eff)
        if user["coins"] < bp:
            await state.clear()
            await safe_edit(callback, "❌ کمبود.", reply_markup=get_keyboard(uid)); return
        gt = GROWTH_TIMES[fidx] * eff["growth_mult"] * get_growth_mult(user)
        sb = get_pet_effect(user, "speed")
        if sb > 0:
            gt *= (1 - sb / 100)
        ht = datetime.now() + timedelta(minutes=gt)
        plots[pidx] = {"fruit": fidx, "state": "growing", "harvest_time": ht.isoformat()}
        update_user(uid, {"coins": user["coins"] - bp, "plots": plots, "current_fruit": fidx})
        mi = int(gt)
        se = int((gt - mi) * 60)
        await state.clear()
        await safe_edit(callback, f"🌱 {FRUITS[fidx]}!\n⏳ {mi}:{se:02d}", reply_markup=get_keyboard(uid))
    elif tr_type == "worker_plant":
        fi = d.get("tr_fruit")
        h = d.get("tr_hours")
        cost = d.get("tr_cost", 0)
        if fi is None or h is None or user["coins"] < cost:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        expires = datetime.now() + timedelta(hours=h)
        workers = user.get("workers", {})
        workers["planting"] = {"active": True, "fruit": fi, "hours": h, "expires_at": expires.isoformat(), "paused": False, "paused_at": None}
        update_user(uid, {"coins": user["coins"] - cost, "workers": workers})
        update_leaderboard(uid, user["name"], user["coins"] - cost, user["level"], user["prestige"])
        await state.clear()
        await safe_edit(callback, f"✅ **کارگر کاشت!**\n🍎 {FRUITS[fi]}\n⏰ {h}h\n💰 {format_coins(cost)}", reply_markup=get_keyboard(uid))
    elif tr_type == "worker_harvest":
        h = d.get("tr_hours")
        if h is None:
            await state.clear(); return
        expires = datetime.now() + timedelta(hours=h)
        workers = user.get("workers", {})
        workers["harvest_sell"] = {"active": True, "hours": h, "expires_at": expires.isoformat(), "paused": False, "paused_at": None}
        update_user(uid, {"workers": workers})
        await state.clear()
        await safe_edit(callback, f"✅ **کارگر برداشت/فروش!**\n⏰ {h}h", reply_markup=get_keyboard(uid))
    elif tr_type == "fire_worker":
        wk = d.get("tr_wk")
        if wk not in ["planting", "harvest_sell"]:
            await state.clear(); return
        workers = user.get("workers", {})
        workers[wk] = {"active": False, "fruit": None, "hours": 0, "expires_at": None, "paused": False, "paused_at": None}
        update_user(uid, {"workers": workers})
        await state.clear()
        await safe_edit(callback, f"🚪 اخراج شد.", reply_markup=get_keyboard(uid))
    elif tr_type == "clan_disband":
        cid = user.get("clan_id")
        if not cid:
            await state.clear()
            await safe_edit(callback, "❌ کلن نداری.", reply_markup=get_keyboard(uid)); return
        data = load_data()
        clan = data["clans"].get(cid)
        if not clan or clan["leader_id"] != str(uid):
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        for m in clan["members"]:
            if m in data["users"]:
                data["users"][m]["clan_id"] = None
        del data["clans"][cid]
        save_data(data)
        await state.clear()
        await safe_edit(callback, "🗑 منحل شد.", reply_markup=get_keyboard(uid))
    elif tr_type == "clan_leave":
        cid = user.get("clan_id")
        if not cid:
            await state.clear()
            await safe_edit(callback, "❌ کلن نداری.", reply_markup=get_keyboard(uid)); return
        data = load_data()
        clan = data["clans"].get(cid)
        if clan:
            if str(uid) in clan["members"]:
                clan["members"].remove(str(uid))
            clan["member_names"].pop(str(uid), None)
        data["users"][str(uid)]["clan_id"] = None
        save_data(data)
        await state.clear()
        await safe_edit(callback, "🚪 خارج شدی.", reply_markup=get_keyboard(uid))
    elif tr_type == "clan_upgrade":
        cid = user.get("clan_id")
        cost = d.get("tr_cost", 0)
        nx = d.get("tr_next_level", 1)
        if not cid:
            await state.clear(); return
        data = load_data()
        clan = data["clans"].get(cid)
        if not clan or clan["treasury"] < cost:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        clan["level"] = nx
        clan["treasury"] -= cost
        save_data(data)
        await state.clear()
        await safe_edit(callback, f"✅ کلن → لول {nx}!", reply_markup=get_keyboard(uid))
    elif tr_type == "buy_shop":
        amount = d.get("tr_amount")
        coins = d.get("tr_coins")
        if not amount or not coins:
            await state.clear(); return
        await state.clear()
        await safe_edit(callback, "✅ در حال ارسال فاکتور...", reply_markup=get_keyboard(uid))
        try:
            r = amount * 10
            if amount == 70000:
                pl = f"shop_{amount}_{coins}_phoenix"
                ti = "ققنوس"
                de = f"{format_coins(coins)}+🦅"
            else:
                pl = f"shop_{amount}_{coins}"
                ti = format_coins(coins)
                de = f"{amount:,} تومان"
            kwargs = dict(chat_id=uid, title=ti, description=de,
                          payload=pl, provider_token=PROVIDER_TOKEN)
            if HAS_LABELED_PRICE:
                kwargs["prices"] = [LabeledPrice(label=format_coins(coins), amount=r)]
            else:
                kwargs["prices"] = [{"label": format_coins(coins), "amount": r}]
            await bot.send_invoice(**kwargs)
        except Exception as e:
            print(f"Invoice error: {e}")
            try:
                await bot.send_message(uid, f"❌ خطا:\n`{str(e)[:200]}`")
            except Exception:
                pass
    elif tr_type == "market_buy":
        cid = d.get("tr_cid")
        coins = d.get("tr_coins", 0)
        if not cid or cid not in MARKET_CURRENCIES or coins <= 0:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        if user["coins"] < coins:
            await state.clear()
            await safe_edit(callback, "❌ کمبود.", reply_markup=get_keyboard(uid)); return
        market = get_market_data()
        price = market["currencies"][cid]["price"]
        amount_currency = coins / price
        holdings = user.get("market_holdings", {})
        h = holdings.get(cid, {"amount": 0.0, "total_invested": 0})
        h["amount"] = h.get("amount", 0) + amount_currency
        h["total_invested"] = h.get("total_invested", 0) + coins
        holdings[cid] = h
        update_user(uid, {"coins": user["coins"] - coins, "market_holdings": holdings})
        update_leaderboard(uid, user["name"], user["coins"] - coins, user["level"], user["prestige"])
        cur = MARKET_CURRENCIES[cid]
        await state.clear()
        await safe_edit(callback, f"✅ **خرید!**\n\n{cur['emoji']} {cur['name']}\n💰 {format_coins(coins)}\n📦 {amount_currency:.4f}\n📊 {format_market_price(price)}", reply_markup=get_keyboard(uid))
    elif tr_type == "market_sell":
        cid = d.get("tr_cid")
        sell_amount = d.get("tr_sell_amount", 0)
        coins_get = d.get("tr_coins_get", 0)
        final_all = d.get("tr_final_all", False)
        if not cid or cid not in MARKET_CURRENCIES or sell_amount <= 0:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        holdings = user.get("market_holdings", {})
        h = holdings.get(cid)
        if not h or h.get("amount", 0) <= 0:
            await state.clear()
            await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid)); return
        if final_all:
            del holdings[cid]
        else:
            h["amount"] = h.get("amount", 0) - sell_amount
            if h["amount"] <= 0.0001:
                del holdings[cid]
            else:
                holdings[cid] = h
        nc = user["coins"] + coins_get
        update_user(uid, {"coins": nc, "market_holdings": holdings})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        cur = MARKET_CURRENCIES[cid]
        await state.clear()
        await safe_edit(callback, f"✅ **فروش!**\n\n{cur['emoji']} {cur['name']}\n📦 {sell_amount:.4f}\n💰 {format_coins(coins_get)}\n💼 {format_coins(nc)}", reply_markup=get_keyboard(uid))
    elif tr_type == "bank_deposit":
        amt = d.get("tr_amount", 0)
        final_amount = d.get("tr_final", 0)
        commission = d.get("tr_commission", 0)
        if user["coins"] < amt:
            await state.clear()
            await safe_edit(callback, "❌ کمبود.", reply_markup=get_keyboard(uid)); return
        bank = user.get("bank", create_default_bank())
        bank["balance"] = bank.get("balance", 0) + final_amount
        history = bank.get("history", [])
        history.append({"type": "deposit", "amount": final_amount, "commission": commission,
                        "time": datetime.now().isoformat()})
        bank["history"] = history[-50:]
        update_user(uid, {"coins": user["coins"] - amt, "bank": bank})
        update_leaderboard(uid, user["name"], user["coins"] - amt, user["level"], user["prestige"])
        await state.clear()
        await safe_edit(callback, f"✅ **سپرده!**\n💰 {format_coins(amt)}\n📊 کمیسیون: {format_coins(commission)}\n🏦 {format_coins(bank['balance'])}", reply_markup=get_keyboard(uid))
    elif tr_type == "bank_withdraw":
        amt = d.get("tr_amount", 0)
        bank = user.get("bank", create_default_bank())
        if bank.get("balance", 0) < amt:
            await state.clear()
            await safe_edit(callback, "❌ کمبود.", reply_markup=get_keyboard(uid)); return
        bank["balance"] -= amt
        history = bank.get("history", [])
        history.append({"type": "withdraw", "amount": amt, "time": datetime.now().isoformat()})
        bank["history"] = history[-50:]
        nc = user["coins"] + amt
        update_user(uid, {"coins": nc, "bank": bank})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        await state.clear()
        await safe_edit(callback, f"✅ **برداشت!**\n💰 {format_coins(amt)}\n🏦 {format_coins(bank['balance'])}\n💼 {format_coins(nc)}", reply_markup=get_keyboard(uid))
    elif tr_type == "bank_transfer":
        tid = d.get("tr_target_id")
        tname = d.get("tr_target_name")
        amt = d.get("tr_amount", 0)
        acc = d.get("tr_acc", "?")
        target = get_user(tid) if tid else None
        if not target:
            await state.clear()
            await safe_edit(callback, "❌ پیدا نشد.", reply_markup=get_keyboard(uid)); return
        bank = user.get("bank", create_default_bank())
        if bank.get("balance", 0) < amt:
            await state.clear()
            await safe_edit(callback, "❌ کمبود.", reply_markup=get_keyboard(uid)); return
        data = load_data()
        data["users"][str(uid)]["bank"]["balance"] -= amt
        th = data["users"][str(uid)]["bank"].setdefault("history", [])
        th.append({"type": "transfer_out", "amount": amt, "to": tname, "to_acc": acc, "time": datetime.now().isoformat()})
        data["users"][str(uid)]["bank"]["history"] = th[-50:]
        data["users"][tid]["bank"]["balance"] = data["users"][tid].get("bank", {}).get("balance", 0) + amt
        ri = data["users"][tid]["bank"].setdefault("history", [])
        ri.append({"type": "transfer_in", "amount": amt, "from": user.get("name", "?"), "time": datetime.now().isoformat()})
        data["users"][tid]["bank"]["history"] = ri[-50:]
        save_data(data)
        await state.clear()
        await safe_edit(callback, f"✅ **انتقال!**\n👤 {tname}\n💰 {format_coins(amt)}\n🏦 {format_coins(data['users'][str(uid)]['bank']['balance'])}", reply_markup=get_keyboard(uid))
    elif tr_type == "bank_loan":
        amt = d.get("tr_amount", 0)
        hours = d.get("tr_hours", 1)
        total_due = d.get("tr_total_due", 0)
        bank = user.get("bank", create_default_bank())
        if bank.get("loan"):
            await state.clear()
            await safe_edit(callback, "❌ وام فعال.", reply_markup=get_keyboard(uid)); return
        period_end = get_period_end_datetime(user.get("current_period", 1))
        if period_end:
            loan_end = datetime.now() + timedelta(hours=hours)
            if loan_end > period_end:
                await state.clear()
                await safe_edit(callback, "❌ بعد از اتمام دوره.", reply_markup=get_keyboard(uid)); return
        due_time = datetime.now() + timedelta(hours=hours)
        bank["loan"] = {"amount": amt, "total_due": total_due,
                        "start_time": datetime.now().isoformat(),
                        "due_time": due_time.isoformat(), "warning_sent": False}
        nc = user["coins"] + amt
        update_user(uid, {"coins": nc, "bank": bank})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        await state.clear()
        await safe_edit(callback, f"✅ **وام!**\n💰 {format_coins(amt)}\n⏰ {hours}h\n💵 {format_coins(total_due)}", reply_markup=get_keyboard(uid))
    else:
        await state.clear()
        await safe_edit(callback, "❌ خطا.", reply_markup=get_keyboard(uid))


@dp.callback_query(F.data == "confirm_no")
async def confirm_transfer_no(callback: CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    uid = callback.from_user.id
    await state.clear()
    await safe_edit(callback, "❌ **لغو شد.**", reply_markup=get_keyboard(uid))


# ==================== MAIN CALLBACK ====================
@dp.callback_query()
async def on_callback(callback: CallbackQuery, state: FSMContext):
    await safe_answer(callback)
    uid = callback.from_user.id
    if is_banned(uid):
        return
    raw_data = callback.data or ""
    cur_state = await state.get_state()
    if cur_state is not None and raw_data not in ["confirm_yes", "confirm_no"] \
            and not raw_data.startswith("clan_accept_") and not raw_data.startswith("clan_reject_") \
            and not raw_data.startswith("clan_req_") and not raw_data.startswith("market_cid_") \
            and not raw_data.startswith("market_sell_cid_"):
        await state.clear()
    if raw_data.startswith("owner_"):
        parts = raw_data.split("_", 2)
        owner_id = parts[1]
        real_action = parts[2] if len(parts) > 2 else "noop"
        if str(uid) != owner_id:
            try:
                await callback.answer("⛔ این دکمه مال شما نیست!", show_alert=True)
            except Exception:
                pass
            return
        data = real_action
    else:
        if raw_data in ["confirm_yes", "confirm_no"]:
            return
        if raw_data.startswith("clan_accept_") or raw_data.startswith("clan_reject_") or raw_data.startswith("clan_req_"):
            return
        data = raw_data

    check_all_harvests(uid)
    process_workers(uid)
    check_period_reset(uid)
    update_market_prices()
    update_bank_interest(uid)
    user = get_user(uid)
    if not user:
        return

    if user.get("bank", {}).get("in_jail") and not data.startswith("jail_"):
        bank = user.get("bank", {})
        jail_until_str = bank.get("jail_until")
        expired = False
        if jail_until_str:
            try:
                if datetime.now() >= datetime.fromisoformat(jail_until_str):
                    expired = True
            except Exception:
                pass
        if expired:
            bank["in_jail"] = False
            bank["jail_until"] = None
            bank["jail_work_count"] = 0
            bank["jail_ready_to_pay"] = False
            if bank.get("jail_reason") == "loan_overdue":
                bank["loan_banned_until"] = (datetime.now() + timedelta(days=7)).isoformat()
                bank["jail_reason"] = None
            new_coins = get_initial_coins_for_prestige(user)
            update_user(uid, {"bank": bank, "coins": new_coins})
            user = get_user(uid)
        else:
            await show_jail_page(callback, user, uid)
            return

    if data.startswith("market_cid_"):
        cid = data.replace("market_cid_", "")
        if cid not in MARKET_CURRENCIES:
            await safe_edit(callback, "❌", reply_markup=get_keyboard(uid)); return
        cur = MARKET_CURRENCIES[cid]
        market = get_market_data()
        price = market["currencies"][cid]["price"]
        await state.update_data(market_buy_cid=cid)
        await state.set_state(UserForm.market_buy_amount)
        await safe_edit(callback,
            f"💹 **خرید {cur['emoji']} {cur['name']}**\n\n"
            f"📊 قیمت: **{format_market_price(price)}**\n\n"
            f"💰 مقدار **سکه** رو وارد کن:\n❌ /cancel",
            reply_markup=get_keyboard(uid))
        return
    if data.startswith("market_sell_cid_"):
        cid = data.replace("market_sell_cid_", "")
        if cid not in MARKET_CURRENCIES:
            await safe_edit(callback, "❌", reply_markup=get_keyboard(uid)); return
        holdings = user.get("market_holdings", {})
        h = holdings.get(cid)
        if not h or h.get("amount", 0) <= 0:
            await safe_edit(callback, "❌ نداری.", reply_markup=get_keyboard(uid)); return
        cur = MARKET_CURRENCIES[cid]
        market = get_market_data()
        price = market["currencies"][cid]["price"]
        total_value = h["amount"] * price
        await state.update_data(market_sell_cid=cid)
        await state.set_state(UserForm.market_sell_amount)
        await safe_edit(callback,
            f"💹 **فروش {cur['emoji']} {cur['name']}**\n\n"
            f"📦 {h['amount']:.4f}\n"
            f"📊 {format_market_price(price)}\n"
            f"💰 ارزش: **{format_coins(int(total_value))}**\n\n"
            f"مقدار سکه یا «همه»:\n❌ /cancel",
            reply_markup=get_keyboard(uid))
        return

    if data == "jail_work":
        bank = user.get("bank", {})
        last_work_str = bank.get("jail_last_work")
        can_work = True
        if last_work_str:
            try:
                last = datetime.fromisoformat(last_work_str)
                if (datetime.now() - last).total_seconds() < JAIL_WORK_INTERVAL_MIN * 60:
                    can_work = False
            except Exception:
                pass
        if not can_work:
            await safe_edit(callback, "⏳ نه هنوز.", reply_markup=get_keyboard(uid)); return
        bank["jail_work_count"] = bank.get("jail_work_count", 0) + 1
        bank["jail_last_work"] = datetime.now().isoformat()
        if bank["jail_work_count"] >= bank.get("jail_target_works", 15):
            bank["jail_ready_to_pay"] = True
        update_user(uid, {"bank": bank})
        user = get_user(uid)
        await show_jail_page(callback, user, uid)
        return
    if data == "jail_pay":
        bank = user.get("bank", {})
        bank["in_jail"] = False
        bank["jail_until"] = None
        bank["jail_work_count"] = 0
        bank["jail_ready_to_pay"] = False
        bank["loan"] = None
        if bank.get("jail_reason") == "loan_overdue":
            bank["loan_banned_until"] = (datetime.now() + timedelta(days=7)).isoformat()
            bank["jail_reason"] = None
        new_coins = get_initial_coins_for_prestige(user)
        update_user(uid, {"bank": bank, "coins": new_coins})
        user = get_user(uid)
        await safe_edit(callback,
            f"🎉 **آزاد شدی!**\n💰 {format_coins(new_coins)}",
            reply_markup=get_keyboard(uid))
        return
    if data == "pay_loan_yes":
        bank = user.get("bank", {})
        loan = bank.get("loan")
        if not loan:
            await safe_edit(callback, "❌ وام نداری.", reply_markup=get_keyboard(uid)); return
        total_due = loan.get("total_due", 0)
        if user["coins"] < total_due:
            await safe_edit(callback,
                f"❌ کمبود!\n💰 {format_coins(user['coins'])}\n💵 {format_coins(total_due)}",
                reply_markup=get_keyboard(uid)); return
        nc = user["coins"] - total_due
        bank["loan"] = None
        update_user(uid, {"coins": nc, "bank": bank})
        update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
        await safe_edit(callback, f"✅ **وام پرداخت شد!**\n💰 {format_coins(total_due)}\n💼 {format_coins(nc)}", reply_markup=get_keyboard(uid))
        return

    if data == "noop":
        return
    elif data == "status":
        await edit_status(callback, user, uid)
    elif data == "admin_panel":
        await show_admin_panel(callback, uid)
    elif data == "bank_menu":
        user = ensure_account_number(uid, user)
        await show_bank_menu(callback, user, uid)
    elif data == "bank_account":
        user = ensure_account_number(uid, user)
        await show_bank_account(callback, user, uid)
    elif data == "bank_deposit":
        await state.set_state(UserForm.bank_deposit_amount)
        await safe_edit(callback, "💰 مقدار سپرده:\n(۵٪ کمیسیون)\n❌ /cancel", reply_markup=get_keyboard(uid))
    elif data == "bank_withdraw":
        await state.set_state(UserForm.bank_withdraw_amount)
        await safe_edit(callback, "💰 مقدار برداشت (یا «همه»):\n❌ /cancel", reply_markup=get_keyboard(uid))
    elif data == "bank_transfer":
        await state.set_state(UserForm.bank_transfer_target)
        await safe_edit(callback, "🆔 شماره حساب ۶ رقمی:\n❌ /cancel", reply_markup=get_keyboard(uid))
    elif data == "bank_loan":
        await show_bank_loan(callback, user, uid, state)
    elif data == "bank_pay_loan":
        await show_pay_loan(callback, user, uid, state)
    elif data == "bank_history":
        await show_bank_history(callback, user, uid)
    elif data == "market_menu":
        await show_market_menu(callback, user, uid)
    elif data == "market_asset":
        await show_market_asset_menu(callback, user, uid)
    elif data == "lands_menu":
        await show_lands_menu(callback, user, uid)
    elif data == "inventory_menu":
        await show_inventory(callback, user, uid)
    elif data == "buy_prestige":
        await buy_prestige(callback, user, uid, state)
    elif data == "buy_land":
        mp = user.get("max_plots", 1)
        pr = get_land_price(mp)
        if pr is None:
            await safe_edit(callback, "✅ حداکثر داری.", reply_markup=get_keyboard(uid)); return
        if user["coins"] < pr:
            await safe_edit(callback, f"❌ نیاز: {format_coins(pr)}", reply_markup=get_keyboard(uid)); return
        await state.update_data(tr_type="buy_land")
        await state.set_state(UserForm.confirm_transfer)
        text = (f"🏞️ **خرید زمین {mp+1}**\n\n💰 **{format_coins(pr)}**\n"
                f"💼 بعد: {format_coins(user['coins'] - pr)}\n\n⚠️ مطمئنی؟")
        kb = InlineKeyboardBuilder()
        kb.button("✅ تأیید", callback_data="confirm_yes")
        kb.button("❌ لغو", callback_data="confirm_no")
        kb.adjust(2)
        await safe_edit(callback, text, reply_markup=kb.as_markup())
    elif data.startswith("buy_"):
        try:
            idx = int(data.split("_")[1])
        except ValueError:
            return
        await buy_seed_for_plot(callback, user, uid, idx, state)
    elif data.startswith("harvest_"):
        try:
            idx = int(data.split("_")[1])
        except ValueError:
            return
        await harvest_plot(callback, user, uid, idx)
    elif data.startswith("sell_inv_"):
        await sell_from_inventory(callback, user, uid, data.replace("sell_inv_", ""))
    elif data == "sell_all_inv":
        await sell_all_inventory(callback, user, uid)
    elif data.startswith("plant_plot_"):
        p = data.split("_")
        try:
            pidx = int(p[2])
            fidx = int(p[3])
        except (ValueError, IndexError):
            return
        await plant_in_plot(callback, user, uid, pidx, fidx, state)
    elif data.startswith("switch_"):
        try:
            idx = int(data.split("_")[1])
        except ValueError:
            return
        await switch_fruit(callback, user, uid, idx)
    elif data == "leaderboard":
        await show_leaderboard(callback, user, uid)
    elif data == "upgrades":
        await show_upgrades(callback, user, uid)
    elif data.startswith("upgrade_"):
        await buy_upgrade(callback, user, uid, data.replace("upgrade_", ""), state)
    elif data == "daily_orders":
        await show_daily_orders(callback, user, uid)
    elif data == "complete_orders":
        await complete_orders(callback, user, uid)
    elif data == "shop":
        await show_shop(callback, user, uid)
    elif data.startswith("shop_"):
        try:
            amt = int(data.split("_")[1])
        except ValueError:
            return
        await buy_shop(callback, user, uid, amt, state)
    elif data == "worker_menu":
        await show_worker(callback, user, uid)
    elif data == "hire_planting":
        await start_hire_planting(callback, user, uid)
    elif data == "hire_harvest":
        await state.set_state(UserForm.worker_harvest_hours)
        await start_hire_harvest(callback, user, uid)
    elif data == "worker_toggle_planting":
        await toggle_worker_pause(callback, user, uid, "planting")
    elif data == "worker_toggle_harvest":
        await toggle_worker_pause(callback, user, uid, "harvest_sell")
    elif data == "fire_planting":
        await fire_worker(callback, user, uid, "planting", state)
    elif data == "fire_harvest":
        await fire_worker(callback, user, uid, "harvest_sell", state)
    elif data.startswith("wp_fruit_"):
        try:
            fruit_idx = int(data.replace("wp_fruit_", ""))
        except ValueError:
            return
        if fruit_idx not in get_available_fruits(user):
            await safe_edit(callback, "❌", reply_markup=get_keyboard(uid)); return
        await state.update_data(wp_fruit=fruit_idx)
        await state.set_state(UserForm.worker_plant_hours)
        await safe_edit(callback,
            f"🌱 **{FRUITS[fruit_idx]}**\n\n⏰ چند ساعت؟ (۱-۷۲)\n❌ /cancel",
            reply_markup=get_keyboard(uid))
    elif data == "prestige_menu":
        await show_prestige(callback, user, uid)
    elif data == "pet_menu":
        await show_pet_menu(callback, user, uid)
    elif data.startswith("spin_"):
        await do_spin(callback, user, uid, data.replace("spin_", ""), state)
    elif data == "clan_menu":
        await show_clan_menu(callback, user, uid)
    elif data == "clan_create":
        await start_clan_create(callback, user, uid, state)
    elif data == "clan_info":
        await show_clan_info(callback, user, uid)
    elif data == "clan_search":
        await start_clan_search(callback, user, uid, state)
    elif data == "clan_leaderboard":
        await show_clan_leaderboard(callback, user, uid)
    elif data == "clan_invite":
        await state.set_state(UserForm.clan_invite)
        await safe_edit(callback, "👤 نام یا کد:\n❌ /cancel", reply_markup=get_keyboard(uid))
    elif data == "clan_donate":
        await state.set_state(UserForm.clan_donate)
        await safe_edit(callback, "💰 مقدار (حداقل ۱۰,۰۰۰):\n❌ /cancel", reply_markup=get_keyboard(uid))
    elif data == "clan_chat":
        await state.set_state(UserForm.clan_chat)
        await safe_edit(callback, "✉️ پیام:\n❌ /cancel", reply_markup=get_keyboard(uid))
    elif data == "clan_upgrade":
        c = get_clan(user["clan_id"])
        if not c or c["level"] >= 10:
            await safe_edit(callback, "❌ حداکثر!", reply_markup=get_keyboard(uid)); return
        nx = c["level"] + 1
        cost = CLAN_LEVEL_COSTS[nx]
        if c["treasury"] < cost:
            await safe_edit(callback, f"❌ نیاز: {format_coins(cost)}", reply_markup=get_keyboard(uid)); return
        await state.update_data(tr_type="clan_upgrade", tr_cost=cost, tr_next_level=nx)
        await state.set_state(UserForm.confirm_transfer)
        text = (f"⬆️ **ارتقاء کلن**\n\nلول {c['level']} → {nx}\n"
                f"💰 {format_coins(cost)}\n🏦 {format_coins(c['treasury'])}\n\n⚠️ مطمئنی؟")
        kb = InlineKeyboardBuilder()
        kb.button("✅ تأیید", callback_data="confirm_yes")
        kb.button("❌ لغو", callback_data="confirm_no")
        kb.adjust(2)
        await safe_edit(callback, text, reply_markup=kb.as_markup())
    elif data == "clan_leave":
        c = get_clan(user["clan_id"])
        if not c:
            await safe_edit(callback, "❌ نداری.", reply_markup=get_keyboard(uid)); return
        if c["leader_id"] == str(uid):
            await safe_edit(callback, "❌ لیدر نمی‌تونه.", reply_markup=get_keyboard(uid)); return
        await state.update_data(tr_type="clan_leave")
        await state.set_state(UserForm.confirm_transfer)
        text = f"🚪 **خروج از {c['name']}؟**"
        kb = InlineKeyboardBuilder()
        kb.button("✅ تأیید", callback_data="confirm_yes")
        kb.button("❌ لغو", callback_data="confirm_no")
        kb.adjust(2)
        await safe_edit(callback, text, reply_markup=kb.as_markup())
    elif data == "clan_disband":
        c = get_clan(user["clan_id"])
        if not c:
            await safe_edit(callback, "❌ نداری.", reply_markup=get_keyboard(uid)); return
        if c["leader_id"] != str(uid):
            await safe_edit(callback, "❌ فقط لیدر.", reply_markup=get_keyboard(uid)); return
        await state.update_data(tr_type="clan_disband")
        await state.set_state(UserForm.confirm_transfer)
        text = (f"🗑 **منحل کردن کلن**\n\n🏰 {c['name']}\n👥 {len(c['members'])}\n💰 {format_coins(c['treasury'])}\n\n"
                f"⚠️ **قابل بازگشت نیست!**")
        kb = InlineKeyboardBuilder()
        kb.button("✅ تأیید", callback_data="confirm_yes")
        kb.button("❌ لغو", callback_data="confirm_no")
        kb.adjust(2)
        await safe_edit(callback, text, reply_markup=kb.as_markup())
    elif data == "league_menu":
        await show_league_menu(callback, user, uid)
    elif data == "achievements":
        await show_achievements(callback, user, uid)
    elif data == "back":
        await safe_edit(callback, "🔙 منوی اصلی", reply_markup=get_keyboard(uid))


# ==================== WORKER HELPERS ====================
async def toggle_worker_pause(callback, user, uid, wk):
    data = load_data()
    u = data["users"].get(str(uid))
    if not u:
        return
    workers = u.get("workers", {})
    w = workers.get(wk, {})
    if not w.get("active"):
        await safe_edit(callback, "❌ فعال نیست.", reply_markup=get_keyboard(uid)); return
    if w.get("paused"):
        paused_at = w.get("paused_at")
        if paused_at:
            try:
                pause_dur = (datetime.now() - datetime.fromisoformat(paused_at)).total_seconds()
                old_exp = datetime.fromisoformat(w["expires_at"])
                new_exp = old_exp + timedelta(seconds=pause_dur)
                w["expires_at"] = new_exp.isoformat()
            except Exception:
                pass
        w["paused"] = False
        w["paused_at"] = None
    else:
        w["paused"] = True
        w["paused_at"] = datetime.now().isoformat()
    workers[wk] = w
    u["workers"] = workers
    save_data(data)
    status = "متوقف ⏸" if w["paused"] else "فعال ▶️"
    name = "کاشت" if wk == "planting" else "برداشت/فروش"
    await safe_edit(callback, f"✅ کارگر {name} {status}.", reply_markup=get_keyboard(uid))


async def fire_worker(callback, user, uid, wk, state):
    workers = user.get("workers", {})
    w = workers.get(wk, {})
    if not w.get("active"):
        await safe_edit(callback, "❌ فعال نیست.", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="fire_worker", tr_wk=wk)
    await state.set_state(UserForm.confirm_transfer)
    name = "کاشت" if wk == "planting" else "برداشت/فروش"
    text = f"🚪 **اخراج کارگر {name}**\n\n⚠️ پول برنمی‌گرده!\n\nمطمئنی؟"
    kb = InlineKeyboardBuilder()
    kb.button("✅ اخراج", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


# ==================== SHOW FUNCTIONS ====================
async def show_admin_panel(callback, uid):
    if not is_admin(uid):
        return
    kb = InlineKeyboardBuilder()
    kb.button("🔙 بازگشت", callback_data="back")
    kb.adjust(1)
    await safe_edit(callback, "👑 **پنل ادمین**\n\n/admin برای لیست.", reply_markup=kb.as_markup())


async def show_main_menu(message: Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        return
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
        else:
            pt += f"🏞 {i+1}: خالی\n"
    et = ""
    ev = get_active_event()
    if ev:
        et = f"\n🎉 **ایونت فعال!** {ev['message']}\n"
    text = (f"🌾 **مزرعه‌ی {user['name']}**\n\n"
            f"🌤 فصل: {SEASON_FA[season]}\n💰 سکه: {format_coins(user['coins'])}\n"
            f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
            f"⭐ {p}\n📦 انبار: {get_inv_count(user)}/{get_inv_capacity(user)}\n"
            f"{et}\n{pt}\n💡 **دستورات:** وضعیت، پت، بانک، لیدربرد، بازار، انبار، کارگرها، ...")
    await message.answer(text, reply_markup=get_keyboard(uid))


async def edit_status(callback, user, uid):
    await safe_edit(callback, build_status_text(user, uid), reply_markup=get_keyboard(uid))


async def show_bank_menu(callback, user, uid):
    user = ensure_account_number(uid, user)
    bank = user.get("bank", create_default_bank())
    acc = bank.get("account_number") or "—"
    has_loan = bool(bank.get("loan"))
    text = (f"🏦 **بانک**\n\n"
            f"🆔 حساب: `{acc}`\n"
            f"💰 سپرده: **{format_coins(bank.get('balance', 0))}**\n"
            f"💼 کیف: {format_coins(user['coins'])}\n"
            f"📊 سود روزانه: **۱۰٪**\n")
    if has_loan:
        loan = bank["loan"]
        try:
            due = datetime.fromisoformat(loan["due_time"])
            rem = (due - datetime.now()).total_seconds()
            text += f"\n⚠️ **وام:** {format_coins(loan['amount'])}\n"
            text += f"💵 بازپرداخت: {format_coins(loan['total_due'])}\n"
            text += f"⏰ سررسید: {format_time_remaining(rem)}\n"
        except Exception:
            pass
    banned = bank.get("loan_banned_until")
    if banned:
        try:
            bu = datetime.fromisoformat(banned)
            if datetime.now() < bu:
                rem = (bu - datetime.now()).total_seconds()
                text += f"\n🚫 منع وام: {format_time_remaining(rem)}\n"
        except Exception:
            pass
    kb = InlineKeyboardBuilder()
    kb.button("📋 حساب", callback_data=f"owner_{uid}_bank_account")
    kb.button("💰 سپرده‌گذاری", callback_data=f"owner_{uid}_bank_deposit")
    kb.button("💸 برداشت", callback_data=f"owner_{uid}_bank_withdraw")
    kb.button("📤 انتقال", callback_data=f"owner_{uid}_bank_transfer")
    if not has_loan:
        kb.button("🏦 وام", callback_data=f"owner_{uid}_bank_loan")
    else:
        kb.button("💳 پرداخت وام", callback_data=f"owner_{uid}_bank_pay_loan")
    kb.button("📜 تاریخچه", callback_data=f"owner_{uid}_bank_history")
    kb.button("🔙 بازگشت", callback_data=f"owner_{uid}_back")
    kb.adjust(2, 2, 2, 1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_bank_account(callback, user, uid):
    user = ensure_account_number(uid, user)
    bank = user.get("bank", create_default_bank())
    acc = bank.get("account_number") or "—"
    text = (f"📋 **حساب بانکی**\n\n"
            f"🆔 `{acc}`\n"
            f"💰 سپرده: **{format_coins(bank.get('balance', 0))}**\n"
            f"💼 کیف: {format_coins(user['coins'])}\n\n"
            f"💡 این شماره رو به دیگران بده.")
    kb = InlineKeyboardBuilder()
    kb.button("🔙 بازگشت", callback_data=f"owner_{uid}_bank_menu")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_bank_loan(callback, user, uid, state):
    bank = user.get("bank", create_default_bank())
    if bank.get("loan"):
        await safe_edit(callback, "❌ وام فعال داری.", reply_markup=get_keyboard(uid)); return
    banned_until = bank.get("loan_banned_until")
    if banned_until:
        try:
            bu = datetime.fromisoformat(banned_until)
            if datetime.now() < bu:
                rem = (bu - datetime.now()).total_seconds()
                await safe_edit(callback, f"❌ تا {format_time_remaining(rem)} نمی‌تونی وام بگیری.", reply_markup=get_keyboard(uid)); return
        except Exception:
            pass
    avg = get_avg_balance_24h(user)
    max_loan = int(avg * LOAN_MULTIPLIER)
    period_end = get_period_end_datetime(user.get("current_period", 1))
    text = (f"🏦 **درخواست وام**\n\n"
            f"💰 میانگین حساب: {format_coins(avg)}\n"
            f"📊 حداکثر: **{format_coins(max_loan)}**\n\n"
            f"📈 سود: ۴۰٪ هر ۳۰ دقیقه\n\n")
    if period_end:
        rem_period = (period_end - datetime.now()).total_seconds()
        text += f"⏰ پایان دوره: {format_league_time(rem_period)}\n\n"
    text += "💰 مقدار وام:"
    await state.set_state(UserForm.bank_loan_amount)
    await safe_edit(callback, text, reply_markup=get_keyboard(uid))


async def show_pay_loan(callback, user, uid, state):
    bank = user.get("bank", create_default_bank())
    loan = bank.get("loan")
    if not loan:
        await safe_edit(callback, "❌ وام نداری.", reply_markup=get_keyboard(uid)); return
    total_due = loan.get("total_due", 0)
    try:
        due = datetime.fromisoformat(loan["due_time"])
        rem = (due - datetime.now()).total_seconds()
    except Exception:
        rem = 0
    text = (f"💳 **فیش پرداخت وام**\n\n"
            f"💰 **{format_coins(total_due)}**\n"
            f"⏰ {format_time_remaining(rem)}\n\n"
            f"⚠️ اگه پرداخت نکنی، جریمه سنگین!\n\nمطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ پرداخت", callback_data=f"owner_{uid}_pay_loan_yes")
    kb.button("❌ لغو", callback_data=f"owner_{uid}_back")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_bank_history(callback, user, uid):
    bank = user.get("bank", create_default_bank())
    history = bank.get("history", [])
    if not history:
        text = "📜 تاریخچه‌ای نیست."
    else:
        text = "📜 **تاریخچه**\n\n"
        type_fa = {"deposit": "💰 سپرده", "withdraw": "💸 برداشت",
                   "transfer_in": "📥 دریافتی", "transfer_out": "📤 انتقال",
                   "interest": "📈 سود", "loan": "🏦 وام"}
        for h in history[-15:]:
            t = type_fa.get(h.get("type"), h.get("type"))
            text += f"{t} — {format_coins(h.get('amount', 0))}\n"
    kb = InlineKeyboardBuilder()
    kb.button("🔙 بازگشت", callback_data=f"owner_{uid}_bank_menu")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_market_menu(callback, user, uid):
    update_market_prices()
    market = get_market_data()
    prefix = f"owner_{uid}_"
    text = "💹 **بازار کشاورزی**\n\n"
    for cid, cur in MARKET_CURRENCIES.items():
        cdata = market["currencies"][cid]
        price = cdata["price"]
        last_ch = cdata.get("last_change", 0.0)
        if last_ch > 0.01:
            arrow = "📈"
        elif last_ch < -0.01:
            arrow = "📉"
        else:
            arrow = "➡️"
        text += f"{cur['emoji']} **{cur['name']}**: {format_market_price(price)}  {arrow} {last_ch:+.2f}%\n"
    text += "\n💡 روی هر ارز بزن تا بخری."
    kb = InlineKeyboardBuilder()
    kb.button(f"{MARKET_CURRENCIES['millet']['emoji']} ارزن", callback_data=f"{prefix}market_cid_millet")
    kb.button(f"{MARKET_CURRENCIES['alfalfa']['emoji']} یونجه", callback_data=f"{prefix}market_cid_alfalfa")
    kb.button(f"{MARKET_CURRENCIES['wheat']['emoji']} گندم", callback_data=f"{prefix}market_cid_wheat")
    kb.button(f"{MARKET_CURRENCIES['barley']['emoji']} جو", callback_data=f"{prefix}market_cid_barley")
    kb.button(f"{MARKET_CURRENCIES['corn']['emoji']} ذرت", callback_data=f"{prefix}market_cid_corn")
    kb.button("💼 دارایی", callback_data=f"{prefix}market_asset")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(2, 2, 1, 1, 1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_market_asset_menu(callback, user, uid):
    update_market_prices()
    market = get_market_data()
    prefix = f"owner_{uid}_"
    holdings = user.get("market_holdings", {})
    text = "💼 **دارایی بازار**\n\n"
    has_any = False
    buttons = []
    for cid, cur in MARKET_CURRENCIES.items():
        h = holdings.get(cid)
        if not h or h.get("amount", 0) <= 0:
            continue
        has_any = True
        price = market["currencies"][cid]["price"]
        amount = h.get("amount", 0)
        invested = h.get("total_invested", 0)
        current_value = amount * price
        profit = current_value - invested
        profit_pct = (profit / invested * 100) if invested > 0 else 0
        emoji = "📈" if profit > 0.01 else ("📉" if profit < -0.01 else "➡️")
        text += (f"{cur['emoji']} **{cur['name']}**\n"
                 f"   📦 {amount:.4f}\n"
                 f"   💰 ارزش: {format_coins(int(current_value))}\n"
                 f"   💵 سرمایه: {format_coins(int(invested))}\n"
                 f"   {emoji} سود: {format_coins(int(profit))} ({profit_pct:+.2f}%)\n\n")
        buttons.append((cid, cur))
    if not has_any:
        text += "هنوز چیزی نخریدی!"
    kb = InlineKeyboardBuilder()
    for cid, cur in buttons:
        kb.button(f"{cur['emoji']} {cur['name']}", callback_data=f"{prefix}market_sell_cid_{cid}")
    kb.button("🔙 بازار", callback_data=f"{prefix}market_menu")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_lands_menu(callback, user, uid):
    plots = user.get("plots", [])
    mp = user.get("max_plots", 1)
    prefix = f"owner_{uid}_"
    text = f"🏞️ **زمین‌ها ({mp})**\n\n"
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
            kb.button(f"🏞{i+1} 📦", callback_data=f"{prefix}harvest_{i}")
        else:
            text += f"🏞 {i+1}: خالی\n"
            kb.button(f"🏞{i+1} 🌱", callback_data=f"{prefix}buy_{i}")
    np = get_land_price(mp)
    if np:
        text += f"\n🛒 زمین {mp+1}: {format_coins(np)}"
        kb.button(f"🛒 خرید زمین", callback_data=f"{prefix}buy_land")
    kb.button("📦 انبار", callback_data=f"{prefix}inventory_menu")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_inventory(callback, user, uid):
    inv = user.get("inventory", {})
    cap = get_inv_capacity(user)
    c = get_inv_count(user)
    prefix = f"owner_{uid}_"
    text = f"📦 **انبار ({c}/{cap})**\n\n"
    kb = InlineKeyboardBuilder()
    if not inv:
        text += "خالیه!"
    else:
        for fn, cnt in inv.items():
            if fn.startswith("طلایی_"):
                base_name = fn.replace("طلایی_", "")
                text += f"✨ {base_name} (طلایی): {cnt}\n"
                kb.button(f"💰 فروش {base_name} ✨", callback_data=f"{prefix}sell_inv_{fn}")
            else:
                text += f"🍎 {fn}: {cnt}\n"
                kb.button(f"💰 فروش {fn}", callback_data=f"{prefix}sell_inv_{fn}")
        kb.button("💰 فروش همه انبار", callback_data=f"{prefix}sell_all_inv")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def buy_seed_for_plot(callback, user, uid, idx, state):
    plots = user.get("plots", [])
    if idx >= len(plots):
        return
    plot = plots[idx]
    if plot["state"] == "growing":
        await safe_edit(callback, "⏳", reply_markup=get_keyboard(uid)); return
    if plot["state"] == "harvested":
        await safe_edit(callback, "📦 اول برداشت.", reply_markup=get_keyboard(uid)); return
    avail = get_available_fruits(user)
    eff, _ = get_season_effects()
    prefix = f"owner_{uid}_"
    text = f"🌱 **کاشت زمین {idx+1}**\n\n"
    kb = InlineKeyboardBuilder()
    for i in avail:
        bp = get_seed_price(i, user, eff)
        text += f"• {FRUITS[i]}: {format_coins(bp)}\n"
        kb.button(f"🌱 {FRUITS[i]}", callback_data=f"{prefix}plant_plot_{idx}_{i}")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}lands_menu")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def plant_in_plot(callback, user, uid, pidx, fidx, state):
    plots = user.get("plots", [])
    if pidx >= len(plots) or fidx not in get_available_fruits(user):
        return
    eff, _ = get_season_effects()
    bp = get_seed_price(fidx, user, eff)
    if user["coins"] < bp:
        await safe_edit(callback, f"❌ نیاز: {format_coins(bp)}", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="plant", tr_plot_idx=pidx, tr_fruit_idx=fidx)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🌱 **کاشت {FRUITS[fidx]}**\n\n🏞️ زمین {pidx+1}\n"
            f"💰 **{format_coins(bp)}**\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def harvest_plot(callback, user, uid, idx):
    plots = user.get("plots", [])
    if idx >= len(plots):
        return
    p = plots[idx]
    if p["state"] != "harvested":
        await safe_edit(callback, "⏳", reply_markup=get_keyboard(uid)); return
    fn = FRUITS[p.get("fruit", 0)]
    if not add_to_inventory(uid, fn):
        await safe_edit(callback, f"📦 پره! ({get_inv_count(user)}/{get_inv_capacity(user)})", reply_markup=get_keyboard(uid)); return
    plots[idx] = {"fruit": 0, "state": "idle", "harvest_time": None}
    update_user(uid, {"plots": plots})
    await safe_edit(callback, f"📦 {fn} به انبار!", reply_markup=get_keyboard(uid))


def _calc_sale(user, fn, effects):
    """محاسبه فروش یک آیتم از انبار — return (coins, xp, is_golden_chance)"""
    is_golden = fn.startswith("طلایی_")
    real_name = fn.replace("طلایی_", "") if is_golden else fn
    try:
        cf = FRUITS.index(real_name)
    except Exception:
        return None
    bs = int(PRICES[cf][1] * user["prestige_multiplier"] * effects["sell_mult"])
    if is_golden:
        bs *= GOLDEN_MULT
    sp = bs
    pb = get_pet_effect(user, "sell")
    if pb > 0:
        sp += int(bs * pb / 100)
    cb = get_clan_bonus(user)
    if cb > 0:
        sp += int(bs * cb / 100)
    if user["upgrades"].get("golden_pot", 0) > 0:
        sp = int(sp * get_sell_bonus(user))
    g = False
    if not is_golden:
        g = random.random() < effects["golden_chance"]
        if g:
            sp *= 2
    xp = int(xp_from_sale(real_name) * user["prestige_multiplier"] * effects["xp_mult"])
    if is_golden:
        xp *= GOLDEN_MULT
    px = get_pet_effect(user, "xp")
    if px > 0:
        xp += int(xp * px / 100)
    return sp, xp, g, is_golden


async def sell_from_inventory(callback, user, uid, fn):
    inv = user.get("inventory", {})
    if inv.get(fn, 0) < 1:
        await safe_edit(callback, "❌", reply_markup=get_keyboard(uid)); return
    eff, _ = get_season_effects()
    result = _calc_sale(user, fn, eff)
    if not result:
        await safe_edit(callback, "❌", reply_markup=get_keyboard(uid)); return
    sp, xp, g, is_golden = result
    inv[fn] -= 1
    if inv[fn] <= 0:
        del inv[fn]
    nc = user["coins"] + sp
    nx = user["xp"] + xp
    nl = user["level"]
    lu = ""
    xn = xp_needed_for(nl)
    while nx >= xn and nl < 7:
        nx -= xn
        nl += 1
        xn = xp_needed_for(nl)
        lu = f"\n🎉 لول {nl}!"
    update_user(uid, {"coins": nc, "xp": nx, "level": nl, "inventory": inv})
    update_leaderboard(uid, user["name"], nc, nl, user["prestige"])
    upd = get_user(uid)
    update_league_profit(uid, upd, upd["coins"] - upd.get("period_start_coins", 1))
    if is_golden:
        real_name = fn.replace("طلایی_", "")
        await safe_edit(callback,
            f"✨ **{real_name} طلایی فروخته شد!**\n💰 +{format_coins(sp)}\n⭐ +{xp}\n📈 {nl}{lu}",
            reply_markup=get_keyboard(uid))
    else:
        gt = " ✨" if g else ""
        await safe_edit(callback,
            f"✅ {fn}{gt}\n💰 +{format_coins(sp)}\n⭐ +{xp}\n📈 {nl}{lu}",
            reply_markup=get_keyboard(uid))


async def sell_all_inventory(callback, user, uid):
    inv = user.get("inventory", {})
    if not inv:
        await safe_edit(callback, "📦 انبار خالیه!", reply_markup=get_keyboard(uid)); return
    eff, _ = get_season_effects()
    total_coins = 0
    total_xp = 0
    sold_items = {}
    golden_count = 0
    normal_count = 0
    for fn, cnt in list(inv.items()):
        if cnt <= 0:
            continue
        result = _calc_sale(user, fn, eff)
        if not result:
            continue
        sp_one, xp_one, _, is_golden = result
        # همه رو با هم حساب کن (به جای loop)
        total_coins += sp_one * cnt
        total_xp += xp_one * cnt
        if is_golden:
            golden_count += cnt
            real_name = fn.replace("طلایی_", "")
            sold_items[real_name + " ✨"] = sold_items.get(real_name + " ✨", 0) + cnt
        else:
            normal_count += cnt
            sold_items[fn] = sold_items.get(fn, 0) + cnt
    if total_coins == 0 and total_xp == 0:
        await safe_edit(callback, "❌ چیزی برای فروش نیست.", reply_markup=get_keyboard(uid)); return
    inv = {}
    nc = user["coins"] + total_coins
    nx = user["xp"] + total_xp
    nl = user["level"]
    lu = ""
    xn = xp_needed_for(nl)
    while nx >= xn and nl < 7:
        nx -= xn
        nl += 1
        xn = xp_needed_for(nl)
        lu = f"\n🎉 لول {nl}!"
    update_user(uid, {"coins": nc, "xp": nx, "level": nl, "inventory": inv})
    update_leaderboard(uid, user["name"], nc, nl, user["prestige"])
    upd = get_user(uid)
    update_league_profit(uid, upd, upd["coins"] - upd.get("period_start_coins", 1))
    # ساخت خلاصه
    lines = []
    for name, cnt in sold_items.items():
        lines.append(f"• {name}: {cnt}")
    summary = "\n".join(lines[:10])
    if len(lines) > 10:
        summary += f"\n• ... و {len(lines) - 10} آیتم دیگه"
    await safe_edit(callback,
        f"✅ **فروش همه انبار!**\n\n{summary}\n\n"
        f"💰 **+{format_coins(total_coins)}**\n⭐ **+{total_xp} XP**\n📈 لول {nl}{lu}",
        reply_markup=get_keyboard(uid))


async def switch_fruit(callback, user, uid, idx):
    if idx not in get_available_fruits(user):
        await safe_edit(callback, "🔒", reply_markup=get_keyboard(uid)); return
    update_user(uid, {"current_fruit": idx})
    await safe_edit(callback, f"✅ {FRUITS[idx]}", reply_markup=get_keyboard(uid))


async def show_leaderboard(callback, user, uid):
    data = load_data()
    lb = data["leaderboard"][:10]
    text = "🏆 **لیدربرد:**\n\n"
    for i, it in enumerate(lb, 1):
        p = f"⭐{it.get('prestige',0)}" if it.get('prestige', 0) > 0 else ""
        text += f"{i}. {it.get('name','?')} {p} — لول {it.get('level',1)} | {format_coins(it.get('coins',0))}\n"
    if not lb:
        text += "خالیه!"
    await safe_edit(callback, text, reply_markup=get_keyboard(uid))


async def show_upgrades(callback, user, uid):
    u = user["upgrades"]
    w = u.get("auto_water", 0)
    g = u.get("golden_pot", 0)
    s = u.get("professional_seeder", 0)
    c1 = upgrade_price("auto_water", w)
    c2 = upgrade_price("golden_pot", g)
    c3 = upgrade_price("professional_seeder", s)
    mp = user.get("max_plots", 1)
    lp = get_land_price(mp)
    prefix = f"owner_{uid}_"
    text = (f"🔧 **ارتقاء ابزار**\n\n"
            f"💧 **آبیاری خودکار** — هر سطح ۲۰٪ رشد سریع‌تر\n"
            f"   سطح: {w} | ضریب: {get_growth_mult(user):.3f}x\n"
            f"   💰 {format_coins(c1)}\n\n"
            f"🏺 **گلدان طلایی** — هر سطح ۱۰٪ فروش بیشتر\n"
            f"   سطح: {g} | ضریب: {get_sell_bonus(user):.2f}x\n"
            f"   💰 {format_coins(c2)}\n\n"
            f"🌱 **بذرپاش** — هر سطح ۱۰٪ تخفیف (سقف ۵۰٪)\n"
            f"   سطح: {s}\n"
            f"   💰 {format_coins(c3)}\n")
    if lp:
        text += f"\n🏞️ **زمین {mp+1}:** **{format_coins(lp)}**"
    kb = InlineKeyboardBuilder()
    kb.button(f"💧 آبیاری", callback_data=f"{prefix}upgrade_auto_water")
    kb.button(f"🏺 گلدان", callback_data=f"{prefix}upgrade_golden_pot")
    kb.button(f"🌱 بذرپاش", callback_data=f"{prefix}upgrade_professional_seeder")
    if lp:
        kb.button(f"🏞️ خرید زمین", callback_data=f"{prefix}buy_land")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def buy_upgrade(callback, user, uid, key, state):
    if key not in ["auto_water", "golden_pot", "professional_seeder"]:
        return
    cnt = user["upgrades"].get(key, 0)
    cost = upgrade_price(key, cnt)
    if user["coins"] < cost:
        await safe_edit(callback, f"❌ نیاز: {format_coins(cost)}", reply_markup=get_keyboard(uid)); return
    names = {"auto_water": "آبیاری خودکار", "golden_pot": "گلدان طلایی", "professional_seeder": "بذرپاش"}
    await state.update_data(tr_type="upgrade", tr_key=key, tr_count=cnt, tr_cost=cost)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🔧 **تأیید {names[key]}**\n\n"
            f"💰 **{format_coins(cost)}**\n"
            f"📈 از {cnt} → {cnt+1}\n"
            f"💼 بعد: {format_coins(user['coins'] - cost)}\n\n⚠️ مطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


def _generate_missions(user):
    available = get_available_fruits(user)
    mission_fruits = [i for i in available if i < 6]
    if not mission_fruits:
        mission_fruits = [0]
    num_missions = min(3, len(mission_fruits))
    chosen = random.sample(mission_fruits, num_missions)
    orders = []
    for fi in chosen:
        orders.append({"fruit": FRUITS[fi], "count": random.randint(1, 3)})
    return {"orders": orders, "completed": False, "completed_at": None, "next_at": None}


async def show_daily_orders(callback, user, uid):
    do = user.get("daily_orders", {})
    now = datetime.now()
    if do.get("completed"):
        next_at_str = do.get("next_at")
        next_at = None
        if next_at_str:
            try:
                next_at = datetime.fromisoformat(next_at_str)
            except Exception:
                next_at = None
        if next_at and now < next_at:
            rem = (next_at - now).total_seconds()
            await safe_edit(callback,
                f"📦 **ماموریت‌ها تکمیل شده!**\n\n⏰ ماموریت جدید: **{format_time_remaining(rem)}**",
                reply_markup=get_keyboard(uid))
            return
        do = _generate_missions(user)
        update_user(uid, {"daily_orders": do})
        user = get_user(uid)
        do = user["daily_orders"]
    if not do.get("orders"):
        do = _generate_missions(user)
        update_user(uid, {"daily_orders": do})
        user = get_user(uid)
        do = user["daily_orders"]
    orders = do["orders"]
    inv = user.get("inventory", {})
    prefix = f"owner_{uid}_"
    text = "📦 **ماموریت‌های ساعتی**\n\n💡 **×۱.۵ سود بیشتر!**\n\n"
    for i, o in enumerate(orders, 1):
        h = inv.get(o["fruit"], 0)
        text += f"{i}. {o['count']}× {o['fruit']} ({'✅' if h >= o['count'] else '❌'} داری: {h})\n"
    bonus = int(sum(PRICES[FRUITS.index(o["fruit"])][1] * o["count"] * 1.5 for o in orders) * user["prestige_multiplier"])
    text += f"\n💰 پاداش: **{format_coins(bonus)}**"
    kb = InlineKeyboardBuilder()
    kb.button("✅ تکمیل", callback_data=f"{prefix}complete_orders")
    kb.button("🔙 بازگشت", callback_data=f"{prefix}back")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def complete_orders(callback, user, uid):
    do = user.get("daily_orders", {})
    if do.get("completed"):
        await safe_edit(callback, "قبلاً تکمیل!", reply_markup=get_keyboard(uid)); return
    orders = do.get("orders", [])
    if not orders:
        await safe_edit(callback, "❌ ماموریتی نیست.", reply_markup=get_keyboard(uid)); return
    inv = user.get("inventory", {})
    for o in orders:
        if inv.get(o["fruit"], 0) < o["count"]:
            await safe_edit(callback, f"❌ کمبود {o['fruit']}", reply_markup=get_keyboard(uid)); return
    for o in orders:
        inv[o["fruit"]] -= o["count"]
        if inv[o["fruit"]] <= 0:
            del inv[o["fruit"]]
    bonus = int(sum(PRICES[FRUITS.index(o["fruit"])][1] * o["count"] * 1.5 for o in orders) * user["prestige_multiplier"])
    nc = user["coins"] + bonus
    now = datetime.now()
    next_at = (now + timedelta(hours=1)).isoformat()
    update_user(uid, {"coins": nc, "inventory": inv,
                       "daily_orders": {"orders": orders, "completed": True,
                                        "completed_at": now.isoformat(), "next_at": next_at}})
    update_leaderboard(uid, user["name"], nc, user["level"], user["prestige"])
    await safe_edit(callback,
        f"✅ **تکمیل!**\n💰 +{format_coins(bonus)}\n\n⏰ ماموریت جدید: **۱ ساعت دیگه**",
        reply_markup=get_keyboard(uid))


async def show_shop(callback, user, uid):
    lv = user["level"] if user.get("prestige", 0) == 0 else 7
    if lv < 4 and user.get("prestige", 0) == 0:
        await safe_edit(callback, "🔒 لول ۴", reply_markup=get_keyboard(uid)); return
    pr = SHOP_PRICES.get(lv, SHOP_PRICES[7])
    mult = user.get("prestige_multiplier", 1.0)
    prefix = f"owner_{uid}_"
    text = "🛒 **فروشگاه سکه**\n\n"
    if mult > 1.0:
        text += f"⭐ ضریب پرستیژ: **{mult:.2f}x**\n\n"
    for amt, c in pr.items():
        final_coins = int(c * mult)
        text += f"• **{amt:,} تومان** → {format_coins(final_coins)}"
        if amt == 50000:
            text += " + 🎁"
        elif amt == 70000:
            text += " + 🦅"
        elif amt == 100000:
            text += " + ✨"
        text += "\n"
    kb = InlineKeyboardBuilder()
    for amt in pr:
        lbl = f"{amt:,}"
        if amt == 70000:
            lbl += " 🦅"
        elif amt == 100000:
            lbl += " ✨"
        if amt == 70000 and user.get("phoenix_owned"):
            continue
        kb.button(lbl, callback_data=f"{prefix}shop_{amt}")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def buy_shop(callback, user, uid, amount, state):
    lv = user["level"] if user.get("prestige", 0) == 0 else 7
    pr = SHOP_PRICES.get(lv, SHOP_PRICES[7])
    if amount not in pr:
        return
    mult = user.get("prestige_multiplier", 1.0)
    coins = int(pr[amount] * mult)
    await state.update_data(tr_type="buy_shop", tr_amount=amount, tr_coins=coins)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"💳 **خرید سکه**\n\n"
            f"💰 **{amount:,} تومان**\n"
            f"🪙 **{format_coins(coins)}**\n")
    if mult > 1.0:
        text += f"⭐ ضریب: {mult:.2f}x\n"
    if amount == 50000:
        text += "🎁 + بذر\n"
    elif amount == 70000:
        text += "🦅 + ققنوس\n"
    elif amount == 100000:
        text += "✨ + طلایی\n"
    text += "\n⚠️ پرداخت از کیف بله."
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_worker(callback, user, uid):
    workers = user.get("workers", {})
    pw = workers.get("planting", {})
    hw = workers.get("harvest_sell", {})
    prefix = f"owner_{uid}_"
    text = "👷 **کارگرها**\n\n"
    if pw.get("active"):
        try:
            exp = datetime.fromisoformat(pw["expires_at"])
            rem = (exp - datetime.now()).total_seconds()
            fname = FRUITS[pw["fruit"]] if pw.get("fruit") is not None else "?"
            st = "⏸" if pw.get("paused") else "✅"
            text += f"🌱 **کاشت:** {st} ({fname})\n   ⏰ {format_time_remaining(rem)}\n\n"
        except Exception:
            text += f"🌱 **کاشت:** ✅\n\n"
    else:
        text += f"🌱 **کاشت:** ❌\n\n"
    if hw.get("active"):
        try:
            exp = datetime.fromisoformat(hw["expires_at"])
            rem = (exp - datetime.now()).total_seconds()
            st = "⏸" if hw.get("paused") else "✅"
            text += f"💼 **برداشت/فروش:** {st}\n   ⏰ {format_time_remaining(rem)}\n\n"
        except Exception:
            text += f"💼 **برداشت/فروش:** ✅\n\n"
    else:
        text += f"💼 **برداشت/فروش:** ❌\n\n"
    text += ("💡 **کاشت:** قیمت = ۱/۳ قیمت فروش × ساعت.\n"
             "💡 **برداشت/فروش:** رایگان، ۲۰٪ کمیسیون.")
    kb = InlineKeyboardBuilder()
    if not pw.get("active"):
        kb.button("🌱 اجاره کارگر کاشت", callback_data=f"{prefix}hire_planting")
    else:
        lbl = "▶️ ادامه کاشت" if pw.get("paused") else "⏸ توقف کاشت"
        kb.button(lbl, callback_data=f"{prefix}worker_toggle_planting")
        kb.button("🚪 اخراج کاشت", callback_data=f"{prefix}fire_planting")
    if not hw.get("active"):
        kb.button("💼 اجاره کارگر برداشت/فروش", callback_data=f"{prefix}hire_harvest")
    else:
        lbl = "▶️ ادامه برداشت" if hw.get("paused") else "⏸ توقف برداشت"
        kb.button(lbl, callback_data=f"{prefix}worker_toggle_harvest")
        kb.button("🚪 اخراج برداشت", callback_data=f"{prefix}fire_harvest")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def start_hire_planting(callback, user, uid):
    available_planting = [i for i in get_available_fruits(user) if i >= 2]
    prefix = f"owner_{uid}_"
    if not available_planting:
        await safe_edit(callback, "❌ حداقل لول ۳.", reply_markup=get_keyboard(uid)); return
    eff, _ = get_season_effects()
    text = "🌱 **کارگر کاشت**\n\n🍎 میوه:\n\n"
    kb = InlineKeyboardBuilder()
    for i in available_planting:
        sp = int(PRICES[i][1] * user["prestige_multiplier"] * eff["sell_mult"])
        price_per_hour = sp // 3
        text += f"• {FRUITS[i]}: {format_coins(price_per_hour)} / ساعت\n"
        kb.button(f"🌱 {FRUITS[i]}", callback_data=f"{prefix}wp_fruit_{i}")
    kb.button("🔙", callback_data=f"{prefix}worker_menu")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def start_hire_harvest(callback, user, uid):
    text = ("💼 **کارگر برداشت و فروش**\n\n"
            "📌 کارها:\n• برداشت → انبار\n• فروش انبار (۲۰٪ کمیسیون)\n\n"
            "💰 رایگان\n\n"
            "⏰ چند ساعت؟ (۱-۷۲)\n❌ /cancel")
    await safe_edit(callback, text, reply_markup=get_keyboard(uid))


# ==================== CLAN ====================
async def show_clan_menu(callback, user, uid):
    prefix = f"owner_{uid}_"
    clan_id = user.get("clan_id")
    if clan_id and not get_clan(clan_id):
        update_user(uid, {"clan_id": None})
        user = get_user(uid)
        clan_id = None
    if not clan_id:
        text = (f"🏰 **بدون کلن**\n\n💰 ساخت: {format_coins(CLAN_CREATE_COST)}\n\n"
                f"💡 می‌تونی بسازی یا عضو شی.")
        kb = InlineKeyboardBuilder()
        kb.button("🏰 ساخت کلن", callback_data=f"{prefix}clan_create")
        kb.button("🔍 جستجو", callback_data=f"{prefix}clan_search")
        kb.button("🏆 رتبه‌بندی", callback_data=f"{prefix}clan_leaderboard")
        kb.button("🔙", callback_data=f"{prefix}back")
        kb.adjust(2, 1, 1)
        await safe_edit(callback, text, reply_markup=kb.as_markup())
    else:
        await show_clan_info(callback, user, uid)


async def show_clan_info(callback, user, uid):
    c = get_clan(user["clan_id"])
    prefix = f"owner_{uid}_"
    if not c:
        update_user(uid, {"clan_id": None})
        user = get_user(uid)
        await show_clan_menu(callback, user, uid); return
    il = c["leader_id"] == str(uid)
    text = (f"🏰 **{c['name']}**\n\n"
            f"📊 لول: {c['level']} | پاداش: +{c['level']*CLAN_BONUS_PER_LEVEL}٪\n"
            f"💰 خزانه: {format_coins(c['treasury'])}\n"
            f"👥 {len(c['members'])}/{CLAN_MAX_MEMBERS.get(c['level'],10)}\n"
            f"👑 {c['leader_name']}\n\n👥 **اعضا:**\n")
    for m in c["members"][:20]:
        text += f"• {c['member_names'].get(m, '?')}\n"
    kb = InlineKeyboardBuilder()
    kb.button("👤 دعوت", callback_data=f"{prefix}clan_invite")
    kb.button("💰 اهدا", callback_data=f"{prefix}clan_donate")
    kb.button("✉️ چت", callback_data=f"{prefix}clan_chat")
    if il:
        kb.button("⬆️ ارتقاء", callback_data=f"{prefix}clan_upgrade")
        kb.button("🗑 منحل", callback_data=f"{prefix}clan_disband")
    else:
        kb.button("🚪 خروج", callback_data=f"{prefix}clan_leave")
    kb.button("🏆 رتبه‌بندی", callback_data=f"{prefix}clan_leaderboard")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(2, 2, 2, 1, 1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_clan_leaderboard(callback, user, uid):
    prefix = f"owner_{uid}_"
    clans = get_clan_leaderboard()
    if not clans:
        text = "🏆 **رتبه‌بندی**\n\nهنوز کلنی نیست!"
    else:
        text = "🏆 **رتبه‌بندی کلن‌ها**\n\n"
        for i, (cid, c) in enumerate(clans, 1):
            medal = "🥇 " if i == 1 else ("🥈 " if i == 2 else ("🥉 " if i == 3 else ""))
            text += (f"{medal}{i}. **{c['name']}**\n"
                     f"   📊 {c['level']} | 💰 {format_coins(c['treasury'])}\n")
    kb = InlineKeyboardBuilder()
    kb.button("🔙", callback_data=f"{prefix}clan_menu")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def start_clan_create(callback, user, uid, state):
    if user["coins"] < CLAN_CREATE_COST:
        await safe_edit(callback, f"❌ نیاز: {format_coins(CLAN_CREATE_COST)}", reply_markup=get_keyboard(uid)); return
    await state.set_state(UserForm.clan_name)
    await safe_edit(callback, "🏰 نام کلن (۳-۲۰ کاراکتر، بدون فاصله):\n❌ /cancel", reply_markup=get_keyboard(uid))


async def start_clan_search(callback, user, uid, state):
    await state.set_state(UserForm.clan_search)
    await safe_edit(callback, "🔍 **جستجو**\n\nنام کلن:\n❌ /cancel", reply_markup=get_keyboard(uid))


# ==================== LEAGUE/PRESTIGE/PET/ACH ====================
async def show_league_menu(callback, user, uid):
    pn = user.get("current_period", 1)
    lg = LEAGUE_FA.get(user.get("prestige", 0), "?")
    profit = user["coins"] - user.get("period_start_coins", 1)
    rank = get_user_league_rank(uid, user)
    prefix = f"owner_{uid}_"
    period_end = get_period_end_datetime(pn)
    time_text = "?"
    if period_end:
        rem = (period_end - datetime.now()).total_seconds()
        time_text = format_league_time(rem) if rem > 0 else "به‌زودی..."
    text = (f"🏅 **لیگ {lg}** — دوره {pn}\n\n"
            f"💵 سود: {format_coins(profit)}\n"
            f"📊 رتبه: {rank}\n\n"
            f"⏰ **دوره {pn}: {time_text} دیگر به اتمام می‌رسد.**\n\n"
            f"🏆 ۱۰٪ برتر افتخار می‌گیرن!")
    kb = InlineKeyboardBuilder()
    kb.button("🎖️ افتخارات", callback_data=f"{prefix}achievements")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_prestige(callback, user, uid):
    if user["level"] < 7:
        await safe_edit(callback, "🔒 لول ۷", reply_markup=get_keyboard(uid)); return
    if user["prestige"] >= 10:
        await safe_edit(callback, "⭐ حداکثر!", reply_markup=get_keyboard(uid)); return
    nx = user["prestige"] + 1
    p = PRESTIGE_PRICES[nx]
    prefix = f"owner_{uid}_"
    text = f"⭐ **پرستیژ {nx}**\n{format_coins(p)}\nضریب: {user['prestige_multiplier']*1.5:.2f}x"
    kb = InlineKeyboardBuilder()
    kb.button(f"⭐ ({format_coins(p)})", callback_data=f"{prefix}buy_prestige")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(1)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def buy_prestige(callback, user, uid, state):
    if user["prestige"] >= 10:
        return
    nx = user["prestige"] + 1
    p = PRESTIGE_PRICES[nx]
    if user["coins"] < p:
        await safe_edit(callback, f"❌ نیاز: {format_coins(p)}", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="prestige")
    await state.set_state(UserForm.confirm_transfer)
    text = (f"⭐ **پرستیژ {nx}**\n\n💰 **{format_coins(p)}**\n"
            f"⭐ ضریب جدید: **{user['prestige_multiplier']*1.5:.2f}x**\n\n"
            f"⚠️ **ریست:** سکه، لول، XP، انبار، زمین‌ها، ارتقاءها\n"
            f"✅ **باقی:** نام، پرستیژ، کلن، ققنوس، افتخارات، حساب بانکی\n\nمطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


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
    else:
        pt = "ندارد"
    if user.get("phoenix_owned"):
        text = f"🐾 {pt}\n\n⚠️ ققنوس داری."
        kb = InlineKeyboardBuilder()
        kb.button("🔙", callback_data=f"{prefix}back")
        await safe_edit(callback, text, reply_markup=kb.as_markup()); return
    text = f"🐾 {pt}\n\n🥚 **تخم‌ها:**\n"
    for k, e in PET_EGGS.items():
        text += f"• {e['name']}: {format_coins(e['price'])}\n"
    text += "\n⚠️ اسپین پت قبلی رو نابود می‌کنه!"
    kb = InlineKeyboardBuilder()
    for k in PET_EGGS:
        s = {"common":"معمولی","uncommon":"غیرمعمولی","rare":"کمیاب","epic":"حماسی","legendary":"افسانه‌ای","mythic":"اساطیری"}[k]
        kb.button(s, callback_data=f"{prefix}spin_{k}")
    kb.button("🔙", callback_data=f"{prefix}back")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def do_spin(callback, user, uid, et, state):
    if user.get("phoenix_owned"):
        await safe_edit(callback, "🦅 ققنوس داری!", reply_markup=get_keyboard(uid)); return
    if et not in PET_EGGS:
        return
    e = PET_EGGS[et]
    if user["coins"] < e["price"]:
        await safe_edit(callback, f"❌ نیاز: {format_coins(e['price'])}", reply_markup=get_keyboard(uid)); return
    await state.update_data(tr_type="spin", tr_egg_type=et)
    await state.set_state(UserForm.confirm_transfer)
    text = (f"🥚 **باز کردن {e['name']}**\n\n"
            f"💰 **{format_coins(e['price'])}**\n\n"
            f"⚠️ پت فعلی از بین می‌ره!\n🎁 یک پت رندوم.\n\nمطمئنی؟")
    kb = InlineKeyboardBuilder()
    kb.button("✅ تأیید", callback_data="confirm_yes")
    kb.button("❌ لغو", callback_data="confirm_no")
    kb.adjust(2)
    await safe_edit(callback, text, reply_markup=kb.as_markup())


async def show_achievements(callback, user, uid):
    a = user.get("achievements", [])
    if not a:
        text = "🎖️ هنوز افتخاری نداری!"
    else:
        text = f"🎖️ **افتخارات ({len(a)})**\n\n"
        for x in a[-20:]:
            ln = LEAGUE_FA.get(x.get("league", 0), "?")
            t = x.get("type")
            if t == "top_percent":
                text += f"🏅 {x['percent']}٪ برتر دوره {x['period']}، لیگ {ln}\n"
            elif t == "lone_eagle":
                text += f"🦅 عقاب تنهای {x['rank']} دوره {x['period']}، لیگ {ln}\n"
            elif t == "medal_gold":
                text += f"🥇 طلای دوره {x['period']}، لیگ {ln}\n"
            elif t == "medal_silver":
                text += f"🥈 نقره دوره {x['period']}، لیگ {ln}\n"
            elif t == "medal_bronze":
                text += f"🥉 برنز دوره {x['period']}، لیگ {ln}\n"
    await safe_edit(callback, text, reply_markup=get_keyboard(uid))


# ==================== TEXT COMMANDS (آخرین هندلر message) ====================
@dp.message()
async def handle_text_commands(message: Message, state: FSMContext):
    if not message.text:
        return
    txt = message.text.strip()
    if txt.startswith("/"):
        return
    cur_state = await state.get_state()
    if cur_state is not None:
        return
    uid = message.from_user.id
    user = get_user(uid)
    if user and user.get("bank", {}).get("in_jail"):
        check_all_harvests(uid)
        process_workers(uid)
        check_period_reset(uid)
        user = get_user(uid)
        await check_jail_and_block(message, user, uid)
        return
    if txt not in TEXT_COMMANDS:
        return
    action = TEXT_COMMANDS[txt]
    if is_banned(uid):
        return
    check_all_harvests(uid)
    process_workers(uid)
    check_period_reset(uid)
    update_market_prices()
    update_bank_interest(uid)
    user = get_user(uid)
    if not user:
        return
    if await check_jail_and_block(message, user, uid):
        return
    if action == "buy_seed_text":
        if user["max_plots"] == 1:
            fake = FakeCallback(message, data=f"owner_{uid}_buy_0")
            await buy_seed_for_plot(fake, user, uid, 0, state)
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


# ==================== BACKGROUND LOOPS ====================
async def bank_interest_loop():
    await asyncio.sleep(60)
    while True:
        try:
            await asyncio.to_thread(apply_interest_all_users)
        except Exception as e:
            print(f"❌ Interest: {e}")
        await asyncio.sleep(3600)


async def loan_check_loop():
    await asyncio.sleep(90)
    while True:
        try:
            notifications = await asyncio.to_thread(check_overdue_loans)
            for uid, text in notifications:
                try:
                    await bot.send_message(int(uid), text)
                except Exception:
                    pass
        except Exception as e:
            print(f"❌ Loan: {e}")
        await asyncio.sleep(300)


async def trim_loop():
    await asyncio.sleep(300)
    while True:
        try:
            await asyncio.to_thread(trim_old_data)
        except Exception as e:
            print(f"❌ Trim: {e}")
        await asyncio.sleep(3600)


# ==================== MAIN ====================
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print(f"🤖 ربات روشن شد... Admin IDs: {ADMIN_IDS}")

    load_data()
    print("✅ Data loaded")

    async def stop_delay():
        await asyncio.sleep(340 * 60)
        print("⏰ توقف...")
        try:
            if _DATA_DIRTY:
                await asyncio.to_thread(_write_to_disk)
            await asyncio.to_thread(merge_to_single_file)
        except Exception as e:
            print(f"Final merge error: {e}")
        try:
            await dp.stop_polling()
        except Exception:
            pass

    asyncio.create_task(stop_delay())
    asyncio.create_task(saver_loop())
    asyncio.create_task(sync_to_single_loop())
    asyncio.create_task(bank_interest_loop())
    asyncio.create_task(loan_check_loop())
    asyncio.create_task(trim_loop())

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"متوقف: {e}")
        try:
            if _DATA_DIRTY:
                await asyncio.to_thread(_write_to_disk)
            await asyncio.to_thread(merge_to_single_file)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
