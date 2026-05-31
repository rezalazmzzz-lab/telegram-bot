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
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

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
async def db():
    return await aiosqlite.connect("bot.db")

async def init():
    async with await db() as c:

        await c.execute("""
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

        await c.execute("""
        CREATE TABLE IF NOT EXISTS leaders(
            user_id INTEGER PRIMARY KEY
        )
        """)

        await c.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await c.execute("INSERT OR IGNORE INTO settings VALUES('transfer','off')")
        await c.execute("INSERT OR IGNORE INTO leaders VALUES(?)", (OWNER_ID,))
        await c.commit()

# =========================
async def is_leader(uid):
    async with await db() as c:
        r = await c.execute("SELECT 1 FROM leaders WHERE user_id=?", (uid,))
        return await r.fetchone() is not None

async def transfer():
    async with await db() as c:
        r = await c.execute("SELECT value FROM settings WHERE key='transfer'")
        x = await r.fetchone()
        return x and x[0] == "on"

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
@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("🏆 نظام البطولة", reply_markup=menu)

# =========================
# REGISTER
# =========================

@dp.message(F.text == "📋 تسجيل")
async def reg(m: Message, state: FSMContext):

    async with await db() as c:
        r = await c.execute("SELECT * FROM players WHERE user_id=?", (m.from_user.id,))
        old = await r.fetchone()

    if old and not await transfer():
        return await m.answer("❌ مسجل مسبقاً")

    if old and await transfer():
        async with await db() as c:
            await c.execute("DELETE FROM players WHERE user_id=?", (m.from_user.id,))
            await c.commit()

    await state.set_state(Reg.team)
    await m.answer("🏆 اسم التيم")

@dp.message(Reg.team)
async def team(m: Message, state: FSMContext):
    await state.update_data(team=m.text)
    await state.set_state(Reg.player)
    await m.answer("👤 اسم اللاعب")

@dp.message(Reg.player)
async def player(m: Message, state: FSMContext):
    await state.update_data(player=m.text)
    await state.set_state(Reg.fb)
    await m.answer("🌐 فيسبوك")

@dp.message(Reg.fb)
async def fb(m: Message, state: FSMContext):
    if not re.match(r"(https?://)?(www\.)?(facebook|fb)\.com/.+", m.text):
        return await m.answer("❌ رابط غلط")

    await state.update_data(fb=m.text)
    await state.set_state(Reg.serial)
    await m.answer("🆔 سيريال")

@dp.message(Reg.serial)
async def serial(m: Message, state: FSMContext):
    await state.update_data(serial=m.text)
    await state.set_state(Reg.photo)
    await m.answer("📸 صورة")

@dp.message(Reg.photo, F.photo)
async def photo(m: Message, state: FSMContext):

    data = await state.get_data()
    ph = m.photo[-1].file_id

    async with await db() as c:
        await c.execute("DELETE FROM players WHERE user_id=?", (m.from_user.id,))
        await c.execute("""
        INSERT INTO players VALUES(?,?,?,?,?,?,?)
        """, (
            m.from_user.id,
            data["team"],
            data["player"],
            data["fb"],
            data["serial"],
            ph,
            "pending"
        ))
        await c.commit()

    async with await db() as c:
        r = await c.execute("SELECT user_id FROM leaders")
        ls = await r.fetchall()

    txt = f"📥 طلب\n🏆 {data['team']}\n👤 {data['player']}\n🆔 {data['serial']}"

    kb = None

    for l in ls:
        try:
            await bot.send_photo(l[0], ph, caption=txt, reply_markup=kb)
        except:
            pass

    await m.answer("✅ تم الإرسال")
    await state.clear()

# =========================
# ACCEPT / REJECT
# =========================

@dp.callback_query(F.data.startswith("ok_"))
async def ok(c: CallbackQuery):

    if not await is_leader(c.from_user.id):
        return

    uid = int(c.data.split("_")[1])

    async with await db() as d:
        await d.execute("UPDATE players SET status='accepted' WHERE user_id=?", (uid,))
        await d.commit()

    await bot.send_message(uid, "✅ مقبول")
    await c.message.delete()

@dp.callback_query(F.data.startswith("no_"))
async def no(c: CallbackQuery):

    if not await is_leader(c.from_user.id):
        return

    uid = int(c.data.split("_")[1])

    async with await db() as d:
        await d.execute("DELETE FROM players WHERE user_id=?", (uid,))
        await d.commit()

    await bot.send_message(uid, "❌ مرفوض")
    await c.message.delete()

# =========================
# TEAMS
# =========================

@dp.message(F.text == "🏆 التيمات")
async def teams(m: Message):

    async with await db() as c:
        r = await c.execute("SELECT DISTINCT team FROM players WHERE status='accepted'")
        rows = await r.fetchall()

    txt = "🏆 التيمات:\n\n"
    for r in rows:
        txt += f"• {r[0]}\n"

    await m.answer(txt)

# =========================
# SEARCH
# =========================

@dp.message(F.text == "🔎 بحث")
async def s(m: Message, state: FSMContext):
    await state.set_state(Search.text)
    await m.answer("اكتب اسم")

@dp.message(Search.text)
async def sd(m: Message, state: FSMContext):

    async with await db() as c:
        r = await c.execute("""
        SELECT team,player,serial FROM players
        WHERE player LIKE ?
        """, (f"%{m.text}%",))
        rows = await r.fetchall()

    t = ""
    for r in rows:
        t += f"\n{r[0]} | {r[1]} | {r[2]}"

    await m.answer(t or "لا يوجد")
    await state.clear()

# =========================
# ADMIN
# =========================

@dp.message(F.text == "🛠 إدارة")
async def admin(m: Message):

    if not await is_leader(m.from_user.id):
        return

    await m.answer("🛠 لوحة إدارة جاهزة (تطوير إضافي لاحقاً)")

# =========================
async def main():
    await init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
