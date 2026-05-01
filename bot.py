import os, sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

# ===== TABLES =====
cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders(id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS clubs(name TEXT, president INTEGER, pres_name TEXT, fb TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS players(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, fb TEXT, club TEXT, photo TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, data TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT, val TEXT)")
db.commit()

# ===== HELPERS =====
def is_leader(uid):
    if uid == OWNER_ID: return True
    return cur.execute("SELECT 1 FROM leaders WHERE id=?", (uid,)).fetchone()

def transfer_open():
    r = cur.execute("SELECT val FROM settings WHERE key='t'").fetchone()
    return r and r[0] == "1"

def set_transfer(v):
    cur.execute("DELETE FROM settings WHERE key='t'")
    cur.execute("INSERT INTO settings VALUES('t',?)",(v,))
    db.commit()

async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def menu(uid):
    m=[["🔍 بحث لاعب"]]

    if uid == OWNER_ID:
        m += [["👑 القادة"],["📥 الطلبات"],["⚙️ الانتقالات"]]

    elif is_leader(uid):
        m += [["🏟 الأندية"],["📥 الطلبات"]]

    else:
        m += [["📋 عرض الأندية"]]

    return ReplyKeyboardMarkup(m, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    db.commit()
    await update.message.reply_text("🔥 البوت جاهز", reply_markup=menu(uid))

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    t = update.message.text
    s = context.user_data.get("s")

    # رجوع
    if t=="🔙":
        context.user_data.clear()
        return await update.message.reply_text("رجوع", reply_markup=menu(uid))

    # ===== إضافة قائد =====
    if t=="➕ قائد":
        context.user_data["s"]="addL"
        return await update.message.reply_text("ID")

    if s=="addL":
        if not t.isdigit(): return await update.message.reply_text("❌")
        if not await valid_user(context.application,int(t)):
            return await update.message.reply_text("❌ لازم start")

        cur.execute("INSERT INTO leaders VALUES(?)",(int(t),))
        db.commit(); context.user_data.clear()
        return await update.message.reply_text("✅ تم")

    # ===== إضافة نادي =====
    if t=="➕ نادي":
        context.user_data["s"]="pn"
        return await update.message.reply_text("اسم الرئيس")

    if s=="pn":
        context.user_data["pn"]=t; context.user_data["s"]="pid"
        return await update.message.reply_text("ID")

    if s=="pid":
        if not t.isdigit(): return await update.message.reply_text("❌")
        if not await valid_user(context.application,int(t)):
            return await update.message.reply_text("❌ لازم start")

        context.user_data["pid"]=int(t); context.user_data["s"]="cn"
        return await update.message.reply_text("اسم النادي")

    if s=="cn":
        cur.execute("INSERT INTO clubs VALUES(?,?,?,?)",
                    (t,context.user_data["pid"],context.user_data["pn"],"fb"))
        cur.execute("INSERT INTO leaders VALUES(?)",(context.user_data["pid"],))
        db.commit(); context.user_data.clear()
        return await update.message.reply_text("✅ تم")

    # ===== عرض الأندية =====
    if t=="📋 عرض الأندية":
        clubs=cur.execute("SELECT * FROM clubs").fetchall()
        if not clubs: return await update.message.reply_text("❌")

        for c in clubs:
            count = cur.execute("SELECT COUNT(*) FROM players WHERE club=?",(c[0],)).fetchone()[0]
            await update.message.reply_text(f"{c[0]}\n👤 {c[2]}\n👥 {count} لاعب")

    # ===== إضافة لاعب (صورة حقيقية) =====
    if t=="➕ لاعب":
        if not transfer_open():
            return await update.message.reply_text("❌ الانتقالات مغلقة")

        context.user_data["s"]="pname"
        return await update.message.reply_text("اسم اللاعب")

    if s=="pname":
        context.user_data["name"]=t
        context.user_data["s"]="pfb"
        return await update.message.reply_text("رابط الفيس")

    if s=="pfb":
        context.user_data["fb"]=t
        context.user_data["s"]="photo"
        return await update.message.reply_text("ارسل صورة اللاعب")

    if s=="photo" and update.message.photo:
        file = update.message.photo[-1].file_id

        club = cur.execute("SELECT name FROM clubs WHERE president=?",(uid,)).fetchone()
        if not club:
            return await update.message.reply_text("❌ مو رئيس نادي")

        cur.execute("INSERT INTO players(name,fb,club,photo) VALUES(?,?,?,?)",
                    (context.user_data["name"],context.user_data["fb"],club[0],file))
        db.commit()

        # 🔔 إشعار
        await context.bot.send_message(OWNER_ID, f"تم إضافة لاعب {context.user_data['name']}")

        context.user_data.clear()
        return await update.message.reply_text("✅ تم إضافة اللاعب")

    # ===== حذف لاعب =====
    if t=="❌ حذف لاعب":
        context.user_data["s"]="del"
        return await update.message.reply_text("اسم اللاعب")

    if s=="del":
        cur.execute("DELETE FROM players WHERE name=?",(t,))
        db.commit()
        context.user_data.clear()
        return await update.message.reply_text("✅ تم الحذف")

    # ===== تعديل لاعب =====
    if t=="✏️ تعديل لاعب":
        context.user_data["s"]="edit"
        return await update.message.reply_text("اسم اللاعب")

    if s=="edit":
        context.user_data["old"]=t
        context.user_data["s"]="new"
        return await update.message.reply_text("الاسم الجديد")

    if s=="new":
        cur.execute("UPDATE players SET name=? WHERE name=?",(t,context.user_data["old"]))
        db.commit()
        context.user_data.clear()
        return await update.message.reply_text("✅ تم التعديل")

    # ===== البحث =====
    if t=="🔍 بحث لاعب":
        context.user_data["s"]="search"
        return await update.message.reply_text("اكتب الاسم")

    if s=="search":
        p=cur.execute("SELECT * FROM players WHERE name LIKE ?",('%'+t+'%',)).fetchone()
        if not p: return await update.message.reply_text("❌")

        await update.message.reply_photo(p[4],caption=f"{p[1]}\n{p[2]}\n{p[3]}")
        context.user_data.clear()

    # ===== الانتقالات =====
    if t=="⚙️ الانتقالات":
        kb=[["🟢 فتح","🔴 غلق"]]
        return await update.message.reply_text("⚙️",reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))

    if t=="🟢 فتح":
        set_transfer("1")
        return await update.message.reply_text("🟢 مفتوحة")

    if t=="🔴 غلق":
        set_transfer("0")
        return await update.message.reply_text("🔴 مغلقة")

# ===== RUN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle))
    app.run_polling()

if __name__=="__main__":
    main()
