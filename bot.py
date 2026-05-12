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
    CallbackQuery
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


def valid_facebook(url):

    pattern = r'(https?://)?(www\.)?(facebook|fb)\.com/.+'

    return re.match(pattern, url)

# ======================================
# MAIN MENU
# ======================================

async def main_menu(user_id):

    buttons = [

        [
            InlineKeyboardButton(
                text="📋 تسجيل",
                callback_data="register"
            )
        ],

        [
            InlineKeyboardButton(
                text="🏆 عرض التيمات",
                callback_data="teams"
            )
        ],

        [
            InlineKeyboardButton(
                text="🔎 بحث لاعب",
                callback_data="search"
            )
        ]

    ]

    if await is_leader(user_id):

        buttons.append([
            InlineKeyboardButton(
                text="📥 الطلبات",
                callback_data="requests"
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
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
        reply_markup=await main_menu(
            message.from_user.id
        )
    )

# ======================================
# REGISTER
# ======================================

@dp.callback_query(F.data == "register")
async def register(callback: CallbackQuery, state: FSMContext):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM players WHERE user_id=?",
            (callback.from_user.id,)
        ) as cursor:

            exists = await cursor.fetchone()

    if exists:

        return await callback.message.answer(
            "❌ انت مسجل مسبقاً داخل الاتحاد"
        )

    await callback.message.answer(
        "🏆 ارسل اسم التيم"
    )

    await state.set_state(Register.team)

# ======================================
# TEAM
# ======================================

@dp.message(Register.team)
async def reg_team(message: Message, state: FSMContext):

    await state.update_data(
        team=message.text
    )

    await message.answer(
        "👤 ارسل اسم اللاعب"
    )

    await state.set_state(Register.player)

# ======================================
# PLAYER
# ======================================

@dp.message(Register.player)
async def reg_player(message: Message, state: FSMContext):

    await state.update_data(
        player=message.text
    )

    await message.answer(
        "🌐 ارسل رابط الفيسبوك"
    )

    await state.set_state(Register.facebook)

# ======================================
# FACEBOOK
# ======================================

@dp.message(Register.facebook)
async def reg_facebook(message: Message, state: FSMContext):

    if not valid_facebook(message.text):

        return await message.answer(
            "❌ رابط الفيسبوك غير صحيح"
        )

    await state.update_data(
        facebook=message.text
    )

    await message.answer(
        "📱 ارسل الرقم التسلسلي"
    )

    await state.set_state(Register.phone)

# ======================================
# PHONE
# ======================================

@dp.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):

    await state.update_data(
        phone=message.text
    )

    await message.answer(
        "🖼 ارسل سكرين الرقم التسلسلي"
    )

    await state.set_state(Register.screenshot)

# ======================================
# NO PHOTO
# ======================================

@dp.message(Register.screenshot)
async def no_photo(message: Message):

    if not message.photo:

        await message.answer(
            "❌ يرجى ارسال صورة فقط"
        )

# ======================================
# SCREENSHOT
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
        "✅ تم ارسال طلبك الى القادة"
    )

    await state.clear()

# ======================================
# ACCEPT
# ======================================

@dp.callback_query(F.data.startswith("accept_"))
async def accept_player(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

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
        "✅ تم قبول طلبك داخل الاتحاد"
    )

    await callback.answer(
        "تم قبول اللاعب"
    )

# ======================================
# REJECT
# ======================================

@dp.callback_query(F.data.startswith("reject_"))
async def reject_player(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

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

    await callback.answer(
        "تم رفض اللاعب"
    )

# ======================================
# REQUESTS
# ======================================

@dp.callback_query(F.data == "requests")
async def requests(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM players WHERE status='pending'"
        ) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await callback.message.answer(
            "❌ لا توجد طلبات"
        )

    for row in rows:

        text = f"""
📥 طلب جديد

🏆 التيم : {row[2]}
👤 اللاعب : {row[3]}
🌐 الفيس : {row[4]}
📱 الرقم : {row[5]}
🆔 الايدي : {row[1]}
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
            callback.from_user.id,
            row[6],
            caption=text,
            reply_markup=keyboard
        )

# ======================================
# TEAMS
# ======================================

@dp.callback_query(F.data == "teams")
async def teams(callback: CallbackQuery):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT team, COUNT(*) as total
        FROM players
        WHERE status='accepted'
        GROUP BY team
        ORDER BY total DESC
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await callback.message.answer(
            "❌ لا توجد تيمات"
        )

    buttons = []

    for row in rows:

        buttons.append([

            InlineKeyboardButton(
                text=f"{row[0]} ({row[1]})",
                callback_data=f"team_{row[0]}"
            )

        ])

    await callback.message.answer(
        "🏆 قائمة التيمات",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

# ======================================
# TEAM PLAYERS
# ======================================

@dp.callback_query(F.data.startswith("team_"))
async def team_players(callback: CallbackQuery):

    team = callback.data.replace(
        "team_",
        ""
    )

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT player_name, facebook, phone
        FROM players
        WHERE team=? AND status='accepted'
        """, (team,)) as cursor:

            rows = await cursor.fetchall()

    text = f"🏆 التيم : {team}\n\n"

    for row in rows:

        text += f"👤 اللاعب : {row[0]}\n"
        text += f"🌐 الفيس : {row[1]}\n"
        text += f"📱 الرقم : {row[2]}\n"
        text += "━━━━━━━━━━\n"

    await callback.message.answer(text)

# ======================================
# SEARCH
# ======================================

@dp.callback_query(F.data == "search")
async def search(callback: CallbackQuery, state: FSMContext):

    await callback.message.answer(
        "🔎 ارسل اسم اللاعب او رابط الفيس"
    )

    await state.set_state(SearchPlayer.text)

# ======================================
# SEARCH RESULT
# ======================================

@dp.message(SearchPlayer.text)
async def search_player(message: Message, state: FSMContext):

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
# RUN
# ======================================

async def main():

    await setup_db()

    print("BOT IS RUNNING")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
