import os
import re
import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
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

class Reg(StatesGroup):
    team = State()
    player = State()
    fb = State()
    serial = State()
    photo = State()

class Search(StatesGroup):
    text = State()

# =========================
# DB
# =========================

async def db_init():
    async with aiosqlite.connect("bot.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            user_id INTEGER PRIMARY KEY,
            team TEXT,
            player TEXT,
            fb TEXT,
            serial TEXT,
            photo TEXT,
            status TEXT
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS leaders(
            user_id INTEGER PRIMARY KEY
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await db.execute("INSERT OR IGNORE INTO settings VALUES('transfer','off')")
        await db.execute("INSERT OR IGNORE INTO leaders VALUES(?)", (OWNER_ID,))

        await db.commit()

# =========================
# HELPERS
# =========================

async def is_leader(uid):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT 1 FROM leaders WHERE user_id=?", (uid,))
        return await cur.fetchone() is not None


async def transfer():
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT value FROM settings WHERE key='transfer'")
        row = await cur.fetchone()
        return row and row[0] == "on"

# =========================
# KEYBOARD
# =========================

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 تسجيل")],
        [KeyboardButton(text="🏆 التيمات"), KeyboardButton(text="🔎 بحث")],
        [KeyboardButton(text="🛠 إدارة")]
    ],
    resize_keyboard=True
)

# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("🏆 أهلاً بك في نظام البطولة", reply_markup=menu)

# =========================
# MENU ROUTER
# =========================

@dp.message(F.text == "📋 تسجيل")
async def reg_start(m: Message, state: FSMContext):

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT * FROM players WHERE user_id=?", (m.from_user.id,))
        old = await cur.fetchone()

    if old and not await transfer():
        return await m.answer("❌ أنت مسجل مسبقاً")

    if old and await transfer():
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("DELETE FROM players WHERE user_id=?", (m.from_user.id,))
            await db.commit()

    await state.set_state(Reg.team)
    await m.answer("🏆 اكتب اسم التيم")

@dp.message(Reg.team)
async def team(m: Message, state: FSMContext):
    await state.update_data(team=m.text)
    await state.set_state(Reg.player)
    await m.answer("👤 اسم اللاعب")

@dp.message(Reg.player)
async def player(m: Message, state: FSMContext):
    await state.update_data(player=m.text)
    await state.set_state(Reg.fb)
    await m.answer("🌐 رابط الفيسبوك")

@dp.message(Reg.fb)
async def fb(m: Message, state: FSMContext):

    if not re.match(r"(https?://)?(www\.)?(facebook|fb)\.com/.+", m.text):
        return await m.answer("❌ رابط غير صحيح")

    await state.update_data(fb=m.text)
    await state.set_state(Reg.serial)
    await m.answer("🆔 السيريال")

@dp.message(Reg.serial)
async def serial(m: Message, state: FSMContext):
    await state.update_data(serial=m.text)
    await state.set_state(Reg.photo)
    await m.answer("📸 ارسل صورة")

@dp.message(Reg.photo, F.photo)
async def photo(m: Message, state: FSMContext):

    data = await state.get_data()
    photo = m.photo[-1].file_id

    async with aiosqlite.connect("bot.db") as db:
        await db.execute("DELETE FROM players WHERE user_id=?", (m.from_user.id,))
        await db.execute("""
        INSERT INTO players VALUES(?,?,?,?,?,?,?)
        """, (
            m.from_user.id,
            data["team"],
            data["player"],
            data["fb"],
            data["serial"],
            photo,
            "pending"
        ))
        await db.commit()

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT user_id FROM leaders")
        leaders = await cur.fetchall()

    text = f"""
📥 طلب جديد
🏆 {data['team']}
👤 {data['player']}
🆔 {data['serial']}
"""

    keyboard = None

    for l in leaders:
        try:
            await bot.send_photo(
                l[0],
                photo,
                caption=text,
                reply_markup=keyboard
            )
        except:
            pass

    await m.answer("✅ تم إرسال طلبك")
    await state.clear()

# =========================
# ACCEPT / REJECT
# =========================

@dp.callback_query(F.data.startswith("ok_"))
async def ok(c: CallbackQuery):

    if not await is_leader(c.from_user.id):
        return

    uid = int(c.data.split("_")[1])

    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE players SET status='accepted' WHERE user_id=?", (uid,))
        await db.commit()

    await bot.send_message(uid, "✅ تمت الموافقة")
    await c.message.delete()

@dp.callback_query(F.data.startswith("no_"))
async def no(c: CallbackQuery):

    if not await is_leader(c.from_user.id):
        return

    uid = int(c.data.split("_")[1])

    async with aiosqlite.connect("bot.db") as db:
        await db.execute("DELETE FROM players WHERE user_id=?", (uid,))
        await db.commit()

    await bot.send_message(uid, "❌ تم الرفض")
    await c.message.delete()

# =========================
# TEAMS
# =========================

@dp.message(F.text == "🏆 التيمات")
async def teams(m: Message):

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT DISTINCT team FROM players WHERE status='accepted'")
        rows = await cur.fetchall()

    text = "🏆 التيمات:\n\n"
    for r in rows:
        text += f"• {r[0]}\n"

    await m.answer(text)

# =========================
# SEARCH
# =========================

@dp.message(F.text == "🔎 بحث")
async def search(m: Message, state: FSMContext):
    await state.set_state(Search.text)
    await m.answer("🔎 اكتب اسم اللاعب")

@dp.message(Search.text)
async def search_do(m: Message, state: FSMContext):

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("""
        SELECT team,player,serial FROM players
        WHERE player LIKE ?
        """, (f"%{m.text}%",))
        rows = await cur.fetchall()

    text = ""
    for r in rows:
        text += f"\n🏆 {r[0]}\n👤 {r[1]}\n🆔 {r[2]}\n"

    await m.answer(text or "ماكو نتائج")
    await state.clear()

# =========================
# TRANSFER (ADMIN ONLY BASIC)
# =========================

@dp.message(F.text == "🛠 إدارة")
async def admin(m: Message):

    if not await is_leader(m.from_user.id):
        return

    await m.answer("🛠 لوحة الإدارة مفعلة (تطوير لاحق)")

# =========================
# RUN
# =========================

async def main():
    await db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
