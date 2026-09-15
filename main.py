import json
import os
import random
import shutil
import asyncio
import logging
import sys
from datetime import datetime
from filelock import FileLock

from baleio import Bot, Dispatcher, md
from baleio.client.default import DefaultBotProperties
from baleio.enums import ParseMode
from baleio.filters import Command, CommandStart
from baleio.fsm import FSMContext, State, StatesGroup
from baleio.types import Message, CallbackQuery
from baleio.utils import InlineKeyboardBuilder

# ==================== تنظیمات ====================
TOKEN = os.getenv("BOT_TOKEN", "1256580489:2CcrEtsKwjKFnuBajGRSMG-dx6BeJiujhr0")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "WALLET-TEST-1111111111111111")
DATA_FILE = "data.json"
BACKUP_FILE = "data_backup.json"
LOCK_FILE = "data.lock"
lock = FileLock(LOCK_FILE, timeout=10)

# ==================== میوه‌ها ====================
FRUITS = ["توت‌فرنگی", "گوجه", "سیب", "پرتقال", "نارگیل", "آناناس", "میوه اژدها"]
PRICES = [
    (1, 3), (15, 38), (304, 760), (9120, 22800),
    (456000, 1140000), (27360000, 68400000), (2052000000, 5130000000)
]
GROWTH_TIMES = [1, 2.5, 4, 5.5, 7, 8.5, 10]

# ==================== XP و لول ====================
XP_REQUIRED = {1: 5, 2: 5, 3: 30, 4: 75, 5: 250, 6: 1000}
XP_FROM_SALES = {
    "توت‌فرنگی": (1, 1), "گوجه": (2, 3), "سیب": (4, 6),
    "پرتقال": (8, 12), "نارگیل": (20, 30), "آناناس": (35, 65)
}

LEVEL_UNLOCKS = {
    1: {"fruits": [0], "features": ["status"]},
    2: {"fruits": [0, 1], "features": ["status", "leaderboard"]},
    3: {"fruits": [0, 1, 2], "features": ["status", "leaderboard", "upgrades"]},
    4: {"fruits": [0, 1, 2, 3], "features": ["status", "leaderboard", "upgrades", "daily_orders", "shop"]},
    5: {"fruits": [0, 1, 2, 3, 4], "features": ["status", "leaderboard", "upgrades", "daily_orders", "shop", "worker"]},
    6: {"fruits": [0, 1, 2, 3, 4, 5], "features": ["status", "leaderboard", "upgrades", "daily_orders", "shop", "worker", "gift"]},
    7: {"fruits": [0, 1, 2, 3, 4, 5, 6], "features": ["status", "leaderboard", "upgrades", "daily_orders", "shop", "worker", "gift", "prestige"]},
}

PRESTIGE_PRICES = {
    1: 50_000_000_000, 2: 100_000_000_000, 3: 200_000_000_000,
    4: 500_000_000_000, 5: 725_000_000_000, 6: 1_000_000_000_000,
    7: 1_500_000_000_000, 8: 2_500_000_000_000,
    9: 5_000_000_000_000, 10: 10_000_000_000_000,
}

SHOP_PRICES = {
    4: {5000: 114000, 10000: 228000, 20000: 456000, 50000: 1140000, 100000: 2280000},
    5: {5000: 5700000, 10000: 11400000, 20000: 22800000, 50000: 57000000, 100000: 114000000},
    6: {5000: 342000000, 10000: 684000000, 20000: 1368000000, 50000: 3420000000, 100000: 6840000000},
    7: {5000: 25650000000, 10000: 51300000000, 20000: 102600000000, 50000: 256500000000, 100000: 513000000000},
}

SEASON_CYCLE = ["spring", "summer", "autumn", "winter"]
SEASON_DURATION_MIN = 45
SEASON_FA = {"spring": "🌸 بهار", "summer": "☀️ تابستان", "autumn": "🍂 پاییز", "winter": "❄️ زمستان"}

# ==================== FSM ====================
class UserForm(StatesGroup):
    name = State()
    gift_target = State()
    gift_amount = State()

# ==================== دیتابیس ====================
def create_default_data():
    return {
        "game_start_time": datetime.now().isoformat(),
        "users": {},
        "leaderboard": []
    }

