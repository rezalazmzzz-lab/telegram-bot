# =========================================
# IRAQ CLANS UNION BOT
# FULL PROFESSIONAL VERSION
# =========================================

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

# =========================================
# TOKEN
# =========================================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 653170487

# =========================================
# BOT
# =========================================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =========================================
# STATES
# =========================================

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

# =========================================
# DATABASE
# =========================================

async def setup_db():

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
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

        await db.execute("""
        INSERT OR IGNORE INTO settings (name, value)
        VALUES ('transfers', 'off')
        """)

        await db.execute("""
        INSERT OR IGNORE INTO leaders (user_id)
        VALUES (?)
        """, (OWNER_ID,))

        await db.commit()

# =========================================
# FUNCTIONS
# =========================================

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

    pattern = r"(https?://)?(www\.)?(facebook|fb)\.com/.+"

    return re.match(pattern, url)

# =========================================
# MENUS
# =========================================

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
                text="🛠 الإدارة",
                callback_data="admin_panel"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def admin_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📥 الطلبات",
                    callback_data="requests"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔓 فتح الانتقالات",
                    callback_data="open_transfers"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🔒 غلق الانتقالات",
                    callback_data="close_transfers"
                )
            ],

            [
                InlineKeyboardButton(
                    text="➕ اضافة قائد",
                    callback_data="add_leader"
                )
            ],

            [
                InlineKeyboardButton(
                    text="➖ حذف قائد",
                    callback_data="remove_leader"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ رجوع",
                    callback_data="back_main"
                )
            ]
        ]
    )

# =========================================
# START
# =========================================

@dp.message(CommandStart())
async def start(message: Message):

    text = """
<b>🇮🇶 الاتحاد العراقي للكلانات</b>

اهلا وسهلا بك ❤️
"""

    await message.answer(
        text,
        reply_markup=await main_menu(message.from_user.id)
    )

# =========================================
# BACK
# =========================================

@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):

    await callback.message.answer(
        "🏠 القائمة الرئيسية",
        reply_markup=await main_menu(callback.from_user.id)
    )

# =========================================
# ADMIN
# =========================================

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    await callback.message.answer(
        "🛠 لوحة الإدارة",
        reply_markup=await admin_menu()
    )

# =========================================
# REGISTER
# =========================================

@dp.callback_query(F.data == "register")
async def register(callback: CallbackQuery, state: FSMContext):

    user_id = callback.from_user.id

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT * FROM players WHERE user_id=?",
            (user_id,)
        ) as cursor:

            old = await cursor.fetchone()

    # اذا مسجل والانتقالات مغلقة
    if old and not await transfers_open():

        return await callback.message.answer(
            "❌ انت مسجل بالفعل"
        )

    # اذا الانتقالات مفتوحة نحذف القديم
    if old and await transfers_open():

        async with aiosqlite.connect("union.db") as db:

            await db.execute(
                "DELETE FROM players WHERE user_id=?",
                (user_id,)
            )

            await db.commit()

    await callback.message.answer(
        "🏆 ارسل اسم التيم"
    )

    await state.set_state(Register.team)

# =========================================
# REGISTER STEPS
# =========================================

@dp.message(Register.team)
async def reg_team(message: Message, state: FSMContext):

    await state.update_data(team=message.text)

    await message.answer("👤 ارسل اسم اللاعب")

    await state.set_state(Register.player)


@dp.message(Register.player)
async def reg_player(message: Message, state: FSMContext):

    await state.update_data(player=message.text)

    await message.answer("🌐 ارسل رابط الفيسبوك")

    await state.set_state(Register.facebook)


@dp.message(Register.facebook)
async def reg_facebook(message: Message, state: FSMContext):

    if not valid_facebook(message.text):

        return await message.answer(
            "❌ رابط الفيسبوك غير صحيح"
        )

    await state.update_data(facebook=message.text)

    await message.answer("📱 ارسل الرقم التسلسلي")

    await state.set_state(Register.phone)


@dp.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):

    await state.update_data(phone=message.text)

    await message.answer("🖼 ارسل سكرين الرقم التسلسلي")

    await state.set_state(Register.screenshot)

# =========================================
# SCREENSHOT
# =========================================

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

    # القادة
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
        "✅ تم ارسال طلبك للمراجعة"
    )

    await state.clear()

# =========================================
# IF NOT PHOTO
# =========================================

@dp.message(Register.screenshot)
async def no_photo(message: Message):

    await message.answer(
        "❌ يرجى ارسال صورة فقط"
    )

# =========================================
# ACCEPT
# =========================================

@dp.callback_query(F.data.startswith("accept_"))
async def accept(callback: CallbackQuery):

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

# =========================================
# REJECT
# =========================================

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "DELETE FROM players WHERE user_id=?",
            (user_id,)
        )

        await db.commit()

    await bot.send_message(
        user_id,
        "❌ تم رفض طلبك"
    )

    await callback.answer("تم الرفض")

