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
                text="تسجيل",
                callback_data="register"
            )
        ],
        [
            InlineKeyboardButton(
                text="عرض التيمات",
                callback_data="teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="بحث لاعب",
                callback_data="search"
            )
        ]
    ]

    if await is_leader(user_id):

        buttons.append([
            InlineKeyboardButton(
                text="الادارة",
                callback_data="admin_panel"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def admin_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="الطلبات",
                    callback_data="requests"
                )
            ],

            [
                InlineKeyboardButton(
                    text="فتح الانتقالات",
                    callback_data="open_transfers"
                )
            ],

            [
                InlineKeyboardButton(
                    text="غلق الانتقالات",
                    callback_data="close_transfers"
                )
            ],

            [
                InlineKeyboardButton(
                    text="اضافة قائد",
                    callback_data="add_leader"
                )
            ],

            [
                InlineKeyboardButton(
                    text="حذف قائد",
                    callback_data="remove_leader"
                )
            ],

            [
                InlineKeyboardButton(
                    text="رجوع",
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
<b>الاتحاد العراقي للكلانات</b>

اهلا وسهلا بك
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
        "القائمة الرئيسية",
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
        "لوحة الادارة",
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

    if old and not await transfers_open():

        return await callback.message.answer(
            "انت مسجل بالفعل"
        )

    if old and await transfers_open():

        async with aiosqlite.connect("union.db") as db:

            await db.execute(
                "DELETE FROM players WHERE user_id=?",
                (user_id,)
            )

            await db.commit()

    await callback.message.answer(
        "ارسل اسم التيم"
    )

    await state.set_state(Register.team)

# =========================================
# REGISTER STEPS
# =========================================

@dp.message(Register.team)
async def reg_team(message: Message, state: FSMContext):

    await state.update_data(team=message.text)

    await message.answer("ارسل اسم اللاعب")

    await state.set_state(Register.player)


@dp.message(Register.player)
async def reg_player(message: Message, state: FSMContext):

    await state.update_data(player=message.text)

    await message.answer("ارسل رابط الفيسبوك")

    await state.set_state(Register.facebook)


@dp.message(Register.facebook)
async def reg_facebook(message: Message, state: FSMContext):

    if not valid_facebook(message.text):

        return await message.answer(
            "رابط الفيسبوك غير صحيح"
        )

    await state.update_data(facebook=message.text)

    await message.answer("ارسل الرقم التسلسلي")

    await state.set_state(Register.phone)


@dp.message(Register.phone)
async def reg_phone(message: Message, state: FSMContext):

    await state.update_data(phone=message.text)

    await message.answer("ارسل سكرين الرقم التسلسلي")

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

    leaders = []

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT user_id FROM leaders"
        ) as cursor:

            rows = await cursor.fetchall()

            leaders = [x[0] for x in rows]

    text = f"""
طلب تسجيل جديد

التيم : {data['team']}
اللاعب : {data['player']}
الفيس : {data['facebook']}
الرقم : {data['phone']}
الايدي : {message.from_user.id}
"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="قبول",
                    callback_data=f"accept_{message.from_user.id}"
                ),

                InlineKeyboardButton(
                    text="رفض",
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
        "تم ارسال طلبك للمراجعة"
    )

    await state.clear()

# =========================================
# IF NOT PHOTO
# =========================================

@dp.message(Register.screenshot)
async def no_photo(message: Message):

    await message.answer(
        "يرجى ارسال صورة فقط"
    )
