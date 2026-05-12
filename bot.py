# ==============================
# IRAQ CLANS UNION BOT
# FULL PROFESSIONAL VERSION
# ==============================

import asyncio
import sqlite3
import re
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==============================
# BOT INFO
# ==============================

TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 653170487

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher(storage=MemoryStorage())

# ==============================
# DATABASE
# ==============================

db = sqlite3.connect("clans.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    team_name TEXT,
    player_name TEXT,
    facebook TEXT,
    serial TEXT,
    screenshot TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS leaders(
    user_id INTEGER UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    transfers INTEGER
)
""")

db.commit()

cursor.execute("SELECT * FROM settings")

if not cursor.fetchone():
    cursor.execute("""
    INSERT INTO settings VALUES (0)
    """)
    db.commit()

# ==============================
# STATES
# ==============================

class Register(StatesGroup):
    team = State()
    player = State()
    facebook = State()
    serial = State()
    screenshot = State()

# ==============================
# FUNCTIONS
# ==============================

def is_admin(user_id):

    if user_id == OWNER_ID:
        return True

    cursor.execute("""
    SELECT * FROM leaders
    WHERE user_id=?
    """, (user_id,))

    return cursor.fetchone() is not None

def valid_facebook(link):

    pattern = r"(https?:\/\/)?(www\.)?facebook\.com\/.+"

    return re.match(pattern, link)

# ==============================
# MENUS
# ==============================

def admin_menu():

    kb = InlineKeyboardBuilder()

    kb.button(
        text="الطلبات",
        callback_data="requests"
    )

    kb.button(
        text="عرض التيمات",
        callback_data="teams"
    )

    kb.button(
        text="بحث لاعب",
        callback_data="search"
    )

    kb.button(
        text="فتح الانتقالات",
        callback_data="open"
    )

    kb.button(
        text="غلق الانتقالات",
        callback_data="close"
    )

    kb.button(
        text="إضافة قائد",
        callback_data="addleader"
    )

    kb.button(
        text="حذف قائد",
        callback_data="removeleader"
    )

    kb.adjust(2)

    return kb.as_markup()

# ==============================
# START
# ==============================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):

    if is_admin(message.from_user.id):

        await message.answer(
            "لوحة التحكم",
            reply_markup=admin_menu()
        )

    text = """
اهلاً وسهلاً بك في الاتحاد العراقي للكلانات

يرجى ارسال اسم التيم
"""

    await message.answer(text)

    await state.set_state(Register.team)

# ==============================
# REGISTER
# ==============================

@dp.message(Register.team)
async def get_team(message: Message, state: FSMContext):

    await state.update_data(
        team=message.text
    )

    await message.answer(
        "ارسل اسم اللاعب"
    )

    await state.set_state(Register.player)

@dp.message(Register.player)
async def get_player(message: Message, state: FSMContext):

    await state.update_data(
        player=message.text
    )

    await message.answer(
        "ارسل رابط الفيسبوك"
    )

    await state.set_state(Register.facebook)

@dp.message(Register.facebook)
async def get_facebook(message: Message, state: FSMContext):

    if not valid_facebook(message.text):

        return await message.answer(
            "رابط الفيسبوك غير صالح"
        )

    await state.update_data(
        facebook=message.text
    )

    await message.answer(
        "ارسل الرقم التسلسلي"
    )

    await state.set_state(Register.serial)

@dp.message(Register.serial)
async def get_serial(message: Message, state: FSMContext):

    cursor.execute("""
    SELECT * FROM players
    WHERE serial=?
    """, (message.text,))

    if cursor.fetchone():

        return await message.answer(
            "الرقم مستخدم مسبقاً"
        )

    await state.update_data(
        serial=message.text
    )

    await message.answer(
        "ارسل صورة السكرين"
    )

    await state.set_state(Register.screenshot)

@dp.message(Register.screenshot, F.photo)
async def get_screenshot(message: Message, state: FSMContext):

    data = await state.get_data()

    file_id = message.photo[-1].file_id

    cursor.execute("""
    INSERT INTO players(
        user_id,
        team_name,
        player_name,
        facebook,
        serial,
        screenshot,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        data["team"],
        data["player"],
        data["facebook"],
        data["serial"],
        file_id,
        "pending"
    ))

    db.commit()

    text = f"""
طلب تسجيل جديد

التيم: {data['team']}

اللاعب: {data['player']}

الفيس: {data['facebook']}

الرقم: {data['serial']}
"""

    kb = InlineKeyboardMarkup(
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

    await bot.send_photo(
        OWNER_ID,
        photo=file_id,
        caption=text,
        reply_markup=kb
    )

    await message.answer(
        "تم ارسال طلبك"
    )

    await state.clear()

# ==============================
# ADMIN
# ==============================

@dp.message(F.text == "/admin")
async def admin(message: Message):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "لوحة التحكم",
        reply_markup=admin_menu()
    )

# ==============================
# REQUESTS
# ==============================

@dp.callback_query(F.data == "requests")
async def requests(callback: CallbackQuery):

    cursor.execute("""
    SELECT player_name,
           team_name,
           status
    FROM players
    """)

    data = cursor.fetchall()

    if not data:

        return await callback.message.answer(
            "لا توجد طلبات"
        )

    text = ""

    for p in data:

        text += f"""
اللاعب: {p[0]}

التيم: {p[1]}

الحالة: {p[2]}

--------------------
"""

    await callback.message.answer(text)