def create_default_user(user_id):
    return {
        "name": "", "level": 1, "xp": 0, "coins": 1,
        "state": "idle", "current_fruit": 0, "inventory": [],
        "upgrades": {"auto_water": 0, "golden_pot": 0, "professional_seeder": 0},
        "worker": {"level": 1, "active": False},
        "daily_orders": {"date": "", "orders": [], "completed": False},
        "prestige": 0, "prestige_multiplier": 1.0,
        "gifts_given": 0, "gifts_received": 0,
        "referral_code": f"REF{user_id}{random.randint(100,999)}",
    }

def _ensure_keys(data):
    """اطمینان از وجود کلیدهای ضروری در داده"""
    if not isinstance(data, dict):
        return create_default_data()
    if "users" not in data:
        data["users"] = {}
    if "leaderboard" not in data:
        data["leaderboard"] = []
    if "game_start_time" not in data:
        data["game_start_time"] = datetime.now().isoformat()
    return data

def load_data():
    with lock:
        if not os.path.exists(DATA_FILE):
            if os.path.exists(BACKUP_FILE):
                try:
                    shutil.copy(BACKUP_FILE, DATA_FILE)
                except Exception:
                    pass
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
                except Exception:
                    pass
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
            try:
                shutil.copy(DATA_FILE, BACKUP_FILE)
            except Exception:
                pass
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
    data["leaderboard"].append({
        "user_id": str(user_id), "name": name,
        "coins": coins, "level": level, "prestige": prestige
    })
    data["leaderboard"].sort(key=lambda x: (x["prestige"], x["level"], x["coins"]), reverse=True)
    data["leaderboard"] = data["leaderboard"][:50]
    save_data(data)

# ==================== توابع کمکی ====================
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

def get_available_fruits(user):
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["fruits"]

def get_available_features(user):
    return LEVEL_UNLOCKS.get(user["level"], LEVEL_UNLOCKS[7])["features"]

def has_feature(user, feature):
    return feature in get_available_features(user)

def xp_needed_for(level):
    return XP_REQUIRED.get(level, 999999)

def xp_from_sale(fruit_name):
    return random.randint(*XP_FROM_SALES[fruit_name]) if fruit_name in XP_FROM_SALES else 0

def find_user_by_name_or_code(query):
    data = load_data()
    q = query.lower()
    for uid, u in data["users"].items():
        if u.get("name", "").lower() == q:
            return uid, u
        if u.get("referral_code", "").lower() == q:
            return uid, u
    return None, None

# ==================== کیبورد ====================
def get_keyboard(user_id):
    user = get_user(user_id)
    if not user:
        return InlineKeyboardBuilder().as_markup()
    
    cf = user["current_fruit"]
    if cf not in get_available_fruits(user):
        cf = get_available_fruits(user)[0]
        update_user(user_id, {"current_fruit": cf})
    
    effects, _ = get_season_effects()
    multiplier = user["prestige_multiplier"]
    fruit = FRUITS[cf]
    buy_price = int(PRICES[cf][0] * multiplier * effects["buy_mult"])
    sell_price = int(PRICES[cf][1] * multiplier * effects["sell_mult"])
    
    kb = InlineKeyboardBuilder()
    
    if user["state"] == "growing":
        kb.button("⏳ در حال رشد...", callback_data="noop")
        kb.button("⏳ هنوز نرسیده!", callback_data="noop")
    elif user["state"] == "harvested":
        kb.button("🌱 بذر قبلاً کاشته شده", callback_data="noop")
        kb.button(f"💰 فروش {fruit} ({sell_price:,})", callback_data="sell")
    elif user["coins"] < buy_price:
        kb.button(f"❌ سکه ناکافی (نیاز {buy_price:,})", callback_data="noop")
        kb.button(f"💰 فروش {fruit} ({sell_price:,})", callback_data="sell")
    else:
        kb.button(f"🌱 خرید بذر {fruit} ({buy_price:,})", callback_data="buy")
        kb.button(f"💰 فروش {fruit} ({sell_price:,})", callback_data="sell")
    
    kb.adjust(2)
    
    available = get_available_fruits(user)
    if len(available) > 1:
        for i in available:
            mark = "✅ " if i == cf else ""
            kb.button(f"{mark}{FRUITS[i]}", callback_data=f"switch_{i}")
        kb.adjust(3)
    
    kb.button("📊 وضعیت", callback_data="status")
    
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
    if has_feature(user, "gift"):
        kb.button("🎁 هدیه دادن", callback_data="gift")
    if has_feature(user, "prestige") and user["level"] >= 7:
        kb.button("⭐ پرستیژ", callback_data="prestige_menu")
    
    kb.adjust(2)
    return kb.as_markup()

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
    await show_main_menu(message)

