# ======================================
# IRAQ CLANS UNION BOT
# ======================================

import os
import re
import asyncio
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ======================================
# معلومات البوت
# ======================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

# ======================================
# تشغيل البوت
# ======================================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ======================================
# الحالات
# ======================================

class Register(StatesGroup):
    team = State()
    player = State()
    facebook = State()
    phone = State()
    screenshot = State()


class SearchPlayer(StatesGroup):
    text = State()


class AddLeader(StatesGroup):
    user_id = State()


class RemoveLeader(StatesGroup):
    user_id = State()

# ======================================
# قاعدة البيانات
# ======================================

async def setup_db():

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            team TEXT,
            player_name TEXT,
            facebook TEXT,
            phone TEXT,
            screenshot TEXT,
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
            name TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await db.execute("""
        INSERT OR IGNORE INTO leaders(user_id)
        VALUES(?)
        """, (OWNER_ID,))

        await db.execute("""
        INSERT OR IGNORE INTO settings(name,value)
        VALUES('transfers','off')
        """)

        await db.commit()

# ======================================
# دوال
# ======================================

async def is_leader(user_id):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM leaders WHERE user_id=?",
            (user_id,)
        ) as cursor:

            row = await cursor.fetchone()

            return row is not None


async def transfers_open():

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT value FROM settings WHERE name='transfers'"
        ) as cursor:

            row = await cursor.fetchone()

            return row[0] == "on"


def valid_facebook(url):

    pattern = r'(https?://)?(www\.)?(facebook|fb)\.com/.+'

    return re.match(pattern, url)

# ======================================
# القوائم
# ======================================

def main_menu(admin=False):

    buttons = [
        [KeyboardButton(text="📋 تسجيل")],
        [KeyboardButton(text="🏆 عرض التيمات")],
        [KeyboardButton(text="🔎 بحث لاعب")]
    ]

    if admin:
        buttons.append(
            [KeyboardButton(text="🛠 الإدارة")]
        )

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def admin_menu():

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 الطلبات")],
            [KeyboardButton(text="🔓 فتح الانتقالات")],
            [KeyboardButton(text="🔒 غلق الانتقالات")],
            [KeyboardButton(text="➕ اضافة قائد")],
            [KeyboardButton(text="➖ حذف قائد")],
            [KeyboardButton(text="🏠 رجوع")]
        ],
        resize_keyboard=True
    )

# ======================================
# ستارت
# ======================================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🇮🇶 اهلا بك في الاتحاد العراقي للكلانات",
        reply_markup=main_menu(
            await is_leader(message.from_user.id)
        )
    )

# ======================================
# رجوع
# ======================================

@dp.message(F.text == "🏠 رجوع")
async def back_home(message: Message):

    await message.answer(
        "🏠 القائمة الرئيسية",
        reply_markup=main_menu(
            await is_leader(message.from_user.id)
        )
    )

# ======================================
# الادارة
# ======================================

@dp.message(F.text == "🛠 الإدارة")
async def admin_panel(message: Message):

    if not await is_leader(message.from_user.id):
        return

    await message.answer(
        "🛠 لوحة الادارة",
        reply_markup=admin_menu()
    )

# ======================================
# تسجيل
# ======================================

@dp.message(F.text == "📋 تسجيل")
async def register(message: Message, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM players WHERE user_id=?",
            (message.from_user.id,)
        ) as cursor:

            player = await cursor.fetchone()

    if player and not await transfers_open():

        return await message.answer(
            "❌ انت مسجل بالفعل"
        )

    if player and await transfers_open():

        async with aiosqlite.connect("union.db") as db:

            await db.execute(
                "DELETE FROM players WHERE user_id=?",
                (message.from_user.id,)
            )

            await db.commit()

    await message.answer("🏆 ارسل اسم التيم")

    await state.set_state(Register.team)

# ======================================
# التسجيل
# ======================================

@dp.message(Register.team)
async def reg_team(message: Message, state: FSMContext):

    await state.update_data(team=message.text)

    await message.answer("👤 ارسل اسم اللاعب")

    await state.set_state(Register.player)


@dp.message(Register.player)
async def reg_player(message: Message, state: FSMContext):

    await state.update_data(player=message.text)

    await message.answer("🌐 ارسل رابط الفيس")

    await state.set_state(Register.facebook)


@dp.message(Register.facebook)
async def reg_facebook(message: Message, state: FSMContext):

    if not valid_facebook(message.text):

        return await message.answer(
            "❌ رابط غير صحيح"
        )

    await state.update_data(facebook=message.text)

    await message.answer("📱 ارسل الرقم")

    await state.set_state(Register.phone)


@dp.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):

    await state.update_data(phone=message.text)

    await message.answer("🖼 ارسل السكرين")

    await state.set_state(Register.screenshot)


@dp.message(Register.screenshot, F.photo)
async def reg_screen(message: Message, state: FSMContext):

    data = await state.get_data()

    photo = message.photo[-1].file_id

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        INSERT INTO players(
            user_id,
            team,
            player_name,
            facebook,
            phone,
            screenshot,
            status
        )
        VALUES(?,?,?,?,?,?,?)
        """, (
            message.from_user.id,
            data["team"],
            data["player"],
            data["facebook"],
            data["phone"],
            photo,
            "pending"
        ))

        await db.commit()

    leaders = []

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT user_id FROM leaders"
        ) as cursor:

            rows = await cursor.fetchall()

            leaders = [x[0] for x in rows]

    text = f"""