# ==============================
# TEAMS
# ==============================

@dp.callback_query(F.data == "teams")
async def teams(callback: CallbackQuery):

    cursor.execute("""
    SELECT DISTINCT team_name
    FROM players
    """)

    teams = cursor.fetchall()

    kb = InlineKeyboardBuilder()

    for team in teams:

        kb.button(
            text=team[0],
            callback_data=f"team_{team[0]}"
        )

    kb.adjust(1)

    await callback.message.answer(
        "قائمة التيمات",
        reply_markup=kb.as_markup()
    )

# ==============================
# TEAM PLAYERS
# ==============================

@dp.callback_query(F.data.startswith("team_"))
async def team_players(callback: CallbackQuery):

    team = callback.data.split("_")[1]

    cursor.execute("""
    SELECT player_name,
           facebook,
           serial,
           status
    FROM players
    WHERE team_name=?
    """, (team,))

    players = cursor.fetchall()

    text = f"{team}\n\n"

    for p in players:

        text += f"""
اللاعب: {p[0]}

الفيس: {p[1]}

الرقم: {p[2]}

الحالة: {p[3]}

--------------------
"""

    await callback.message.answer(text)

# ==============================
# ACCEPT
# ==============================

@dp.callback_query(F.data.startswith("accept_"))
async def accept(callback: CallbackQuery):

    user_id = int(
        callback.data.split("_")[1]
    )

    cursor.execute("""
    UPDATE players
    SET status='accepted'
    WHERE user_id=?
    """, (user_id,))

    db.commit()

    await bot.send_message(
        user_id,
        "تم قبول طلبك"
    )

    await callback.answer(
        "تم القبول"
    )

# ==============================
# REJECT
# ==============================

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery):

    user_id = int(
        callback.data.split("_")[1]
    )

    cursor.execute("""
    UPDATE players
    SET status='rejected'
    WHERE user_id=?
    """, (user_id,))

    db.commit()

    await bot.send_message(
        user_id,
        "تم رفض طلبك"
    )

    await callback.answer(
        "تم الرفض"
    )

# ==============================
# OPEN TRANSFERS
# ==============================

@dp.callback_query(F.data == "open")
async def open_transfer(callback: CallbackQuery):

    cursor.execute("""
    UPDATE settings
    SET transfers=1
    """)

    db.commit()

    await callback.message.answer(
        "تم فتح الانتقالات"
    )

# ==============================
# CLOSE TRANSFERS
# ==============================

@dp.callback_query(F.data == "close")
async def close_transfer(callback: CallbackQuery):

    cursor.execute("""
    UPDATE settings
    SET transfers=0
    """)

    db.commit()

    await callback.message.answer(
        "تم غلق الانتقالات"
    )

# ==============================
# ADD LEADER
# ==============================

@dp.callback_query(F.data == "addleader")
async def addleader_info(callback: CallbackQuery):

    await callback.message.answer(
        "ارسل:\n/addleader ID"
    )

@dp.message(F.text.startswith("/addleader"))
async def add_leader(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    try:

        user_id = int(
            message.text.split()[1]
        )

        cursor.execute("""
        INSERT INTO leaders(user_id)
        VALUES(?)
        """, (user_id,))

        db.commit()

        await message.answer(
            "تم اضافة القائد"
        )

    except:

        await message.answer(
            "خطأ"
        )

# ==============================
# REMOVE LEADER
# ==============================

@dp.callback_query(F.data == "removeleader")
async def removeleader_info(callback: CallbackQuery):

    await callback.message.answer(
        "ارسل:\n/removeleader ID"
    )

@dp.message(F.text.startswith("/removeleader"))
async def remove_leader(message: Message):

    if message.from_user.id != OWNER_ID:
        return

    try:

        user_id = int(
            message.text.split()[1]
        )

        cursor.execute("""
        DELETE FROM leaders
        WHERE user_id=?
        """, (user_id,))

        db.commit()

        await message.answer(
            "تم حذف القائد"
        )

    except:

        await message.answer(
            "خطأ"
        )

# ==============================
# SEARCH PLAYER
# ==============================

@dp.message(F.text.startswith("/search"))
async def search_player(message: Message):

    query = message.text.replace(
        "/search ",
        ""
    )

    cursor.execute("""
    SELECT team_name,
           player_name,
           facebook,
           serial,
           screenshot,
           status
    FROM players
    WHERE player_name LIKE ?
    OR facebook LIKE ?
    """, (
        f"%{query}%",
        f"%{query}%"
    ))

    result = cursor.fetchall()

    if not result:

        return await message.answer(
            "اللاعب غير موجود"
        )

    for r in result:

        text = f"""
التيم: {r[0]}

اللاعب: {r[1]}

الفيس: {r[2]}

الرقم: {r[3]}

الحالة: {r[5]}
"""

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=r[4],
            caption=text
        )

# ==============================
# SEARCH BUTTON
# ==============================

@dp.callback_query(F.data == "search")
async def search_help(callback: CallbackQuery):

    await callback.message.answer(
        "ابحث هكذا:\n/search اسم اللاعب"
    )

# ==============================
# RUN
# ==============================

async def main():

    print("BOT STARTED")

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