# =========================================
# REQUESTS
# =========================================

@dp.callback_query(F.data == "requests")
async def requests(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT team, player_name
        FROM players
        WHERE status='pending'
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await callback.message.answer(
            "❌ لا توجد طلبات"
        )

    text = "📥 الطلبات الحالية\n\n"

    for row in rows:

        text += f"🏆 {row[0]} - 👤 {row[1]}\n"

    await callback.message.answer(text)

# =========================================
# TEAMS
# =========================================

@dp.callback_query(F.data == "teams")
async def teams(callback: CallbackQuery):

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT DISTINCT team
        FROM players
        WHERE status='accepted'
        """) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        return await callback.message.answer(
            "❌ لا توجد تيمات"
        )

    buttons = []

    for row in rows:

        team = row[0]

        buttons.append([
            InlineKeyboardButton(
                text=f"🏆 {team}",
                callback_data=f"team_{team}"
            )
        ])

    await callback.message.answer(
        "🏆 قائمة التيمات",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

# =========================================
# TEAM PLAYERS
# =========================================

@dp.callback_query(F.data.startswith("team_"))
async def team_players(callback: CallbackQuery):

    team = callback.data.replace("team_", "")

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT player_name, facebook, phone
        FROM players
        WHERE team=? AND status='accepted'
        """, (team,)) as cursor:

            rows = await cursor.fetchall()

    text = f"🏆 التيم : {team}\n\n"

    for row in rows:

        text += f"""
👤 اللاعب : {row[0]}
🌐 الفيس : {row[1]}
📱 الرقم : {row[2]}
━━━━━━━━━━━━
"""

    await callback.message.answer(text)

# =========================================
# SEARCH
# =========================================

@dp.callback_query(F.data == "search")
async def search(callback: CallbackQuery, state: FSMContext):

    await callback.message.answer(
        "🔎 ارسل اسم اللاعب او رابط الفيس"
    )

    await state.set_state(SearchPlayer.text)


@dp.message(SearchPlayer.text)
async def do_search(message: Message, state: FSMContext):

    text = message.text

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT team, player_name, facebook, phone
        FROM players
        WHERE player_name LIKE ?
        OR facebook LIKE ?
        """, (
            f"%{text}%",
            f"%{text}%"
        )) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        await message.answer(
            "❌ لم يتم العثور على اللاعب"
        )

        return

    result = ""

    for row in rows:

        result += f"""
🏆 التيم : {row[0]}
👤 اللاعب : {row[1]}
🌐 الفيس : {row[2]}
📱 الرقم : {row[3]}
━━━━━━━━━━━━
"""

    await message.answer(result)

    await state.clear()

# =========================================
# OPEN TRANSFERS
# =========================================

@dp.callback_query(F.data == "open_transfers")
async def open_transfers(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        UPDATE settings
        SET value='on'
        WHERE name='transfers'
        """)

        await db.commit()

    await callback.message.answer(
        "✅ تم فتح الانتقالات"
    )

# =========================================
# CLOSE TRANSFERS
# =========================================

@dp.callback_query(F.data == "close_transfers")
async def close_transfers(callback: CallbackQuery):

    if not await is_leader(callback.from_user.id):
        return

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        UPDATE settings
        SET value='off'
        WHERE name='transfers'
        """)

        await db.commit()

    await callback.message.answer(
        "✅ تم غلق الانتقالات"
    )

# =========================================
# ADD LEADER
# =========================================

@dp.callback_query(F.data == "add_leader")
async def add_leader(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != OWNER_ID:
        return

    await callback.message.answer(
        "➕ ارسل ايدي القائد"
    )

    await state.set_state(AddLeader.user_id)


@dp.message(AddLeader.user_id)
async def save_leader(message: Message, state: FSMContext):

    try:

        user_id = int(message.text)

    except:

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        INSERT OR IGNORE INTO leaders (user_id)
        VALUES (?)
        """, (user_id,))

        await db.commit()

    await message.answer(
        "✅ تم اضافة القائد"
    )

    await state.clear()

# =========================================
# REMOVE LEADER
# =========================================

@dp.callback_query(F.data == "remove_leader")
async def remove_leader(callback: CallbackQuery, state: FSMContext):

    if callback.from_user.id != OWNER_ID:
        return

    await callback.message.answer(
        "➖ ارسل ايدي القائد"
    )

    await state.set_state(RemoveLeader.user_id)


@dp.message(RemoveLeader.user_id)
async def delete_leader(message: Message, state: FSMContext):

    try:

        user_id = int(message.text)

    except:

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

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

# =========================================
# RUN
# =========================================

async def main():

    await setup_db()

    print("BOT IS RUNNING")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