📥 طلب تسجيل جديد

🏆 التيم : {data['team']}
👤 اللاعب : {data['player']}
🌐 الفيس : {data['facebook']}
📱 الرقم : {data['phone']}
🆔 الايدي : {message.from_user.id}
"""

    for leader in leaders:

        try:

            await bot.send_photo(
                leader,
                photo,
                caption=text
            )

        except:
            pass

    await message.answer(
        "✅ سيتم مراجعة طلبك"
    )

    await state.clear()

# ======================================
# عرض التيمات
# ======================================

@dp.message(F.text == "🏆 عرض التيمات")
async def teams(message: Message):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT DISTINCT team
        FROM players
        WHERE status='accepted'
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ لا توجد تيمات"
        )

    text = "🏆 قائمة التيمات\n\n"

    for row in rows:

        team = row[0]

        text += f"🏆 {team}\n"

        async with aiosqlite.connect("union.db") as db:

            async with db.execute("""
            SELECT player_name,facebook,phone
            FROM players
            WHERE team=? AND status='accepted'
            """, (team,)) as cursor:

                players = await cursor.fetchall()

        for p in players:

            text += f"""
👤 {p[0]}
🌐 {p[1]}
📱 {p[2]}

"""

    await message.answer(text)

# ======================================
# بحث لاعب
# ======================================

@dp.message(F.text == "🔎 بحث لاعب")
async def search(message: Message, state: FSMContext):

    await message.answer(
        "🔎 ارسل اسم اللاعب"
    )

    await state.set_state(SearchPlayer.text)


@dp.message(SearchPlayer.text)
async def search_player(message: Message, state: FSMContext):

    text = message.text

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT
        team,
        player_name,
        facebook,
        phone
        FROM players
        WHERE player_name LIKE ?
        """, (f"%{text}%",)) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ اللاعب غير موجود"
        )

    result = ""

    for row in rows:

        result += f"""
🏆 التيم : {row[0]}
👤 اللاعب : {row[1]}
🌐 الفيس : {row[2]}
📱 الرقم : {row[3]}

"""

    await message.answer(result)

    await state.clear()

# ======================================
# الطلبات
# ======================================

@dp.message(F.text == "📥 الطلبات")
async def requests(message: Message):

    if not await is_leader(message.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT
        player_name,
        team,
        phone,
        facebook,
        screenshot
        FROM players
        WHERE status='pending'
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ لا توجد طلبات"
        )

    for row in rows:

        text = f"""
🏆 التيم : {row[1]}
👤 اللاعب : {row[0]}
🌐 الفيس : {row[3]}
📱 الرقم : {row[2]}
"""

        await bot.send_photo(
            message.chat.id,
            row[4],
            caption=text
        )

# ======================================
# فتح الانتقالات
# ======================================

@dp.message(F.text == "🔓 فتح الانتقالات")
async def open_transfers(message: Message):

    if not await is_leader(message.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        UPDATE settings
        SET value='on'
        WHERE name='transfers'
        """)

        await db.commit()

    await message.answer(
        "✅ تم فتح الانتقالات"
    )

# ======================================
# غلق الانتقالات
# ======================================

@dp.message(F.text == "🔒 غلق الانتقالات")
async def close_transfers(message: Message):

    if not await is_leader(message.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        UPDATE settings
        SET value='off'
        WHERE name='transfers'
        """)

        await db.commit()

    await message.answer(
        "✅ تم غلق الانتقالات"
    )

# ======================================
# اضافة قائد
# ======================================

@dp.message(F.text == "➕ اضافة قائد")
async def add_leader(message: Message, state: FSMContext):

    if message.from_user.id != OWNER_ID:
        return

    await message.answer(
        "🆔 ارسل ايدي القائد"
    )

    await state.set_state(AddLeader.user_id)


@dp.message(AddLeader.user_id)
async def save_leader(message: Message, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "INSERT OR IGNORE INTO leaders(user_id) VALUES(?)",
            (int(message.text),)
        )

        await db.commit()

    await message.answer(
        "✅ تم اضافة القائد"
    )

    await state.clear()

# ======================================
# حذف قائد
# ======================================

@dp.message(F.text == "➖ حذف قائد")
async def remove_leader(message: Message, state: FSMContext):

    if message.from_user.id != OWNER_ID:
        return

    await message.answer(
        "🆔 ارسل ايدي القائد"
    )

    await state.set_state(RemoveLeader.user_id)


@dp.message(RemoveLeader.user_id)
async def delete_leader(message: Message, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "DELETE FROM leaders WHERE user_id=?",
            (int(message.text),)
        )

        await db.commit()

    await message.answer(
        "✅ تم حذف القائد"
    )

    await state.clear()

# ======================================
# تشغيل
# ======================================

async def main():

    await setup_db()

    print("BOT RUNNING")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
