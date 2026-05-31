import os
import re
import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())

# =========================
# STATES
# =========================

class Register(StatesGroup):
    team = State()
    player = State()
    facebook = State()
    serial = State()
    screenshot = State()

class Search(StatesGroup):
    text = State()

class AddLeader(StatesGroup):
    user_id = State()

class RemoveLeader(StatesGroup):
    user_id = State()

# =========================
# DB
# =========================

async def setup_db():
    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            team TEXT,
            player_name TEXT,
            facebook TEXT,
            serial TEXT,
            screenshot TEXT,
            status TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS leaders (
            user_id INTEGER PRIMARY KEY
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            name TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await db.execute("""
        INSERT OR IGNORE INTO settings(name,value)
        VALUES('transfers','off')
        """)

        await db.execute("""
        INSERT OR IGNORE INTO leaders(user_id)
        VALUES(?)
        """, (OWNER_ID,))

        await db.commit()

# =========================
# HELPERS
# =========================

async def is_leader(user_id):
    async with aiosqlite.connect("union.db") as db:
        cur = await db.execute("SELECT 1 FROM leaders WHERE user_id=?", (user_id,))
        return await cur.fetchone() is not None


async def transfers_open():
    async with aiosqlite.connect("union.db") as db:
        cur = await db.execute("SELECT value FROM settings WHERE name='transfers'")
        row = await cur.fetchone()
        return row and row[0] == "on"


def valid_fb(url):
    return re.match(r"(https?://)?(www\.)?(facebook|fb)\.com/.+", url)

# =========================
# UI
# =========================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 تسجيل", callback_data="register")],
        [InlineKeyboardButton(text="🏆 التيمات", callback_data="teams")],
        [InlineKeyboardButton(text="🔎 بحث", callback_data="search")],
        [InlineKeyboardButton(text="🛠 إدارة", callback_data="admin")]
    ])


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 الطلبات", callback_data="requests")],
        [InlineKeyboardButton(text="🔓 فتح الانتقالات", callback_data="open")],
        [InlineKeyboardButton(text="🔒 غلق الانتقالات", callback_data="close")],
        [InlineKeyboardButton(text="➕ قائد", callback_data="add_leader")],
        [InlineKeyboardButton(text="➖ حذف قائد", callback_data="remove_leader")],
        [InlineKeyboardButton(text="⬅️ رجوع", callback_data="back")]
    ])

# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("🇮🇶 أهلاً بك في نظام البطولة", reply_markup=main_menu())

# =========================
# ADMIN CHECK
# =========================

@dp.callback_query(F.data == "admin")
async def admin(callback: CallbackQuery):
    if not await is_leader(callback.from_user.id):
        return await callback.answer("مو مسموح")
    await callback.message.answer("🛠 الإدارة", reply_markup=admin_menu())

# =========================
# REGISTER
# =========================

