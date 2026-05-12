# ======================================
# IRAQ CLANS UNION BOT
# PROFESSIONAL VERSION
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
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

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

class EditInfo(StatesGroup):
    team = State()
    player = State()
    facebook = State()
    phone = State()
    screenshot = State()

class AddLeader(StatesGroup):
    user_id = State()

class RemoveLeader(StatesGroup):
    user_id = State()

class SearchPlayer(StatesGroup):
    text = State()

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
            "INSERT OR IGNORE INTO settings (name, value) VALUES (?, ?)",
            ("transfers", "off")
        )

        await db.execute(
            "INSERT OR IGNORE INTO leaders (user_id) VALUES (?)",
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
        [KeyboardButton(text="🏆 عرض التيمات")],
        [KeyboardButton(text="🔎 بحث لاعب")]

    ]

    if await transfers_open():

        buttons.append([
            KeyboardButton(text="✏️ تعديل معلوماتي")
        ])

    if await is_leader(user_id):

        buttons.append([
            KeyboardButton(text="📥 الطلبات")
        ])

        buttons.append([
            KeyboardButton(text="🔓 فتح الانتقالات")
        ])

        buttons.append([
            KeyboardButton(text="🔒 غلق الانتقالات")
        ])

    if user_id == OWNER_ID:

        buttons.append([
            KeyboardButton(text="➕ اضافة قائد")
        ])

        buttons.append([
            KeyboardButton(text="➖ حذف قائد")
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

    text = """
<b>🇮🇶 الاتحاد العراقي للكلانات</b>

اهلاً وسهلاً بك ❤️

يرجى تسجيل البيانات التالية:

🏆 اسم التيم
👤 اسم اللاعب
🌐 رابط الفيسبوك
📱 الرقم التسلسلي
🖼 سكرين الرقم التسلسلي

⚠️ اي معلومات وهمية تعرضك للحظر
"""

    await message.answer(
        text,
        reply_markup=await main_menu(message.from_user.id)
    )

# ======================================
# REGISTER
# ======================================

@dp.message(F.text == "📋 تسجيل")
async def register(message: Message, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM players WHERE user_id=?",
            (message.from_user.id,)
        ) as cursor:

            exists = await cursor.fetchone()

    if exists:

        return await message.answer(
            "❌ انت مسجل مسبقاً"
        )

    await message.answer(
        "🏆 ارسل اسم التيم"
    )

    await state.set_state(Register.team)

@dp.message(Register.team)
async def reg_team(message: Message, state: FSMContext):

    await state.update_data(team=message.text)

    await message.answer(
        "👤 ارسل اسم اللاعب"
    )

    await state.set_state(Register.player)

@dp.message(Register.player)
async def reg_player(message: Message, state: FSMContext):

    await state.update_data(player=message.text)

    await message.answer(
        "🌐 ارسل رابط الفيسبوك"
    )

    await state.set_state(Register.facebook)

@dp.message(Register.facebook)
async def reg_facebook(message: Message, state: FSMContext):

    if not valid_facebook(message.text):

        return await message.answer(
            "❌ رابط الفيسبوك غير صحيح"
        )

    await state.update_data(facebook=message.text)

    await message.answer(
        "📱 ارسل الرقم التسلسلي"
    )

    await state.set_state(Register.phone)

@dp.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):

    await state.update_data(phone=message.text)

    await message.answer(
        "🖼 ارسل سكرين الرقم التسلسلي"
    )

    await state.set_state(Register.screenshot)

# ======================================
# SAVE REGISTER
# ======================================

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
            data['team'],
            data['player'],
            data['facebook'],
            data['phone'],
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ قبول",
                    callback_data=f"accept_{message.from_user.id}"
                ),

                InlineKeyboardButton(
                    text="❌ رفض",
                    callback_data=f"reject_{message.from_user.id}"
                )
            ]
        ]
    )

    for leader in leaders:

        try:

            await bot.send_photo(
                leader,
                photo,
                caption=text,
                reply_markup=keyboard
            )

        except:
            pass

    await message.answer(
        "✅ سيتم مراجعة طلبك من قبل القادة"
    )

    await state.clear()

