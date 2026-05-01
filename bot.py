import sqlite3
import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 653170487

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

# ================= DATABASE =================
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS owners (id INTEGER, name TEXT, fb TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS clubs (name TEXT, owner_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS players (name TEXT, fb TEXT, serial TEXT UNIQUE, device TEXT, club TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS requests (name TEXT, fb TEXT, serial TEXT, device TEXT, club TEXT)")
conn.commit()

cur.execute("INSERT OR IGNORE INTO admins VALUES (?)", (ADMIN_ID,))
conn.commit()

# ================= FUNCTIONS =================

def is_admin(i): return cur.execute("SELECT 1 FROM admins WHERE id=?", (i,)).fetchone()
def is_leader(i): return cur.execute("SELECT 1 FROM leaders WHERE id=?", (i,)).fetchone()
def is_owner(i): return cur.execute("SELECT 1 FROM clubs WHERE owner_id=?", (i,)).fetchone()

# 🔥 تحقق فيسبوك
def valid_fb(link):
    if not link.startswith("http"):
        return False, "❌ لازم الرابط يبدأ بـ https://"

    if not re.match(r"https?:\/\/(www\.)?(facebook\.com|fb\.com)\/[A-Za-z0-9\.]+", link):
        return False, "❌ هذا مو رابط فيسبوك صحيح"

    if "profile.php" in link:
        return False, "❌ رابط غير مقبول"

    try:
        r = requests.get(link, timeout=5)
        if r.status_code != 200:
            return False, "❌ الرابط غير موجود"
    except:
        return False, "❌ فشل التحقق من الرابط"

    return True, "ok"

# ================= MENU =================

def menu(uid):
    if is_admin(uid):
        return [
            ["👑 إدارة القادة"],
            ["🏟️ إدارة الأندية"],
            ["📥 الطلبات"],
            ["🔍 بحث لاعب"]
        ]
    if is_leader(uid):
        return [
            ["📥 الطلبات"],
            ["🏟️ عرض الأندية"],
            ["🔍 بحث لاعب"]
        ]
    if is_owner(uid):
        return [
            ["➕ لاعب"],
            ["📋 لاعبين النادي"],
            ["🔍 بحث لاعب"]
        ]
    return [["🔍 بحث لاعب"]]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)",(uid,))
    conn.commit()

    await update.message.reply_text("🎮 بوت اتحاد PES", reply_markup=ReplyKeyboardMarkup(menu(uid), resize_keyboard=True))

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    uid = update.effective_user.id
    s = context.user_data.get("s")

    # إدارة القادة
    if t=="👑 إدارة القادة":
        return await update.message.reply_text("اختر", reply_markup=ReplyKeyboardMarkup([["➕ قائد","➖ قائد"],["⬅️ رجوع"]], resize_keyboard=True))

    if t=="➕ قائد" and is_admin(uid):
        context.user_data["s"]="add_leader"
        return await update.message.reply_text("ارسل ID")

    if s=="add_leader":
        if not t.isdigit():
            return await update.message.reply_text("❌ ايدي غلط")

        if not cur.execute("SELECT 1 FROM users WHERE id=?",(int(t),)).fetchone():
            return await update.message.reply_text("❌ هذا المستخدم ما داخل البوت")

        cur.execute("INSERT INTO leaders VALUES (?)",(int(t),))
        conn.commit()
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إضافة قائد")

    # إدارة الأندية
    if t=="🏟️ إدارة الأندية":
        return await update.message.reply_text("اختر", reply_markup=ReplyKeyboardMarkup([["➕ إضافة نادي"],["🏟️ عرض الأندية"],["⬅️ رجوع"]], resize_keyboard=True))

    if t=="➕ إضافة نادي":
        context.user_data["s"]="club_owner_id"
        return await update.message.reply_text("ID رئيس النادي")

    if s=="club_owner_id":
        if not t.isdigit():
            return await update.message.reply_text("❌ ايدي غلط")

        if not cur.execute("SELECT 1 FROM users WHERE id=?",(int(t),)).fetchone():
            return await update.message.reply_text("❌ المستخدم ما دايس /start")

        context.user_data["owner_id"]=int(t)
        context.user_data["s"]="club_owner_name"
        return await update.message.reply_text("اسم الرئيس")

    if s=="club_owner_name":
        context.user_data["owner_name"]=t
        context.user_data["s"]="club_owner_fb"
        return await update.message.reply_text("رابط الفيس")

    if s=="club_owner_fb":
        ok,msg = valid_fb(t)
        if not ok:
            return await update.message.reply_text(msg)

        context.user_data["owner_fb"]=t
        context.user_data["s"]="club_name"
        return await update.message.reply_text("اسم النادي")

    if s=="club_name":
        cur.execute("INSERT INTO clubs VALUES (?,?)",(t,context.user_data["owner_id"]))
        cur.execute("INSERT INTO owners VALUES (?,?,?)",
                    (context.user_data["owner_id"],context.user_data["owner_name"],context.user_data["owner_fb"]))
        conn.commit()

        await update.message.reply_text("✅ تم إنشاء النادي")
        context.user_data.clear()

    # عرض الأندية
    if t=="🏟️ عرض الأندية":
        clubs = cur.execute("SELECT * FROM clubs").fetchall()

        for c in clubs:
            owner = cur.execute("SELECT * FROM owners WHERE id=?",(c[1],)).fetchone()

            kb=[[InlineKeyboardButton("👥 عرض اللاعبين", callback_data=f"players_{c[0]}")]]

            await update.message.reply_text(f"""
🏟️ {c[0]}
👤 {owner[1]}
🔗 {owner[2]}
""", reply_markup=InlineKeyboardMarkup(kb))

    # إضافة لاعب
    if t=="➕ لاعب" and is_owner(uid):
        context.user_data["s"]="p_name"
        return await update.message.reply_text("اسم اللاعب")

    if s=="p_name":
        context.user_data["name"]=t
        context.user_data["s"]="p_fb"
        return await update.message.reply_text("رابط الفيس")

    if s=="p_fb":
        ok,msg = valid_fb(t)
        if not ok:
            return await update.message.reply_text(msg)

        context.user_data["fb"]=t
        context.user_data["s"]="p_serial"
        return await update.message.reply_text("الرقم التسلسلي")

    if s=="p_serial":
        if cur.execute("SELECT * FROM players WHERE serial=?",(t,)).fetchone():
            return await update.message.reply_text("❌ لاعب موجود")

        context.user_data["serial"]=t
        context.user_data["s"]="p_device"
        return await update.message.reply_text("نوع الجهاز")

    if s=="p_device":
        club = cur.execute("SELECT name FROM clubs WHERE owner_id=?",(uid,)).fetchone()[0]

        cur.execute("INSERT INTO requests VALUES (?,?,?,?,?)",
                    (context.user_data["name"],context.user_data["fb"],context.user_data["serial"],t,club))
        conn.commit()

        context.user_data.clear()
        return await update.message.reply_text("📥 تم إرسال الطلب")

    # الطلبات
    if t=="📥 الطلبات":
        reqs = cur.execute("SELECT rowid,* FROM requests").fetchall()

        for r in reqs:
            kb=[[InlineKeyboardButton("✅",callback_data=f"ok_{r[0]}"),
                 InlineKeyboardButton("❌",callback_data=f"no_{r[0]}")]]

            await update.message.reply_text(f"{r[1]} | {r[5]}", reply_markup=InlineKeyboardMarkup(kb))

    # البحث
    if t=="🔍 بحث لاعب":
        context.user_data["s"]="search"
        return await update.message.reply_text("اكتب اسم او فيس")

    if s=="search":
        res = cur.execute("SELECT * FROM players WHERE name LIKE ? OR fb LIKE ?",(f"%{t}%",f"%{t}%")).fetchall()

        for p in res:
            await update.message.reply_text(f"""
👤 {p[0]}
🔗 {p[1]}
🎮 {p[3]}
🏟️ {p[4]}
""")
        context.user_data.clear()

# ================= BUTTONS =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    if data.startswith("players_"):
        club = data.split("_")[1]
        players = cur.execute("SELECT * FROM players WHERE club=?",(club,)).fetchall()

        for p in players:
            await q.message.reply_text(f"""
👤 {p[0]}
🔗 {p[1]}
🎮 {p[3]}
🔢 {p[2]}
""")

    if data.startswith("ok_"):
        rid = data.split("_")[1]
        r = cur.execute("SELECT * FROM requests WHERE rowid=?",(rid,)).fetchone()

        cur.execute("INSERT INTO players VALUES (?,?,?,?,?)",r)
        cur.execute("DELETE FROM requests WHERE rowid=?",(rid,))
        conn.commit()

        await q.message.reply_text("✅ تم القبول")

    if data.startswith("no_"):
        rid = data.split("_")[1]
        cur.execute("DELETE FROM requests WHERE rowid=?",(rid,))
        conn.commit()

        await q.message.reply_text("❌ تم الرفض")

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
