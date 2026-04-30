import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ TOKEN مو موجود! ضيفه بالريلواي")

ADMIN_IDS = [653170487]

# ================= DB =================
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, role TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS clubs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, president_id INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, fb TEXT, serial TEXT UNIQUE, device TEXT, club_id INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, fb TEXT, serial TEXT, device TEXT, club_id INTEGER, president_id INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
conn.commit()

c.execute("INSERT OR IGNORE INTO settings VALUES ('transfer','open')")
conn.commit()

# ================= HELPERS =================

def get_role(user_id):
    if user_id in ADMIN_IDS:
        return "admin"
    r = c.execute("SELECT role FROM users WHERE user_id=?", (user_id,)).fetchone()
    return r[0] if r else None

def transfer_open():
    return c.execute("SELECT value FROM settings WHERE key='transfer'").fetchone()[0] == "open"

def menu(role):
    if role == "admin":
        return [["اضافة قائد","حذف قائد"],["اضافة نادي","عرض الاندية"],["فتح الانتقالات","غلق الانتقالات"]]
    if role == "leader":
        return [["الطلبات","عرض الاندية"],["فتح الانتقالات","غلق الانتقالات"]]
    if role == "president":
        return [["اضافة لاعب","لاعبيني"],["عرض الاندية","بحث لاعب"]]
    return [["/start"]]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = get_role(update.effective_user.id)
    if not role:
        await update.message.reply_text("❌ انت غير مسجل")
        return
    await update.message.reply_text("اهلا بيك", reply_markup=ReplyKeyboardMarkup(menu(role), resize_keyboard=True))

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user.id
    role = get_role(user)
    state = context.user_data.get("state")

    # ===== ADD LEADER =====
    if text == "اضافة قائد" and role == "admin":
        context.user_data["state"] = "add_leader"
        return await update.message.reply_text("ارسل ايدي")

    if state == "add_leader":
        try:
            c.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (int(text), "leader"))
            conn.commit()
            await update.message.reply_text("✅ تم اضافة قائد")
        except:
            await update.message.reply_text("❌ ايدي غير صحيح")
        context.user_data.clear()
        return

    # ===== ADD CLUB =====
    if text == "اضافة نادي" and role == "admin":
        context.user_data["state"] = "club_name"
        return await update.message.reply_text("اسم النادي")

    if state == "club_name":
        context.user_data["club_name"] = text
        context.user_data["state"] = "club_pres"
        return await update.message.reply_text("ايدي الرئيس")

    if state == "club_pres":
        try:
            c.execute("INSERT INTO clubs (name,president_id) VALUES (?,?)", (context.user_data["club_name"], int(text)))
            c.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (int(text), "president"))
            conn.commit()
            await update.message.reply_text("✅ تم اضافة نادي")
        except:
            await update.message.reply_text("❌ خطأ بالايدي")
        context.user_data.clear()
        return

    # ===== ADD PLAYER =====
    if text == "اضافة لاعب" and role == "president":
        if not transfer_open():
            return await update.message.reply_text("❌ الانتقالات مغلقة")
        context.user_data["state"] = "p_name"
        return await update.message.reply_text("اسم اللاعب")

    if state == "p_name":
        context.user_data["name"] = text
        context.user_data["state"] = "p_fb"
        return await update.message.reply_text("رابط الفيس")

    if state == "p_fb":
        context.user_data["fb"] = text
        context.user_data["state"] = "p_serial"
        return await update.message.reply_text("الرقم التسلسلي")

    if state == "p_serial":
        if c.execute("SELECT * FROM players WHERE serial=?", (text,)).fetchone():
            return await update.message.reply_text("❌ لاعب مكرر")
        context.user_data["serial"] = text
        context.user_data["state"] = "p_device"
        return await update.message.reply_text("اسم الجهاز")

    if state == "p_device":
        club = c.execute("SELECT id FROM clubs WHERE president_id=?", (user,)).fetchone()
        if not club:
            return await update.message.reply_text("❌ ما عندك نادي")

        d = context.user_data
        c.execute("INSERT INTO requests (name,fb,serial,device,club_id,president_id) VALUES (?,?,?,?,?,?)",
                  (d["name"], d["fb"], d["serial"], text, club[0], user))
        conn.commit()
        context.user_data.clear()
        return await update.message.reply_text("📨 تم ارسال الطلب للقادة")

    # ===== REQUESTS =====
    if text == "الطلبات" and role == "leader":
        reqs = c.execute("SELECT * FROM requests").fetchall()
        if not reqs:
            return await update.message.reply_text("ماكو طلبات")

        msg = ""
        for r in reqs:
            msg += f"\nID:{r[0]} | {r[1]}"
        msg += "\n\nاكتب: قبول ID او رفض ID"
        return await update.message.reply_text(msg)

    if text.startswith("قبول") and role == "leader":
        rid = int(text.split()[1])
        r = c.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()
        if r:
            c.execute("INSERT INTO players (name,fb,serial,device,club_id) VALUES (?,?,?,?,?)",
                      (r[1], r[2], r[3], r[4], r[5]))
            c.execute("DELETE FROM requests WHERE id=?", (rid,))
            conn.commit()
            return await update.message.reply_text("✅ تمت الموافقة")

    if text.startswith("رفض") and role == "leader":
        rid = int(text.split()[1])
        c.execute("DELETE FROM requests WHERE id=?", (rid,))
        conn.commit()
        return await update.message.reply_text("❌ تم الرفض")

    # ===== VIEW CLUBS =====
    if text == "عرض الاندية":
        clubs = c.execute("SELECT * FROM clubs").fetchall()
        msg = ""
        for club in clubs:
            msg += f"\n🏟 {club[1]}\n"
            players = c.execute("SELECT name FROM players WHERE club_id=?", (club[0],))
            for p in players:
                msg += f"- {p[0]}\n"
        return await update.message.reply_text(msg or "ماكو اندية")

    # ===== SEARCH =====
    if text == "بحث لاعب":
        context.user_data["state"] = "search"
        return await update.message.reply_text("اكتب الاسم او الفيس")

    if state == "search":
        res = c.execute("SELECT name,fb FROM players WHERE name LIKE ? OR fb LIKE ?",
                        (f"%{text}%", f"%{text}%")).fetchall()
        context.user_data.clear()
        if not res:
            return await update.message.reply_text("ماكو لاعب")
        msg = "\n".join([f"{r[0]} | {r[1]}" for r in res])
        return await update.message.reply_text(msg)

    # ===== TRANSFER =====
    if text == "فتح الانتقالات":
        c.execute("UPDATE settings SET value='open'")
        conn.commit()
        return await update.message.reply_text("✅ تم فتح الانتقالات")

    if text == "غلق الانتقالات":
        c.execute("UPDATE settings SET value='closed'")
        conn.commit()
        return await update.message.reply_text("❌ تم غلق الانتقالات")

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

print("🚀 BOT STARTED...")
app.run_polling()
