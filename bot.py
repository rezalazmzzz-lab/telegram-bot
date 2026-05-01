import sqlite3
import os
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 653170487  # غيره الى ايديك

# ================= DB =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS clubs (name TEXT, owner_id INTEGER, owner_name TEXT, fb TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS players (name TEXT, fb TEXT, serial TEXT UNIQUE, device TEXT, club TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, fb TEXT, serial TEXT, device TEXT, club TEXT)")
conn.commit()

cur.execute("INSERT OR IGNORE INTO admins VALUES (?)", (ADMIN_ID,))
conn.commit()

# ================= FUNCTIONS =================
def is_admin(i): return cur.execute("SELECT 1 FROM admins WHERE id=?", (i,)).fetchone()
def is_leader(i): return cur.execute("SELECT 1 FROM leaders WHERE id=?", (i,)).fetchone()
def is_owner(i): return cur.execute("SELECT 1 FROM clubs WHERE owner_id=?", (i,)).fetchone()

def valid_fb(link):
    return re.match(r"(https?://)?(www\.)?facebook\.com/.+", link)

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
    context.user_data.clear()
    uid = update.effective_user.id
    await update.message.reply_text("🎮 بوت اتحاد PES", reply_markup=ReplyKeyboardMarkup(menu(uid), resize_keyboard=True))

# ================= HANDLE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    uid = update.effective_user.id
    s = context.user_data.get("s")

    # 🔙 رجوع
    if t == "رجوع ⬅️":
        context.user_data.clear()
        return await update.message.reply_text("رجعنا 🔙", reply_markup=ReplyKeyboardMarkup(menu(uid), resize_keyboard=True))

    # ================= ADMIN =================
    if t == "➕ قائد" and is_admin(uid):
        context.user_data["s"] = "add_leader"
        return await update.message.reply_text("ارسل ID القائد")

    if s == "add_leader":
        try:
            cur.execute("INSERT INTO leaders VALUES (?)", (int(t),))
            conn.commit()
            context.user_data.clear()
            return await update.message.reply_text("تم إضافة قائد ✅")
        except:
            return await update.message.reply_text("❌ ايدي غلط")

    if t == "➕ نادي" and is_admin(uid):
        context.user_data["s"] = "club_owner"
        return await update.message.reply_text("ارسل ID رئيس النادي")

    if s == "club_owner":
        context.user_data["owner_id"] = int(t)
        context.user_data["s"] = "club_name"
        return await update.message.reply_text("اسم النادي")

    if s == "club_name":
        context.user_data["club_name"] = t
        context.user_data["s"] = "club_fb"
        return await update.message.reply_text("رابط فيسبوك الرئيس")

    if s == "club_fb":
        if not valid_fb(t):
            return await update.message.reply_text("❌ رابط فيسبوك غير صحيح")
        cur.execute("INSERT INTO clubs VALUES (?,?,?,?)",
                    (context.user_data["club_name"], context.user_data["owner_id"], "رئيس", t))
        conn.commit()
        context.user_data.clear()
        return await update.message.reply_text("تم إنشاء النادي ✅")

    # ================= عرض الأندية =================
    if t == "🏟️ عرض الأندية":
        clubs = cur.execute("SELECT name FROM clubs").fetchall()
        if not clubs:
            return await update.message.reply_text("ماكو أندية")
        for c in clubs:
            kb = [[InlineKeyboardButton("👥 عرض اللاعبين", callback_data=f"club_{c[0]}")]]
            await update.message.reply_text(f"🏟️ {c[0]}", reply_markup=InlineKeyboardMarkup(kb))

    # ================= عرض لاعبين =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("club_"):
        club = data.split("_")[1]
        players = cur.execute("SELECT * FROM players WHERE club=?", (club,)).fetchall()
        if not players:
            return await query.message.reply_text("❌ ماكو لاعبين")
        msg = f"🏟️ {club}\n"
        for p in players:
            msg += f"\n👤 {p[0]}\n🔗 {p[1]}\n📱 {p[3]}\n"
        await query.message.reply_text(msg)

# ================= إضافة لاعب =================
async def handle_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    uid = update.effective_user.id
    s = context.user_data.get("s")

    if t == "➕ لاعب" and is_owner(uid):
        context.user_data["s"] = "p_name"
        return await update.message.reply_text("اسم اللاعب")

    if s == "p_name":
        context.user_data["name"] = t
        context.user_data["s"] = "p_fb"
        return await update.message.reply_text("رابط الفيس")

    if s == "p_fb":
        if not valid_fb(t):
            return await update.message.reply_text("❌ رابط غير صحيح")
        context.user_data["fb"] = t
        context.user_data["s"] = "p_serial"
        return await update.message.reply_text("الرقم التسلسلي")

    if s == "p_serial":
        context.user_data["serial"] = t
        context.user_data["s"] = "p_device"
        return await update.message.reply_text("نوع الجهاز")

    if s == "p_device":
        club = cur.execute("SELECT name FROM clubs WHERE owner_id=?", (uid,)).fetchone()[0]
        cur.execute("INSERT INTO requests (name,fb,serial,device,club) VALUES (?,?,?,?,?)",
                    (context.user_data["name"], context.user_data["fb"], context.user_data["serial"], t, club))
        conn.commit()
        context.user_data.clear()
        return await update.message.reply_text("تم إرسال الطلب ⏳")

# ================= الطلبات =================
async def requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (is_admin(update.effective_user.id) or is_leader(update.effective_user.id)):
        return
    rows = cur.execute("SELECT * FROM requests").fetchall()
    for r in rows:
        kb = [
            [InlineKeyboardButton("✅ قبول", callback_data=f"ok_{r[0]}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"no_{r[0]}")]
        ]
        await update.message.reply_text(f"{r[1]} | {r[5]}", reply_markup=InlineKeyboardMarkup(kb))

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("ok_"):
        rid = data.split("_")[1]
        r = cur.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
        try:
            cur.execute("INSERT INTO players VALUES (?,?,?,?,?)", (r[1], r[2], r[3], r[4], r[5]))
            cur.execute("DELETE FROM requests WHERE id=?", (rid,))
            conn.commit()
            await q.message.reply_text("تم القبول ✅")
        except:
            await q.message.reply_text("❌ مكرر")

    if data.startswith("no_"):
        rid = data.split("_")[1]
        cur.execute("DELETE FROM requests WHERE id=?", (rid,))
        conn.commit()
        await q.message.reply_text("تم الرفض ❌")

# ================= بحث =================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["s"] = "search"
    await update.message.reply_text("اكتب اسم او فيسبوك اللاعب")

async def do_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("s") != "search":
        return
    t = update.message.text
    rows = cur.execute("SELECT * FROM players WHERE name LIKE ? OR fb LIKE ?", (f"%{t}%", f"%{t}%")).fetchall()
    if not rows:
        return await update.message.reply_text("❌ ماكو لاعب")
    for r in rows:
        await update.message.reply_text(f"👤 {r[0]}\n🔗 {r[1]}\n🏟️ {r[4]}")

# ================= RUN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))
app.add_handler(MessageHandler(filters.TEXT, handle_owner))
app.add_handler(MessageHandler(filters.Regex("📥 الطلبات"), requests))
app.add_handler(MessageHandler(filters.Regex("🔍 بحث لاعب"), search))
app.add_handler(MessageHandler(filters.TEXT, do_search))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(CallbackQueryHandler(approve))

app.run_polling()
