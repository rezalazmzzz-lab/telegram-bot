# ==============================
# IRAQ CLANS UNION BOT
# FULL FIXED VERSION
# ==============================

import os
import re
import sqlite3
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from aiogram.filters import CommandStart

# ==============================
# TOKEN
# ==============================

TOKEN = os.getenv("BOT_TOKEN")

# ==============================
# BOT
# ==============================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ==============================
# DATABASE
# ==============================

db = sqlite3.connect("union.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS players(
    user_id INTEGER,
    team TEXT,
    player TEXT,
    fb TEXT,
    serial TEXT,
    photo TEXT,
    status TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS captains(
    user_id INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
    id INTEGER PRIMARY KEY,
    transfers INTEGER
)
""")

db.commit()

cur.execute("SELECT * FROM settings WHERE id=1")
if not cur.fetchone():
    cur.execute("INSERT INTO settings VALUES(1,0)")
    db.commit()

# ==============================
# STATES
# ==============================

users = {}

# ==============================
# MENUS
# ==============================

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 تسجيل")],
        [KeyboardButton(text="🏆 عرض التيمات")],
        [KeyboardButton(text="🔍 بحث لاعب")],
        [KeyboardButton(text="🛠 الإدارة")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
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

# ==============================
# START
# ==============================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇮🇶 <b>الاتحاد العراقي للتيمات</b>\n\n"
        "اهلاً وسهلاً بك ❤️",
        reply_markup=main_kb
    )

# ==============================
# رجوع
# ==============================

@dp.message(F.text == "🏠 رجوع")
async def back(message: Message):
    await message.answer(
        "🏠 القائمة الرئيسية",
        reply_markup=main_kb
    )

# ==============================
# الإدارة
# ==============================

@dp.message(F.text == "🛠 الإدارة")
async def admin_panel(message: Message):

    cur.execute(
        "SELECT * FROM captains WHERE user_id=?",
        (message.from_user.id,)
    )

    if not cur.fetchone():
        return await message.answer("❌ هذا القسم للقادة فقط")

    await message.answer(
        "🛠 لوحة الإدارة",
        reply_markup=admin_kb
    )

# ==============================
# فتح الانتقالات
# ==============================

@dp.message(F.text == "🔓 فتح الانتقالات")
async def open_transfer(message: Message):

    cur.execute(
        "SELECT * FROM captains WHERE user_id=?",
        (message.from_user.id,)
    )

    if not cur.fetchone():
        return

    cur.execute(
        "UPDATE settings SET transfers=1 WHERE id=1"
    )

    db.commit()

    await message.answer("✅ تم فتح الانتقالات")

# ==============================
# غلق الانتقالات
# ==============================

@dp.message(F.text == "🔒 غلق الانتقالات")
async def close_transfer(message: Message):

    cur.execute(
        "SELECT * FROM captains WHERE user_id=?",
        (message.from_user.id,)
    )

    if not cur.fetchone():
        return

    cur.execute(
        "UPDATE settings SET transfers=0 WHERE id=1"
    )

    db.commit()

    await message.answer("✅ تم غلق الانتقالات")

# ==============================
# اضافة قائد
# ==============================

@dp.message(F.text == "➕ اضافة قائد")
async def add_cap(message: Message):

    users[message.from_user.id] = {"state": "add_cap"}

    await message.answer(
        "➕ ارسل ايدي القائد"
    )

@dp.message()
async def all_messages(message: Message):

    uid = message.from_user.id

    if uid not in users:
        return

    state = users[uid]["state"]

    # ==========================
    # ADD CAPTAIN
    # ==========================

    if state == "add_cap":

        try:
            target = int(message.text)

            cur.execute(
                "INSERT INTO captains VALUES(?)",
                (target,)
            )

            db.commit()

            await message.answer(
                "✅ تمت اضافة القائد"
            )

        except:
            await message.answer(
                "❌ ايدي غير صالح"
            )

        users.pop(uid)

    # ==========================
    # DELETE CAPTAIN
    # ==========================

    elif state == "del_cap":

        try:
            target = int(message.text)

            cur.execute(
                "DELETE FROM captains WHERE user_id=?",
                (target,)
            )

            db.commit()

            await message.answer(
                "✅ تم حذف القائد"
            )

        except:
            await message.answer(
                "❌ خطأ"
            )

        users.pop(uid)

    # ==========================
    # SEARCH PLAYER
    # ==========================

    elif state == "search":

        name = message.text

        cur.execute(
            "SELECT * FROM players WHERE player LIKE ? AND status='accepted'",
            (f"%{name}%",)
        )

        data = cur.fetchone()

        if not data:
            await message.answer("❌ اللاعب غير موجود")
            users.pop(uid)
            return

        text = (
            f"🏆 التيم: {data[1]}\n"
            f"👤 اللاعب: {data[2]}\n"
            f"🔗 الفيس: {data[3]}\n"
            f"📱 الرقم: {data[4]}"
        )

        await message.answer(text)

        users.pop(uid)

    # ==========================
    # REGISTER
    # ==========================

    elif state == "team":

        users[uid]["team"] = message.text
        users[uid]["state"] = "player"

        await message.answer("👤 ارسل اسم اللاعب")

    elif state == "player":

        users[uid]["player"] = message.text
        users[uid]["state"] = "fb"

        await message.answer("🔗 ارسل رابط الفيس")

    elif state == "fb":

        if "facebook.com" not in message.text:
            return await message.answer(
                "❌ رابط غير صالح"
            )

        users[uid]["fb"] = message.text
        users[uid]["state"] = "serial"

        await message.answer(
            "📱 ارسل الرقم التسلسلي"
        )

    elif state == "serial":

        users[uid]["serial"] = message.text
        users[uid]["state"] = "photo"

        await message.answer(
            "🖼 ارسل سكرين الرقم التسلسلي"
        )

# ==============================
# حذف قائد
# ==============================

@dp.message(F.text == "➖ حذف قائد")
async def del_cap(message: Message):

    users[message.from_user.id] = {"state": "del_cap"}

    await message.answer(
        "➖ ارسل ايدي القائد"
    )

# ==============================
# بحث لاعب
# ==============================

@dp.message(F.text == "🔍 بحث لاعب")
async def search(message: Message):

    users[message.from_user.id] = {"state": "search"}

    await message.answer(
        "🔍 ارسل اسم اللاعب"
    )

# ==============================
# تسجيل
# ==============================

@dp.message(F.text == "📄 تسجيل")
async def register(message: Message):

    cur.execute(
        "SELECT transfers FROM settings WHERE id=1"
    )

    transfers = cur.fetchone()[0]

    cur.execute(
        "SELECT * FROM players WHERE user_id=? AND status='accepted'",
        (message.from_user.id,)
    )

    old = cur.fetchone()

    if old and transfers == 0:
        return await message.answer(
            "❌ انت مسجل بالفعل"
        )

    if old and transfers == 1:
        cur.execute(
            "DELETE FROM players WHERE user_id=?",
            (message.from_user.id,)
        )
        db.commit()

    users[message.from_user.id] = {"state": "team"}

    await message.answer(
        "🏆 ارسل اسم التيم"
    )

# ==============================
# PHOTO
# ==============================

@dp.message(F.photo)
async def photo(message: Message):

    uid = message.from_user.id

    if uid not in users:
        return

    if users[uid]["state"] != "photo":
        return

    photo = message.photo[-1].file_id

    data = users[uid]

    cur.execute("""
    INSERT INTO players VALUES(?,?,?,?,?,?,?)
    """, (
        uid,
        data["team"],
        data["player"],
        data["fb"],
        data["serial"],
        photo,
        "pending"
    ))

    db.commit()

    caption = (
        f"📥 طلب جديد\n\n"
        f"🏆 التيم: {data['team']}\n"
        f"👤 اللاعب: {data['player']}\n"
        f"🔗 الفيس:\n{data['fb']}\n"
        f"📱 الرقم: {data['serial']}"
    )

    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ قبول",
                    callback_data=f"acc_{uid}"
                ),
                InlineKeyboardButton(
                    text="❌ رفض",
                    callback_data=f"rej_{uid}"
                )
            ]
        ]
    )

    cur.execute("SELECT user_id FROM captains")

    caps = cur.fetchall()

    for c in caps:
        try:
            await bot.send_photo(
                c[0],
                photo,
                caption=caption,
                reply_markup=buttons
            )
        except:
            pass

    await message.answer(
        "✅ تم ارسال طلبك للمراجعة"
    )

    users.pop(uid)

# ==============================
# الطلبات
# ==============================

@dp.message(F.text == "📥 الطلبات")
async def requests(message: Message):

    cur.execute(
        "SELECT * FROM players WHERE status='pending'"
    )

    rows = cur.fetchall()

    if not rows:
        return await message.answer(
            "❌ لا توجد طلبات"
        )

    for row in rows:

        text = (
            f"🏆 التيم: {row[1]}\n"
            f"👤 اللاعب: {row[2]}\n"
            f"🔗 الفيس:\n{row[3]}\n"
            f"📱 الرقم: {row[4]}"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ قبول",
                        callback_data=f"acc_{row[0]}"
                    ),
                    InlineKeyboardButton(
                        text="❌ رفض",
                        callback_data=f"rej_{row[0]}"
                    )
                ]
            ]
        )

        await message.answer_photo(
            row[5],
            caption=text,
            reply_markup=kb
        )

# ==============================
# قبول
# ==============================

@dp.callback_query(F.data.startswith("acc_"))
async def accept(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    cur.execute(
        "UPDATE players SET status='accepted' WHERE user_id=?",
        (uid,)
    )

    db.commit()

    await bot.send_message(
        uid,
        "✅ تمت الموافقة على طلبك"
    )

    await call.message.edit_caption(
        caption="✅ accepted"
    )

# ==============================
# رفض
# ==============================

@dp.callback_query(F.data.startswith("rej_"))
async def reject(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    cur.execute(
        "DELETE FROM players WHERE user_id=?",
        (uid,)
    )

    db.commit()

    await bot.send_message(
        uid,
        "❌ تم رفض طلبك"
    )

    await call.message.edit_caption(
        caption="❌ rejected"
    )

# ==============================
# عرض التيمات
# ==============================

@dp.message(F.text == "🏆 عرض التيمات")
async def teams(message: Message):

    cur.execute(
        "SELECT DISTINCT team FROM players WHERE status='accepted'"
    )

    teams = cur.fetchall()

    if not teams:
        return await message.answer(
            "❌ لا توجد تيمات"
        )

    keyboard = []

    for t in teams:
        keyboard.append([
            InlineKeyboardButton(
                text=t[0],
                callback_data=f"team_{t[0]}"
            )
        ])

    kb = InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )

    await message.answer(
        "🏆 قائمة التيمات",
        reply_markup=kb
    )

# ==============================
# TEAM INFO
# ==============================

@dp.callback_query(F.data.startswith("team_"))
async def team_info(call: CallbackQuery):

    team = call.data.replace("team_", "")

    cur.execute(
        "SELECT * FROM players WHERE team=? AND status='accepted'",
        (team,)
    )

    rows = cur.fetchall()

    text = f"🏆 التيم: {team}\n\n"

    for r in rows:

        text += (
            f"👤 {r[2]}\n"
            f"🔗 {r[3]}\n"
            f"📱 {r[4]}\n\n"
        )

    await call.message.answer(text)

# ==============================
# RUN
# ==============================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
