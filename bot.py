import os, sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

# ===== DATABASE =====
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders(id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS clubs(name TEXT, president INTEGER, pres_name TEXT, fb TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS players(name TEXT, fb TEXT, screen TEXT, club TEXT)")
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

def menu(uid):
    m=[["🔍 بحث لاعب"]]

    if uid == OWNER_ID:
        m += [["👑 القادة"],["📥 الطلبات"],["⚙️ الانتقالات"]]

    elif is_leader(uid):
        m += [["🏟 الأندية"],["📥 الطلبات"]]

    else:
        m += [["📋 عرض الأندية"]]

    return ReplyKeyboardMarkup(m, resize_keyboard=True)

async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def valid_fb(x):
    return x.startswith("https://www.facebook.com/")

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

    # ===== القادة =====
    if t=="👑 القادة" and uid==OWNER_ID:
        kb=[["➕ قائد","➖ قائد"],["🔙"]]
        return await update.message.reply_text("👑", reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))

    if t=="➕ قائد":
        context.user_data["s"]="addL"
        return await update.message.reply_text("ID:")

    if s=="addL":
        if not t.isdigit(): return await update.message.reply_text("❌")
        if not await valid_user(context.application,int(t)):
            return await update.message.reply_text("❌ خليه يسوي start")

        cur.execute("INSERT INTO leaders VALUES(?)",(int(t),))
        db.commit(); context.user_data.clear()
        return await update.message.reply_text("✅")

    # ===== الأندية =====
    if t=="🏟 الأندية" and is_leader(uid):
        kb=[["➕ نادي","📋 عرض"],["🔙"]]
        return await update.message.reply_text("🏟",reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))

    if t=="➕ نادي":
        context.user_data["s"]="pn"
        return await update.message.reply_text("اسم الرئيس")

    if s=="pn":
        context.user_data["pn"]=t; context.user_data["s"]="pf"
        return await update.message.reply_text("فيس")

    if s=="pf":
        if not valid_fb(t): return await update.message.reply_text("❌")
        context.user_data["pf"]=t; context.user_data["s"]="pid"
        return await update.message.reply_text("ID")

    if s=="pid":
        if not t.isdigit(): return await update.message.reply_text("❌")
        if not await valid_user(context.application,int(t)):
            return await update.message.reply_text("❌ لازم start")

        context.user_data["pid"]=int(t); context.user_data["s"]="cn"
        return await update.message.reply_text("اسم النادي")

    if s=="cn":
        cur.execute("INSERT INTO clubs VALUES(?,?,?,?)",
                    (t,context.user_data["pid"],context.user_data["pn"],context.user_data["pf"]))
        cur.execute("INSERT INTO leaders VALUES(?)",(context.user_data["pid"],))
        db.commit(); context.user_data.clear()
        return await update.message.reply_text("✅ تم")

    # ===== عرض الأندية =====
    if t=="📋 عرض الأندية" or t=="📋 عرض":
        clubs=cur.execute("SELECT * FROM clubs").fetchall()
        if not clubs: return await update.message.reply_text("❌")

        for c in clubs:
            kb=[[f"👥 {c[0]}"],["🚫 اعتراض"],["🔙"]]
            await update.message.reply_text(f"{c[0]}\n{c[2]}",reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))
        return

    if t.startswith("👥"):
        c=t.replace("👥 ","")
        ps=cur.execute("SELECT * FROM players WHERE club=?",(c,)).fetchall()
        if not ps: return await update.message.reply_text("❌")

        msg=""
        for p in ps:
            msg+=f"{p[0]}\n{p[1]}\n{p[2]}\n\n"
        return await update.message.reply_text(msg)

    # ===== اعتراض =====
    if t=="🚫 اعتراض":
        context.user_data["s"]="comp"
        return await update.message.reply_text("اكتب الاعتراض")

    if s=="comp":
        cur.execute("INSERT INTO requests(type,data) VALUES('comp',?)",(t,))
        db.commit(); context.user_data.clear()
        return await update.message.reply_text("📥 تم")

    # ===== الطلبات =====
    if t=="📥 الطلبات" and is_leader(uid):
        rs=cur.execute("SELECT * FROM requests").fetchall()
        if not rs: return await update.message.reply_text("❌")

        msg=""
        for r in rs:
            msg+=f"{r[0]} - {r[1]} - {r[2]}\n"
        context.user_data["s"]="app"
        return await update.message.reply_text(msg+"اختر رقم")

    if s=="app":
        context.user_data["rid"]=int(t)
        context.user_data["s"]="dec"
        return await update.message.reply_text("✅ او ❌")

    if s=="dec":
        cur.execute("DELETE FROM requests WHERE id=?",(context.user_data["rid"],))
        db.commit(); context.user_data.clear()
        return await update.message.reply_text("تم")

    # ===== الانتقالات =====
    if t=="⚙️ الانتقالات" and uid==OWNER_ID:
        kb=[["🟢 فتح","🔴 غلق"]]
        return await update.message.reply_text("⚙️",reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))

    if t=="🟢 فتح": set_transfer("1"); return await update.message.reply_text("🟢")
    if t=="🔴 غلق": set_transfer("0"); return await update.message.reply_text("🔴")

# ===== RUN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__=="__main__":
    main()
