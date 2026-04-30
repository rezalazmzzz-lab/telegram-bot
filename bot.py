import sqlite3
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 653170487

app_flask = Flask(__name__)

conn = sqlite3.connect("pes_bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS leaders (id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS clubs (name TEXT, owner_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS players (name TEXT, fb TEXT, serial TEXT UNIQUE, device TEXT, club TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS requests (name TEXT, fb TEXT, serial TEXT, device TEXT, club TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT, value TEXT)")
conn.commit()

cur.execute("INSERT OR IGNORE INTO admins VALUES (?)", (ADMIN_ID,))
conn.commit()

def is_admin(i): return cur.execute("SELECT 1 FROM admins WHERE id=?", (i,)).fetchone()
def is_leader(i): return cur.execute("SELECT 1 FROM leaders WHERE id=?", (i,)).fetchone()
def is_owner(i): return cur.execute("SELECT 1 FROM clubs WHERE owner_id=?", (i,)).fetchone()

def transfer_open():
    r = cur.execute("SELECT value FROM settings WHERE key='t'").fetchone()
    return r and r[0] == "1"

def set_transfer(v):
    cur.execute("DELETE FROM settings WHERE key='t'")
    cur.execute("INSERT INTO settings VALUES ('t',?)", (v,))
    conn.commit()

def menu(uid):
    if is_admin(uid):
        return [["➕ قائد","➖ قائد"],["➕ نادي"],["🏟️ الأندية"],["🔄 فتح","🔒 غلق"],["📥 الطلبات"]]
    if is_leader(uid):
        return [["📥 الطلبات"],["🏟️ الأندية"],["🔄 فتح","🔒 غلق"]]
    if is_owner(uid):
        return [["➕ لاعب"],["📋 لاعبين"]]
    return [["🚫"]]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("بوت اتحاد PES 🎮", reply_markup=ReplyKeyboardMarkup(menu(uid), resize_keyboard=True))

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    uid = update.effective_user.id
    s = context.user_data.get("s")

    if t=="➕ قائد" and is_admin(uid):
        context.user_data["s"]="addL"
        return await update.message.reply_text("ارسل ID")

    if s=="addL":
        cur.execute("INSERT INTO leaders VALUES (?)",(int(t),));conn.commit()
        context.user_data.clear()
        return await update.message.reply_text("تم إضافة قائد ✅")

    if t=="➕ نادي" and is_admin(uid):
        context.user_data["s"]="own"
        return await update.message.reply_text("ID رئيس النادي")

    if s=="own":
        context.user_data["oid"]=int(t)
        context.user_data["s"]="name"
        return await update.message.reply_text("اسم النادي")

    if s=="name":
        cur.execute("INSERT INTO clubs VALUES (?,?)",(t,context.user_data["oid"]))
        conn.commit();context.user_data.clear()
        return await update.message.reply_text("تم إضافة نادي ✅")

    if t=="➕ لاعب" and is_owner(uid):
        if not transfer_open():
            return await update.message.reply_text("الانتقالات مغلقة ❌")
        context.user_data["s"]="pn"
        return await update.message.reply_text("اسم اللاعب")

    if s=="pn":
        context.user_data["n"]=t;context.user_data["s"]="pf"
        return await update.message.reply_text("رابط الفيس")

    if s=="pf":
        context.user_data["f"]=t;context.user_data["s"]="ps"
        return await update.message.reply_text("الرقم التسلسلي")

    if s=="ps":
        context.user_data["sr"]=t;context.user_data["s"]="pd"
        return await update.message.reply_text("نوع الجهاز")

    if s=="pd":
        club=cur.execute("SELECT name FROM clubs WHERE owner_id=?",(uid,)).fetchone()[0]
        cur.execute("INSERT INTO requests VALUES (?,?,?,?,?)",
                    (context.user_data["n"],context.user_data["f"],context.user_data["sr"],t,club))
        conn.commit();context.user_data.clear()
        return await update.message.reply_text("تم إرسال الطلب ⏳")

    if t=="🏟️ الأندية":
        msg=""
        for c in cur.execute("SELECT * FROM clubs").fetchall():
            msg+=f"\n🏟️ {c[0]}\n"
            for p in cur.execute("SELECT name FROM players WHERE club=?",(c[0],)):
                msg+=f"- {p[0]}\n"
        return await update.message.reply_text(msg or "ماكو أندية")

    if t=="🔄 فتح" and (is_admin(uid) or is_leader(uid)):
        set_transfer("1")
        return await update.message.reply_text("تم فتح الانتقالات ✅")

    if t=="🔒 غلق" and (is_admin(uid) or is_leader(uid)):
        set_transfer("0")
        return await update.message.reply_text("تم غلق الانتقالات ❌")

    if t=="📥 الطلبات" and (is_admin(uid) or is_leader(uid)):
        for r in cur.execute("SELECT rowid,* FROM requests"):
            await update.message.reply_text(f"ID:{r[0]} | {r[1]} | {r[5]}")

def main():
    if not TOKEN:
        print("❌ التوكن مفقود")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("🚀 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
