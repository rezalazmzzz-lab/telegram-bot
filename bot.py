import os, sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

# ===== DATABASE =====
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders(id INTEGER UNIQUE)")
cur.execute("CREATE TABLE IF NOT EXISTS clubs(name TEXT, president INTEGER, pres_name TEXT, fb TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS players(name TEXT, fb TEXT, screen TEXT, club TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, data TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT, val TEXT)")
db.commit()

# ===== HELPERS =====
def is_leader(uid):
    if uid == OWNER_ID:
        return True
    return cur.execute("SELECT 1 FROM leaders WHERE id=?", (uid,)).fetchone()

def transfer_open():
    r = cur.execute("SELECT val FROM settings WHERE key='t'").fetchone()
    return r and r[0] == "1"

def set_transfer(v):
    cur.execute("DELETE FROM settings WHERE key='t'")
    cur.execute("INSERT INTO settings VALUES('t',?)",(v,))
    db.commit()

def menu(uid):
    m = [["🔍 بحث لاعب"]]

    if uid == OWNER_ID:
        m += [["👑 إدارة القادة"],["📥 الطلبات"],["⚙️ الانتقالات"]]

    elif is_leader(uid):
        m += [["🏟 إدارة الأندية"],["📥 الطلبات"]]

    else:
        m += [["📋 عرض الأندية"]]

    return ReplyKeyboardMarkup(m, resize_keyboard=True)

async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def valid_fb(link):
    return link.startswith("https://www.facebook.com/")

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    db.commit()
    await update.message.reply_text("🔥 البوت شغال", reply_markup=menu(uid))

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    t = update.message.text
    s = context.user_data.get("s")

    # رجوع
    if t == "🔙 رجوع":
        context.user_data.clear()
        return await update.message.reply_text("رجعنا", reply_markup=menu(uid))

    # ===== إدارة القادة (فقط المالك) =====
    if t == "👑 إدارة القادة" and uid == OWNER_ID:
        kb = [["➕ إضافة قائد","➖ حذف قائد"],["🔙 رجوع"]]
        return await update.message.reply_text("👑 القادة", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    if t == "➕ إضافة قائد":
        context.user_data["s"] = "addL"
        return await update.message.reply_text("ارسل ID:")

    if s == "addL":
        if not t.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        uid2 = int(t)

        # تحقق: لازم مسوي start
        if not cur.execute("SELECT 1 FROM users WHERE id=?", (uid2,)).fetchone():
            return await update.message.reply_text("❌ خليه يدخل البوت ويكتب /start")

        # تحقق: ID حقيقي
        if not await valid_user(context.application, uid2):
            return await update.message.reply_text("❌ ID غير حقيقي")

        cur.execute("INSERT OR IGNORE INTO leaders VALUES(?)",(uid2,))
        db.commit()
        context.user_data.clear()

        return await update.message.reply_text("✅ تم إضافة قائد")

    # ===== إدارة الأندية =====
    if t == "🏟 إدارة الأندية" and is_leader(uid):
        kb = [["➕ إضافة نادي","📋 عرض الأندية"],["🔙 رجوع"]]
        return await update.message.reply_text("🏟 الأندية", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    if t == "➕ إضافة نادي":
        context.user_data["s"] = "pres_name"
        return await update.message.reply_text("اسم رئيس النادي:")

    if s == "pres_name":
        context.user_data["pn"] = t
        context.user_data["s"] = "pres_fb"
        return await update.message.reply_text("رابط الفيس:")

    if s == "pres_fb":
        if not valid_fb(t):
            return await update.message.reply_text("❌ رابط فيس غير صحيح")

        context.user_data["pf"] = t
        context.user_data["s"] = "pres_id"
        return await update.message.reply_text("ID التلكرام:")

    if s == "pres_id":
        if not t.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        uid2 = int(t)

        if not cur.execute("SELECT 1 FROM users WHERE id=?", (uid2,)).fetchone():
            return await update.message.reply_text("❌ لازم يسوي /start")

        if not await valid_user(context.application, uid2):
            return await update.message.reply_text("❌ ID غير حقيقي")

        context.user_data["pid"] = uid2
        context.user_data["s"] = "club_name"
        return await update.message.reply_text("اسم النادي:")

    if s == "club_name":
        cur.execute("INSERT INTO clubs VALUES(?,?,?,?)",
                    (t, context.user_data["pid"], context.user_data["pn"], context.user_data["pf"]))

        # إعطاء صلاحية للرئيس
        cur.execute("INSERT OR IGNORE INTO leaders VALUES(?)",(context.user_data["pid"],))

        db.commit()
        context.user_data.clear()

        return await update.message.reply_text("✅ تم إنشاء النادي")

    # ===== عرض الأندية =====
    if t == "📋 عرض الأندية":
        clubs = cur.execute("SELECT * FROM clubs").fetchall()

        if not clubs:
            return await update.message.reply_text("❌ ماكو أندية")

        for c in clubs:
            kb = [[f"👥 {c[0]}"],["🚫 اعتراض"],["🔙 رجوع"]]
            await update.message.reply_text(
                f"🏟 {c[0]}\n👤 {c[2]}",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
            )
        return

    # عرض لاعبين
    if t.startswith("👥"):
        club = t.replace("👥 ","")
        ps = cur.execute("SELECT * FROM players WHERE club=?", (club,)).fetchall()

        if not ps:
            return await update.message.reply_text("❌ ماكو لاعبين")

        msg = ""
        for p in ps:
            msg += f"👤 {p[0]}\n🔗 {p[1]}\n📸 {p[2]}\n\n"

        return await update.message.reply_text(msg)

    # ===== اعتراض =====
    if t == "🚫 اعتراض":
        context.user_data["s"] = "comp"
        return await update.message.reply_text("اكتب الاعتراض:")

    if s == "comp":
        cur.execute("INSERT INTO requests(type,data) VALUES('complaint',?)",(t,))
        db.commit()
        context.user_data.clear()
        return await update.message.reply_text("📥 تم إرسال الاعتراض")

    # ===== الطلبات =====
    if t == "📥 الطلبات" and is_leader(uid):
        rs = cur.execute("SELECT * FROM requests").fetchall()

        if not rs:
            return await update.message.reply_text("❌ ماكو طلبات")

        msg = ""
        for r in rs:
            msg += f"{r[0]} - {r[2]}\n"

        context.user_data["s"] = "approve"
        return await update.message.reply_text(msg + "\nارسل رقم الطلب")

    if s == "approve":
        context.user_data["rid"] = int(t)
        context.user_data["s"] = "dec"
        return await update.message.reply_text("✅ موافقة او ❌ رفض")

    if s == "dec":
        cur.execute("DELETE FROM requests WHERE id=?", (context.user_data["rid"],))
        db.commit()
        context.user_data.clear()
        return await update.message.reply_text("✅ تم")

    # ===== الانتقالات =====
    if t == "⚙️ الانتقالات" and uid == OWNER_ID:
        kb = [["🟢 فتح","🔴 غلق"]]
        return await update.message.reply_text("⚙️ التحكم", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    if t == "🟢 فتح":
        set_transfer("1")
        return await update.message.reply_text("🟢 تم الفتح")

    if t == "🔴 غلق":
        set_transfer("0")
        return await update.message.reply_text("🔴 تم الغلق")

# ===== RUN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