@dp.message(Command("status"))
async def cmd_status(message: Message):
    await show_status(message)

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
    if not user:
        return
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
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
    
    update_user(user_id, {
        "coins": user["coins"] - amount,
        "gifts_given": user.get("gifts_given", 0) + 1
    })
    update_user(int(tid), {
        "coins": target["coins"] + amount,
        "gifts_received": target.get("gifts_received", 0) + 1
    })
    update_leaderboard(user_id, user["name"], user["coins"] - amount, user["level"], user["prestige"])
    update_leaderboard(int(tid), target["name"], target["coins"] + amount, target["level"], target["prestige"])
    await message.answer(f"✅ {amount:,} سکه به {target['name']} هدیه دادی!")

async def show_main_menu(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        return
    
    _, season = get_season_effects()
    prestige_text = f"⭐ پرستیژ {user['prestige']}" if user['prestige'] > 0 else "بدون پرستیژ"
    text = (
        f"🌾 **مزرعه‌ی {user['name']}**\n\n"
        f"🌤 فصل: {SEASON_FA[season]}\n"
        f"💰 سکه: {user['coins']:,}\n"
        f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
        f"⭐ {prestige_text}\n"
        f"🍓 میوه: {FRUITS[user['current_fruit']]}\n"
    )
    await message.answer(text, reply_markup=get_keyboard(user_id))

async def show_status(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        return
    _, season = get_season_effects()
    text = (
        f"📊 **وضعیت {user['name']}:**\n"
        f"💰 سکه: {user['coins']:,}\n"
        f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
        f"⭐ پرستیژ: {user['prestige']} | ضریب: {user['prestige_multiplier']:.2f}x\n"
        f"🌤 فصل: {SEASON_FA[season]}\n"
        f"🌱 میوه: {FRUITS[user['current_fruit']]}\n"
        f"⏳ وضعیت: {user['state']}\n"
        f"🎁 هدیه داده: {user.get('gifts_given', 0)} | گرفته: {user.get('gifts_received', 0)}\n"
        f"👷 کارگر: لول {user['worker']['level']} ({'فعال' if user['worker']['active'] else 'غیرفعال'})"
    )
    await message.answer(text, reply_markup=get_keyboard(user_id))

# ==================== کال‌بک‌ها ====================
@dp.callback_query()
async def on_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = callback.data
    user_id = callback.from_user.id
    user = get_user(user_id)
    if not user:
        return
    
    if data == "noop":
        return
    elif data == "status":
        await edit_status(callback, user)
    elif data == "buy":
        await buy_seed(callback, user, bot)
    elif data == "sell":
        await sell_fruit(callback, user)
    elif data.startswith("switch_"):
        await switch_fruit(callback, user, int(data.split("_")[1]))
    elif data == "leaderboard":
        await show_leaderboard(callback, user)
    elif data == "upgrades":
        await show_upgrades(callback, user)
    elif data.startswith("upgrade_"):
        await buy_upgrade(callback, user, data.replace("upgrade_", ""))
    elif data == "daily_orders":
        await show_daily_orders(callback, user)
    elif data == "complete_orders":
        await complete_orders(callback, user)
    elif data == "shop":
        await show_shop(callback, user)
    elif data.startswith("shop_"):
        await buy_shop(callback, user, int(data.split("_")[1]))
    elif data == "worker_menu":
        await show_worker(callback, user)
    elif data == "worker_toggle":
        await toggle_worker(callback, user)
    elif data == "worker_upgrade":
        await upgrade_worker(callback, user)
    elif data == "gift":
        await start_gift(callback, user, state)
    elif data == "prestige_menu":
        await show_prestige(callback, user)
    elif data == "buy_prestige":
        await buy_prestige(callback, user)
    elif data == "back":
        await callback.message.edit_text("🔙 منوی اصلی", reply_markup=get_keyboard(user_id))

async def edit_status(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    _, season = get_season_effects()
    text = (
        f"📊 **وضعیت {user['name']}:**\n"
        f"💰 سکه: {user['coins']:,}\n"
        f"📈 لول: {user['level']} | XP: {user['xp']}/{xp_needed_for(user['level'])}\n"
        f"⭐ پرستیژ: {user['prestige']}\n"
        f"🌤 فصل: {SEASON_FA[season]}\n"
        f"🌱 میوه: {FRUITS[user['current_fruit']]}\n"
    )
    await callback.message.edit_text(text, reply_markup=get_keyboard(user_id))

async def switch_fruit(callback: CallbackQuery, user, fruit_idx):
    user_id = callback.from_user.id
    if fruit_idx not in get_available_fruits(user):
        await callback.message.edit_text("🔒 این میوه قفل است!", reply_markup=get_keyboard(user_id))
        return
    update_user(user_id, {"current_fruit": fruit_idx})
    await callback.message.edit_text(
        f"✅ میوه‌ی فعلی: {FRUITS[fruit_idx]}",
        reply_markup=get_keyboard(user_id)
    )

async def buy_seed(callback: CallbackQuery, user, bot):
    user_id = callback.from_user.id
    cf = user["current_fruit"]
    effects, _ = get_season_effects()
    buy_price = int(PRICES[cf][0] * user["prestige_multiplier"] * effects["buy_mult"])
    
    if user["state"] == "growing":
        await callback.message.edit_text("⏳ صبر کن بذر در حال رشد است.", reply_markup=get_keyboard(user_id))
        return
    if user["state"] == "harvested":
        await callback.message.edit_text("🌱 اول بفروش بعد بخر.", reply_markup=get_keyboard(user_id))
        return
    if user["coins"] < buy_price:
        await callback.message.edit_text(f"❌ نیاز به {buy_price:,} سکه.", reply_markup=get_keyboard(user_id))
        return
    
    growth_time = GROWTH_TIMES[cf] * effects["growth_mult"]
    if user["upgrades"].get("auto_water", 0) > 0:
        growth_time *= 0.8
    
    update_user(user_id, {"coins": user["coins"] - buy_price, "state": "growing"})
    await callback.message.edit_text(
        f"🌱 {FRUITS[cf]} کاشته شد! {growth_time:.1f} دقیقه دیگه می‌رسه.",
        reply_markup=get_keyboard(user_id)
    )
    asyncio.create_task(grow_complete(user_id, callback.message.chat.id, growth_time, bot))

async def grow_complete(user_id, chat_id, minutes, bot):
    await asyncio.sleep(minutes * 60)
    user = get_user(user_id)
    if user and user["state"] == "growing":
        update_user(user_id, {"state": "harvested"})
        try:
            await bot.send_message(chat_id, f"🍓 {FRUITS[user['current_fruit']]} رسید! بفروشش.", reply_markup=get_keyboard(user_id))
        except Exception:
            pass

async def sell_fruit(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    if user["state"] != "harvested":
        await callback.message.edit_text("⏳ هنوز نرسیده!", reply_markup=get_keyboard(user_id))
        return
    
    cf = user["current_fruit"]
    effects, _ = get_season_effects()
    sell_price = int(PRICES[cf][1] * user["prestige_multiplier"] * effects["sell_mult"])
    
    golden = random.random() < effects["golden_chance"]
    if golden:
        sell_price *= 2
    
    if user["upgrades"].get("golden_pot", 0) > 0:
        sell_price = int(sell_price * (1 + 0.1 * user["upgrades"]["golden_pot"]))
    
    fruit_name = FRUITS[cf]
    xp_gain = int(xp_from_sale(fruit_name) * user["prestige_multiplier"])
    
    new_coins = user["coins"] + sell_price
    new_xp = user["xp"] + xp_gain
    new_level = user["level"]
    
    xp_needed = xp_needed_for(new_level)
    level_up_msg = ""
    while new_xp >= xp_needed and new_level < 7:
        new_xp -= xp_needed
        new_level += 1
        xp_needed = xp_needed_for(new_level)
        level_up_msg = f"\n🎉 **لول آپ! به لول {new_level} رسیدی!**"
    
    update_user(user_id, {"coins": new_coins, "xp": new_xp, "level": new_level, "state": "idle"})
    update_leaderboard(user_id, user["name"], new_coins, new_level, user["prestige"])
    
    golden_text = " ✨(طلایی!)" if golden else ""
    await callback.message.edit_text(
        f"✅ {fruit_name} فروخته شد{golden_text}\n"
        f"💰 +{sell_price:,} سکه\n"
        f"⭐ +{xp_gain} XP\n"
        f"📈 لول {new_level} (XP: {new_xp}/{xp_needed_for(new_level)}){level_up_msg}",
        reply_markup=get_keyboard(user_id)
    )

async def show_leaderboard(callback: CallbackQuery, user):
    data = load_data()
    lb = data["leaderboard"][:10]
    text = "🏆 **لیدربرد:**\n\n"
    for i, item in enumerate(lb, 1):
        p = f"⭐{item['prestige']}" if item['prestige'] > 0 else ""
        text += f"{i}. {item['name']} {p} — لول {item['level']} | {item['coins']:,}\n"
    if not lb:
        text += "هنوز کسی نیست!"
    await callback.message.edit_text(text, reply_markup=get_keyboard(callback.from_user.id))

async def show_upgrades(callback: CallbackQuery, user):
    u = user["upgrades"]
    c1 = 1000 * (u.get("auto_water", 0) + 1)
    c2 = 2000 * (u.get("golden_pot", 0) + 1)
    c3 = 5000 * (u.get("professional_seeder", 0) + 1)
    text = (
        f"🔧 **ارتقاء ابزار:**\n\n"
        f"💧 آبیاری خودکار (۲۰٪ رشد سریع‌تر) — {c1:,}\n"
        f"  خریداری شده: {u.get('auto_water', 0)} بار\n\n"
        f"🏺 گلدان طلایی (+۱۰٪ فروش) — {c2:,}\n"
        f"  خریداری شده: {u.get('golden_pot', 0)} بار\n\n"
        f"🌱 بذرپاش حرفه‌ای — {c3:,}\n"
        f"  خریداری شده: {u.get('professional_seeder', 0)} بار\n"
    )
    kb = InlineKeyboardBuilder()
    kb.button(f"💧 آبیاری ({c1:,})", callback_data="upgrade_auto_water")
    kb.button(f"🏺 گلدان ({c2:,})", callback_data="upgrade_golden_pot")
    kb.button(f"🌱 بذرپاش ({c3:,})", callback_data="upgrade_professional_seeder")
    kb.button("🔙 بازگشت", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_upgrade(callback: CallbackQuery, user, key):
    user_id = callback.from_user.id
    base = {"auto_water": 1000, "golden_pot": 2000, "professional_seeder": 5000}
    if key not in base:
        return
    count = user["upgrades"].get(key, 0)
    cost = base[key] * (count + 1)
    if user["coins"] < cost:
        await callback.message.edit_text(f"❌ نیاز به {cost:,} سکه.", reply_markup=get_keyboard(user_id))
        return
    u = user["upgrades"]
    u[key] = count + 1
    update_user(user_id, {"coins": user["coins"] - cost, "upgrades": u})
    await callback.message.edit_text(f"✅ ارتقاء انجام شد! (بار {count+1})", reply_markup=get_keyboard(user_id))

async def show_daily_orders(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    if user["daily_orders"]["date"] != today:
        orders = []
        for _ in range(3):
            fi = random.randint(0, len(FRUITS) - 2)
            orders.append({"fruit": FRUITS[fi], "count": random.randint(1, 3)})
        update_user(user_id, {"daily_orders": {"date": today, "orders": orders, "completed": False}})
        user = get_user(user_id)
    
    orders = user["daily_orders"]["orders"]
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("📦 امروز سفارشات تکمیل شده!", reply_markup=get_keyboard(user_id))
        return
    
    text = "📦 **سفارشات روزانه:**\n\n"
    for i, o in enumerate(orders, 1):
        text += f"{i}. {o['count']} عدد {o['fruit']}\n"
    kb = InlineKeyboardBuilder()
    kb.button("✅ تکمیل", callback_data="complete_orders")
    kb.button("🔙 بازگشت", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def complete_orders(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    if user["daily_orders"]["completed"]:
        await callback.message.edit_text("قبلاً تکمیل شده!", reply_markup=get_keyboard(user_id))
        return
    orders = user["daily_orders"]["orders"]
    inventory = user.get("inventory", [])
    for o in orders:
        if inventory.count(o["fruit"]) < o["count"]:
            await callback.message.edit_text(f"❌ کمبود {o['fruit']} در انبار!", reply_markup=get_keyboard(user_id))
            return
    for o in orders:
        for _ in range(o["count"]):
            inventory.remove(o["fruit"])
    bonus = 0
    for o in orders:
        fi = FRUITS.index(o["fruit"])
        bonus += PRICES[fi][1] * o["count"] * 1.5
    bonus = int(bonus * user["prestige_multiplier"])
    new_coins = user["coins"] + bonus
    update_user(user_id, {
        "coins": new_coins, "inventory": inventory,
        "daily_orders": {**user["daily_orders"], "completed": True}
    })
    update_leaderboard(user_id, user["name"], new_coins, user["level"], user["prestige"])
    await callback.message.edit_text(f"✅ سفارشات تکمیل شد! +{bonus:,} سکه", reply_markup=get_keyboard(user_id))

async def show_shop(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    level = user["level"]
    if level < 4:
        await callback.message.edit_text("🔒 فروشگاه در لول ۴ باز می‌شود.", reply_markup=get_keyboard(user_id))
        return
    prices = SHOP_PRICES.get(level, SHOP_PRICES[7])
    text = "🛒 **فروشگاه سکه**\n\n💰 با توجه به لول شما، مقدار سکه‌ها متفاوت است.\n\n"
    for amt, coins in prices.items():
        text += f"• {amt:,} تومان → {coins:,} سکه"
        if amt == 50000:
            text += " + بذر معمولی"
        elif amt == 100000:
            text += " + بذر طلایی ✨"
        text += "\n"
    kb = InlineKeyboardBuilder()
    kb.button("۵,۰۰۰ تومان", callback_data="shop_5000")
    kb.button("۱۰,۰۰۰ تومان", callback_data="shop_10000")
    kb.button("۲۰,۰۰۰ تومان", callback_data="shop_20000")
    kb.button("۵۰,۰۰۰ تومان", callback_data="shop_50000")
    kb.button("۱۰۰,۰۰۰ تومان ✨", callback_data="shop_100000")
    kb.button("🔙 بازگشت", callback_data="back")
    kb.adjust(2, 2, 1, 1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_shop(callback: CallbackQuery, user, amount):
    user_id = callback.from_user.id
    level = user["level"]
    prices = SHOP_PRICES.get(level, SHOP_PRICES[7])
    if amount not in prices:
        return
    coins = prices[amount]
    inventory = user.get("inventory", [])
    gift_msg = ""
    if amount == 50000:
        avail = get_available_fruits(user)
        fi = random.choice(avail)
        inventory.append(FRUITS[fi])
        gift_msg = f"\n🎁 بذر {FRUITS[fi]} به انبار اضافه شد."
    elif amount == 100000:
        fi = random.randint(0, len(FRUITS)-1)
        inventory.append(f"طلایی_{FRUITS[fi]}")
        gift_msg = f"\n✨ بذر طلایی {FRUITS[fi]} به انبار اضافه شد."
    new_coins = user["coins"] + coins
    update_user(user_id, {"coins": new_coins, "inventory": inventory})
    update_leaderboard(user_id, user["name"], new_coins, user["level"], user["prestige"])
    await callback.message.edit_text(
        f"✅ خرید موفق!\n💰 +{coins:,} سکه\nموجودی: {new_coins:,}{gift_msg}",
        reply_markup=get_keyboard(user_id)
    )

async def show_worker(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    w = user["worker"]
    cost = 5000 * w["level"]
    text = (
        f"👷 **کارگر شما**\n"
        f"لول: {w['level']}\n"
        f"وضعیت: {'فعال ✅' if w['active'] else 'غیرفعال ❌'}\n"
        f"هزینه ارتقاء: {cost:,}"
    )
    kb = InlineKeyboardBuilder()
    kb.button("🔄 فعال/غیرفعال", callback_data="worker_toggle")
    kb.button("⬆️ ارتقاء", callback_data="worker_upgrade")
    kb.button("🔙 بازگشت", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def toggle_worker(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    w = user["worker"]
    w["active"] = not w["active"]
    update_user(user_id, {"worker": w})
    await callback.message.edit_text(
        f"👷 کارگر {'فعال' if w['active'] else 'غیرفعال'} شد.",
        reply_markup=get_keyboard(user_id)
    )

async def upgrade_worker(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    w = user["worker"]
    cost = 5000 * w["level"]
    if user["coins"] < cost:
        await callback.message.edit_text(f"❌ نیاز به {cost:,} سکه.", reply_markup=get_keyboard(user_id))
        return
    w["level"] += 1
    update_user(user_id, {"coins": user["coins"] - cost, "worker": w})
    await callback.message.edit_text(f"✅ کارگر به لول {w['level']} ارتقاء یافت!", reply_markup=get_keyboard(user_id))

async def start_gift(callback: CallbackQuery, user, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(UserForm.gift_target)
    await callback.message.edit_text(
        "🎁 نام یا کد معرف کاربر مقصد را وارد کن:",
        reply_markup=get_keyboard(user_id)
    )

async def show_prestige(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    if user["level"] < 7:
        await callback.message.edit_text("🔒 پرستیژ در لول ۷ باز می‌شود.", reply_markup=get_keyboard(user_id))
        return
    if user["prestige"] >= 10:
        await callback.message.edit_text("⭐ به بالاترین پرستیژ رسیدی!", reply_markup=get_keyboard(user_id))
        return
    nxt = user["prestige"] + 1
    price = PRESTIGE_PRICES[nxt]
    text = (
        f"⭐ **پرستیژ {nxt}**\n"
        f"هزینه: {price:,} سکه\n"
        f"پاداش: ضریب +۵۰٪ (از {user['prestige_multiplier']:.2f}x به {user['prestige_multiplier']*1.5:.2f}x)\n\n"
        f"⚠️ همه چیز ریست می‌شود به جز نام و پرستیژ."
    )
    kb = InlineKeyboardBuilder()
    kb.button(f"⭐ خرید ({price:,})", callback_data="buy_prestige")
    kb.button("🔙 بازگشت", callback_data="back")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def buy_prestige(callback: CallbackQuery, user):
    user_id = callback.from_user.id
    if user["prestige"] >= 10:
        return
    nxt = user["prestige"] + 1
    price = PRESTIGE_PRICES[nxt]
    if user["coins"] < price:
        await callback.message.edit_text(f"❌ نیاز به {price:,} سکه.", reply_markup=get_keyboard(user_id))
        return
    new_user = create_default_user(user_id)
    new_user["name"] = user["name"]
    new_user["prestige"] = nxt
    new_user["prestige_multiplier"] = user["prestige_multiplier"] * 1.5
    new_user["referral_code"] = user["referral_code"]
    new_user["gifts_given"] = user.get("gifts_given", 0)
    new_user["gifts_received"] = user.get("gifts_received", 0)
    data = load_data()
    data["users"][str(user_id)] = new_user
    save_data(data)
    update_leaderboard(user_id, user["name"], 1, 1, nxt)
    await callback.message.edit_text(
        f"⭐ **تبریک! پرستیژ {nxt}!**\nضریب جدید: {new_user['prestige_multiplier']:.2f}x",
        reply_markup=get_keyboard(user_id)
    )

# ==================== اجرا ====================
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("🤖 ربات فارمینگ بله روشن شد...")
    
    # توقف خودکار بعد از ۴ دقیقه تا اجرای بعدی بدون تداخل شروع شود
    async def stop_after_delay():
        await asyncio.sleep(340 * 60)  # ۳۴۰ دقیقه = ۵ ساعت و ۴۰ دقیقه
        print("⏰ زمان اجرا تمام شد. توقف ربات...")
        try:
            await dp.stop_polling()
        except Exception as e:
            print(f"خطا در توقف: {e}")
    
    asyncio.create_task(stop_after_delay())
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"ربات متوقف شد: {e}")

if __name__ == "__main__":
    asyncio.run(main())