# ======================================
# NO PHOTO
# ======================================

@dp.message(Register.screenshot, ~F.photo)
async def no_photo(message: Message):

    if message.text in [
        "📥 الطلبات",
        "🏆 عرض التيمات",
        "🔎 بحث لاعب",
        "🔓 فتح الانتقالات",
        "🔒 غلق الانتقالات"
    ]:
        return

    await message.answer(
        "❌ يرجى ارسال صورة فقط"
    )

# ======================================
# ACCEPT
# ======================================

@dp.callback_query(F.data.startswith("accept_"))
async def accept_player(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[1])

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

    if not await is_leader(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[1])

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
# REQUESTS
# ======================================

@dp.message(F.text == "📥 الطلبات")
async def requests(message: Message):

    if not await is_leader(message.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM players WHERE status='pending'"
        ) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ لا توجد طلبات"
        )

    for row in rows:

        text = f"""
📥 طلب جديد

🏆 التيم : {row[2]}
👤 اللاعب : {row[3]}
🌐 الفيس : {row[4]}
📱 الرقم : {row[5]}
"""

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
            caption=text,
            reply_markup=keyboard
        )

# ======================================
# TEAMS
# ======================================

@dp.message(F.text == "🏆 عرض التيمات")
async def teams(message: Message):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT team, COUNT(*)
        FROM players
        WHERE status='accepted'
        GROUP BY team
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ لا توجد تيمات"
        )

    text = "🏆 قائمة التيمات\n\n"

    for row in rows:

        text += f"🏅 {row[0]} ({row[1]})\n"

    await message.answer(text)

# ======================================
# SEARCH
# ======================================

@dp.message(F.text == "🔎 بحث لاعب")
async def search(message: Message, state: FSMContext):

    await message.answer(
        "🔎 ارسل اسم اللاعب او رابط الفيس"
    )

    await state.set_state(SearchPlayer.text)

@dp.message(SearchPlayer.text)
async def search_player(message: Message, state: FSMContext):

    if not message.text:
        return

    text = message.text

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT team, player_name, facebook, phone, status
        FROM players
        WHERE player_name LIKE ?
        OR facebook LIKE ?
        """, (

            f"%{text}%",
            f"%{text}%"

        )) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await message.answer(
            "❌ لم يتم العثور على اللاعب"
        )

    result = ""

    for row in rows:

        result += f"🏆 التيم : {row[0]}\n"
        result += f"👤 اللاعب : {row[1]}\n"
        result += f"🌐 الفيس : {row[2]}\n"
        result += f"📱 الرقم : {row[3]}\n"
        result += f"📌 الحالة : {row[4]}\n"
        result += "━━━━━━━━━━\n"

    await message.answer(result)

    await state.clear()

# ======================================
# OPEN TRANSFERS
# ======================================

@dp.message(F.text == "🔓 فتح الانتقالات")
async def open_transfers(message: Message):

    if not await is_leader(message.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "UPDATE settings SET value='on' WHERE name='transfers'"
        )

        await db.commit()

    await message.answer(
        "✅ تم فتح الانتقالات"
    )

# ======================================
# CLOSE TRANSFERS
# ======================================

@dp.message(F.text == "🔒 غلق الانتقالات")
async def close_transfers(message: Message):

    if not await is_leader(message.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "UPDATE settings SET value='off' WHERE name='transfers'"
        )

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
        "➕ ارسل ايدي القائد"
    )

    await state.set_state(AddLeader.user_id)

@dp.message(AddLeader.user_id)
async def save_leader(message: Message, state: FSMContext):

    if not message.text.isdigit():

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

    user_id = int(message.text)

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "INSERT OR IGNORE INTO leaders (user_id) VALUES (?)",
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
        "➖ ارسل ايدي القائد"
    )

    await state.set_state(RemoveLeader.user_id)

@dp.message(RemoveLeader.user_id)
async def delete_leader(message: Message, state: FSMContext):

    if not message.text.isdigit():

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

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
