import sqlite3
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 653170487

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

# ================= DATABASE =================
cur.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS club_requests (id INTEGER, fb TEXT, club TEXT)")
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

def valid_fb(link):
    return "facebook.com" in link.lower()

def menu(uid):
    if is_admin(uid):
        return [["➕ قائد","➖ قائد"],["➕ نادي"],["🏟️ عرض الأندية"],["📥 الطلبات"],["🔍 بحث لاعب"]]
    if is_leader(uid):
        return [["📥 الطلبات"],["🏟️ عرض الأندية"],["🔍 بحث لاعب"]]
    if is_owner(uid):
        return [["➕ لاعب"],["📋 لاعبين النادي"],["🔍 بحث لاعب"]]
    return [["🔍 بحث لاعب"]]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("🎮 بوت اتحاد PES", reply_markup=ReplyKeyboardMarkup(menu(uid), resize_keyboard=True))

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    uid = update.effective_user.id
    s = context.user_data.get("s")

    # ===== إضافة قائد =====
    if t=="➕ قائد" and is_admin(uid):
        context.user_data["s"]="add_leader"
        return await update.message.reply_text("ارسل ID القائد")

    if s=="add_leader":
        try:
            cur.execute("INSERT INTO leaders VALUES (?)",(int(t),))
            conn.commit()
            context.user_data.clear()
            return await update.message.reply_text("✅ تم إضافة قائد")
        except:
            return await update.message.reply_text("❌ ايدي غير صحيح")

    # ===== إضافة نادي =====
    if t=="➕ نادي" and is_admin(uid):
        context.user_data["s"]="club_owner"
        return await update.message.reply_text("ID رئيس النادي")

    if s=="club_owner":
        context.user_data["owner"]=int(t)
        context.user_data["s"]="club_name"
        return await update.message.reply_text("اسم النادي")

    if s=="club_name":
        cur.execute("INSERT INTO clubs VALUES (?,?)",(t,context.user_data["owner"]))
        conn.commit()
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إنشاء النادي")

    # ===== إضافة لاعب =====
    if t=="➕ لاعب" and is_owner(uid):
        context.user_data["s"]="p_name"
        return await update.message.reply_text("اسم اللاعب")

    if s=="p_name":
        context.user_data["name"]=t
        context.user_data["s"]="p_fb"
        return await update.message.reply_text("رابط الفيس")

    if s=="p_fb":
        if not valid_fb(t):
            return await update.message.reply_text("❌ لازم رابط فيسبوك صحيح")
        context.user_data["fb"]=t
        context.user_data["s"]="p_serial"
        return await update.message.reply_text("الرقم التسلسلي")

    if s=="p_serial":
        if cur.execute("SELECT * FROM players WHERE serial=?",(t,)).fetchone():
            return await update.message.reply_text("❌ هذا اللاعب مسجل مسبقاً")
        context.user_data["serial"]=t
        context.user_data["s"]="p_device"
        return await update.message.reply_text("نوع الجهاز")

    if s=="p_device":
        club = cur.execute("SELECT name FROM clubs WHERE owner_id=?",(uid,)).fetchone()[0]

        cur.execute("INSERT INTO requests VALUES (?,?,?,?,?)",
                    (context.user_data["name"],context.user_data["fb"],context.user_data["serial"],t,club))
        conn.commit()
        context.user_data.clear()

        return await update.message.reply_text("📥 تم إرسال الطلب للموافقة")

    # ===== عرض الأندية =====
    if t=="🏟️ عرض الأندية":
        clubs = cur.execute("SELECT name FROM clubs").fetchall()
        if not clubs:
            return await update.message.reply_text("❌ ماكو أندية")

        for c in clubs:
            kb = [[InlineKeyboardButton("👥 عرض اللاعبين", callback_data=f"players_{c[0]}")]]
            await update.message.reply_text(f"🏟️ {c[0]}", reply_markup=InlineKeyboardMarkup(kb))

    # ===== بحث لاعب =====
    if t=="🔍 بحث لاعب":
        context.user_data["s"]="search"
        return await update.message.reply_text("اكتب اسم اللاعب او رابط الفيس")

    if s=="search":
        res = cur.execute("SELECT * FROM players WHERE name LIKE ? OR fb LIKE ?",(f"%{t}%",f"%{t}%")).fetchall()
        if not res:
            return await update.message.reply_text("❌ ماكو لاعب")

        for p in res:
            await update.message.reply_text(f"""
👤 {p[0]}
🔗 {p[1]}
🎮 {p[3]}
🏟️ {p[4]}
""")
        context.user_data.clear()

    # ===== الطلبات =====
    if t=="📥 الطلبات" and (is_admin(uid) or is_leader(uid)):
        reqs = cur.execute("SELECT rowid,* FROM requests").fetchall()
        if not reqs:
            return await update.message.reply_text("❌ ماكو طلبات")

        for r in reqs:
            kb = [
                [InlineKeyboardButton("✅ موافقة", callback_data=f"ok_{r[0]}"),
                 InlineKeyboardButton("❌ رفض", callback_data=f"no_{r[0]}")]
            ]
            await update.message.reply_text(f"{r[1]} | {r[5]}", reply_markup=InlineKeyboardMarkup(kb))

# ================= CALLBACK =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data

    # عرض لاعبين نادي
    if data.startswith("players_"):
        club = data.split("_")[1]
        players = cur.execute("SELECT * FROM players WHERE club=?",(club,)).fetchall()

        if not players:
            return await q.message.reply_text("❌ ماكو لاعبين")

        for p in players:
            await q.message.reply_text(f"""
👤 {p[0]}
🔗 {p[1]}
🎮 {p[3]}
🔢 {p[2]}
""")

    # موافقة
    if data.startswith("ok_"):
        rid = data.split("_")[1]
        r = cur.execute("SELECT * FROM requests WHERE rowid=?",(rid,)).fetchone()

        cur.execute("INSERT INTO players VALUES (?,?,?,?,?)",r)
        cur.execute("DELETE FROM requests WHERE rowid=?",(rid,))
        conn.commit()

        await q.message.reply_text("✅ تم قبول اللاعب")

    # رفض
    if data.startswith("no_"):
        rid = data.split("_")[1]
        cur.execute("DELETE FROM requests WHERE rowid=?",(rid,))
        conn.commit()

        await q.message.reply_text("❌ تم رفض الطلب")

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
