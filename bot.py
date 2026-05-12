# ======================================
# IRAQ UNION BOT
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
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ======================================
# SETTINGS
# ======================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

# ======================================
# BOT
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
# STATES
# ======================================

class Register(StatesGroup):
    team = State()
    player = State()
    facebook = State()
    phone = State()
    screenshot = State()

class AddLeader(StatesGroup):
    user_id = State()

class RemoveLeader(StatesGroup):
    user_id = State()

# ======================================
# DATABASE
# ======================================

async def setup_db():

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
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

        await db.execute(
            "INSERT OR IGNORE INTO settings VALUES (?, ?)",
            ("transfers", "off")
        )

        await db.execute(
            "INSERT OR IGNORE INTO leaders VALUES (?)",
            (OWNER_ID,)
        )

        await db.commit()

# ======================================
# FUNCTIONS
# ======================================

async def is_leader(user_id):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM leaders WHERE user_id=?",
            (user_id,)
        ) as cursor:

            data = await cursor.fetchone()

            return data is not None

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
# MAIN MENU
# ======================================

async def main_menu(user_id):

    buttons = [

        [KeyboardButton(text="📋 تسجيل")],

        [KeyboardButton(text="🏆 عرض التيمات")]

    ]

    if await is_leader(user_id):

        buttons.append([
            KeyboardButton(text="🛠 الإدارة")
        ])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

# ======================================
# START
# ======================================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        """
<b>🇮🇶 الاتحاد العراقي للكلانات</b>

اهلاً وسهلاً بك ❤️
""",
        reply_markup=await main_menu(
            message.from_user.id
        )
    )

# ======================================
# REGISTER
# ======================================

@dp.message(F.text == "📋 تسجيل")
async def register(message: Message, state: FSMContext):

    await message.answer("🏆 ارسل اسم التيم")

    await state.set_state(Register.team)

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

    await message.answer("📱 ارسل الرقم التسلسلي")

    await state.set_state(Register.phone)

@dp.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):

    await state.update_data(phone=message.text)

    await message.answer("🖼 ارسل صورة الرقم التسلسلي")

    await state.set_state(Register.screenshot)

@dp.message(Register.screenshot, F.photo)
async def reg_screen(message: Message, state: FSMContext):

    data = await state.get_data()

    photo = message.photo[-1].file_id

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        INSERT INTO players
        (
            user_id,
            team,
            player_name,
            facebook,
            phone,
            screenshot,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
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

    await message.answer(
        "✅ تم ارسال طلبك وسيتم مراجعته"
    )

    await state.clear()

@dp.message(Register.screenshot)
async def only_photo(message: Message):

    await message.answer(
        "❌ يرجى ارسال صورة فقط"
    )

# ======================================
# TEAMS
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

    buttons = []

    for row in rows:

        buttons.append([

            InlineKeyboardButton(
                text=f"🏆 {row[0]}",
                callback_data=f"team_{row[0]}"
            )

        ])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await message.answer(
        "🏆 قائمة التيمات",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("team_"))
async def team_players(callback: CallbackQuery):

    team = callback.data.replace("team_", "")

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT player_name
        FROM players
        WHERE team=?
        AND status='accepted'
        """, (team,)) as cursor:

            rows = await cursor.fetchall()

    text = f"🏆 التيم : {team}\n\n"

    for row in rows:

        text += f"👤 {row[0]}\n"

    await callback.message.answer(text)

# ======================================
# ADMIN PANEL
# ======================================

@dp.message(F.text == "🛠 الإدارة")
async def admin_panel(message: Message):

    if not await is_leader(message.from_user.id):

        return await message.answer(
            "❌ للقادة فقط"
        )

    buttons = [

        [KeyboardButton(text="📥 الطلبات")],

        [KeyboardButton(text="🔓 فتح الانتقالات")],

        [KeyboardButton(text="🔒 غلق الانتقالات")]

    ]

    if message.from_user.id == OWNER_ID:

        buttons.append([
            KeyboardButton(text="➕ اضافة قائد")
        ])

        buttons.append([
            KeyboardButton(text="➖ حذف قائد")
        ])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await message.answer(
        "🛠 لوحة الإدارة",
        reply_markup=keyboard
    )

# ======================================
# REQUESTS
# ======================================

@dp.message(F.text == "📥 الطلبات")
async def requests(message: Message):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT *
        FROM players
        WHERE status='pending'
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ لا توجد طلبات"
        )

    for row in rows:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ قبول",
                        callback_data=f"accept_{row[1]}"
                    ),

                    InlineKeyboardButton(
                        text="❌ رفض",
                        callback_data=f"reject_{row[1]}"
                    )
                ]
            ]
        )

        await bot.send_photo(
            message.chat.id,
            row[6],
            caption=f"""
🏆 التيم : {row[2]}
👤 اللاعب : {row[3]}
""",
            reply_markup=keyboard
        )

# ======================================
# ACCEPT
# ======================================

@dp.callback_query(F.data.startswith("accept_"))
async def accept_player(callback: CallbackQuery):

    user_id = int(
        callback.data.split("_")[1]
    )

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "UPDATE players SET status='accepted' WHERE user_id=?",
            (user_id,)
        )

        await db.commit()

    await bot.send_message(
        user_id,
        "✅ تمت الموافقة على طلبك"
    )

    await callback.answer("تم القبول")

# ======================================
# REJECT
# ======================================

@dp.callback_query(F.data.startswith("reject_"))
async def reject_player(callback: CallbackQuery):

    user_id = int(
        callback.data.split("_")[1]
    )

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "UPDATE players SET status='rejected' WHERE user_id=?",
            (user_id,)
        )

        await db.commit()

    await bot.send_message(
        user_id,
        "❌ تم رفض طلبك"
    )

    await callback.answer("تم الرفض")

# ======================================
# OPEN TRANSFERS
# ======================================

@dp.message(F.text == "🔓 فتح الانتقالات")
async def open_transfer(message: Message):

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
# CLOSE TRANSFERS
# ======================================

@dp.message(F.text == "🔒 غلق الانتقالات")
async def close_transfer(message: Message):

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        UPDATE settings
        SET value='off'
        WHERE name='transfers'
        """)

        await db.commit()

    await message.answer(
        "🔒 تم غلق الانتقالات"
    )

# ======================================
# ADD LEADER
# ======================================

@dp.message(F.text == "➕ اضافة قائد")
async def add_leader(message: Message, state: FSMContext):

    if message.from_user.id != OWNER_ID:

        return

    await message.answer(
        "🆔 ارسل ايدي الشخص"
    )

    await state.set_state(AddLeader.user_id)

@dp.message(AddLeader.user_id)
async def save_leader(message: Message, state: FSMContext):

    user_id = int(message.text)

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "INSERT OR IGNORE INTO leaders VALUES (?)",
            (user_id,)
        )

        await db.commit()

    await message.answer(
        "✅ تم اضافة القائد"
    )

    await state.clear()

# ======================================
# REMOVE LEADER
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

    user_id = int(message.text)

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "DELETE FROM leaders WHERE user_id=?",
            (user_id,)
        )

        await db.commit()

    await message.answer(
        "✅ تم حذف القائد"
    )

    await state.clear()

# ======================================
# RUN
# ======================================

async def main():

    await setup_db()

    print("BOT IS RUNNING")

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