@dp.callback_query(F.data == "register")
async def register(callback: CallbackQuery, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:
        cur = await db.execute("SELECT * FROM players WHERE user_id=?", (callback.from_user.id,))
        old = await cur.fetchone()

    if old and not await transfers_open():
        return await callback.message.answer("❌ أنت مسجل مسبقاً")

    if old and await transfers_open():
        async with aiosqlite.connect("union.db") as db:
            await db.execute("DELETE FROM players WHERE user_id=?", (callback.from_user.id,))
            await db.commit()

    await state.set_state(Register.team)
    await callback.message.answer("🏆 ارسل اسم التيم")

@dp.message(Register.team)
async def team(message: Message, state: FSMContext):
    await state.update_data(team=message.text)
    await state.set_state(Register.player)
    await message.answer("👤 اسم اللاعب")

@dp.message(Register.player)
async def player(message: Message, state: FSMContext):
    await state.update_data(player=message.text)
    await state.set_state(Register.facebook)
    await message.answer("🌐 رابط الفيسبوك")

@dp.message(Register.facebook)
async def fb(message: Message, state: FSMContext):

    if not valid_fb(message.text):
        return await message.answer("❌ رابط غير صحيح")

    await state.update_data(facebook=message.text)
    await state.set_state(Register.serial)
    await message.answer("🆔 السيريال")

@dp.message(Register.serial)
async def serial(message: Message, state: FSMContext):
    await state.update_data(serial=message.text)
    await state.set_state(Register.screenshot)
    await message.answer("📸 ارسل صورة السيريال")

@dp.message(Register.screenshot, F.photo)
async def screen(message: Message, state: FSMContext):

    data = await state.get_data()
    photo = message.photo[-1].file_id

    async with aiosqlite.connect("union.db") as db:

        await db.execute("DELETE FROM players WHERE user_id=?", (message.from_user.id,))

        await db.execute("""
        INSERT INTO players(user_id,team,player_name,facebook,serial,screenshot,status)
        VALUES(?,?,?,?,?,?,?)
        """, (
            message.from_user.id,
            data["team"],
            data["player"],
            data["facebook"],
            data["serial"],
            photo,
            "pending"
        ))

        await db.commit()

    async with aiosqlite.connect("union.db") as db:
        cur = await db.execute("SELECT user_id FROM leaders")
        leaders = await cur.fetchall()

    text = f"""
📥 طلب جديد
🏆 {data['team']}
👤 {data['player']}
🆔 {data['serial']}
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton("✅ قبول", callback_data=f"ok_{message.from_user.id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"no_{message.from_user.id}")
    ]])

    for l in leaders:
        try:
            await bot.send_photo(l[0], photo, caption=text, reply_markup=keyboard)
        except:
            pass

    await message.answer("✅ تم إرسال طلبك")
    await state.clear()

# =========================
# ACCEPT / REJECT
# =========================

@dp.callback_query(F.data.startswith("ok_"))
async def ok(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    uid = int(callback.data.split("_")[1])

    async with aiosqlite.connect("union.db") as db:
        await db.execute("UPDATE players SET status='accepted' WHERE user_id=?", (uid,))
        await db.commit()

    await bot.send_message(uid, "✅ تمت الموافقة")
    await callback.message.delete()

@dp.callback_query(F.data.startswith("no_"))
async def no(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    uid = int(callback.data.split("_")[1])

    async with aiosqlite.connect("union.db") as db:
        await db.execute("DELETE FROM players WHERE user_id=?", (uid,))
        await db.commit()

    await bot.send_message(uid, "❌ تم الرفض")
    await callback.message.delete()

# =========================
# TEAMS
# =========================

@dp.callback_query(F.data == "teams")
async def teams(callback: CallbackQuery):

    async with aiosqlite.connect("union.db") as db:
        cur = await db.execute("SELECT DISTINCT team FROM players WHERE status='accepted'")
        rows = await cur.fetchall()

    text = "🏆 التيمات:\n\n"
    for r in rows:
        text += f"- {r[0]}\n"

    await callback.message.answer(text)

# =========================
# SEARCH
# =========================

@dp.callback_query(F.data == "search")
async def search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Search.text)
    await callback.message.answer("🔎 ارسل اسم اللاعب")

@dp.message(Search.text)
async def search_do(message: Message, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:
        cur = await db.execute("""
        SELECT team,player_name,facebook,serial
        FROM players
        WHERE player_name LIKE ?
        """, (f"%{message.text}%",))
        rows = await cur.fetchall()

    text = ""
    for r in rows:
        text += f"\n🏆 {r[0]}\n👤 {r[1]}\n🆔 {r[3]}\n"

    await message.answer(text or "ماكو نتائج")
    await state.clear()

# =========================
# TRANSFERS
# =========================

@dp.callback_query(F.data == "open")
async def open_t(callback: CallbackQuery):
    if not await is_leader(callback.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:
        await db.execute("UPDATE settings SET value='on' WHERE name='transfers'")
        await db.commit()

    await callback.message.answer("✅ مفتوحة")

@dp.callback_query(F.data == "close")
async def close_t(callback: CallbackQuery):
    if not await is_leader(callback.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:
        await db.execute("UPDATE settings SET value='off' WHERE name='transfers'")
        await db.commit()

    await callback.message.answer("🔒 مغلقة")

# =========================
# RUN
# =========================

async def main():
    await setup_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
