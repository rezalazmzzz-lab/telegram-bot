import logging
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)

TOKEN = "PUT_YOUR_TOKEN_HERE"
ADMIN_ID = 123456789  # حط ايديك هنا

logging.basicConfig(level=logging.INFO)

leaders = set()
clubs = {}

TRANSFERS_OPEN = False

# ================= تحقق =================
def is_valid_facebook(url):
    return bool(re.match(r"(https?://)?(www\.)?facebook\.com/.+", url))

async def is_real_user(app, user_id):
    try:
        await app.bot.get_chat(user_id)
        return True
    except:
        return False

# ================= القوائم =================
def main_menu():
    return ReplyKeyboardMarkup([
        ["👑 إدارة القادة", "🏟️ إدارة الأندية"],
        ["📥 الطلبات", "🔍 بحث لاعب"]
    ], resize_keyboard=True)

def leaders_menu():
    return ReplyKeyboardMarkup([
        ["➕ إضافة قائد", "➖ حذف قائد"],
        ["🔙 رجوع"]
    ], resize_keyboard=True)

def clubs_menu():
    return ReplyKeyboardMarkup([
        ["➕ إضافة نادي"],
        ["🏟️ عرض الأندية"],
        ["🔄 فتح الانتقالات", "🔒 غلق الانتقالات"],
        ["🔙 رجوع"]
    ], resize_keyboard=True)

def transfer_status():
    return "🟢 مفتوحة" if TRANSFERS_OPEN else "🔴 مغلقة"

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            f"👑 لوحة التحكم\n⚙️ الانتقالات: {transfer_status()}",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text("❌ هذا البوت خاص")

# ================= MENU =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "👑 إدارة القادة":
        await update.message.reply_text("👑 قسم القادة", reply_markup=leaders_menu())

    elif text == "🏟️ إدارة الأندية":
        await update.message.reply_text(
            f"🏟️ قسم الأندية\n⚙️ الانتقالات: {transfer_status()}",
            reply_markup=clubs_menu()
        )

    elif text == "🔙 رجوع":
        await start(update, context)

    elif text == "➕ إضافة قائد":
        context.user_data["state"] = "ADD_LEADER"
        await update.message.reply_text("📥 ارسل ID القائد")

    elif text == "➖ حذف قائد":
        context.user_data["state"] = "DEL_LEADER"
        await update.message.reply_text("📥 ارسل ID القائد للحذف")

    elif text == "➕ إضافة نادي":
        context.user_data["state"] = "ADD_CLUB_NAME"
        await update.message.reply_text("📛 اسم النادي؟")

    elif text == "🏟️ عرض الأندية":
        await show_clubs(update, context)

    elif text == "🔄 فتح الانتقالات":
        await open_transfers(update, context)

    elif text == "🔒 غلق الانتقالات":
        await close_transfers(update, context)

    elif text == "🔍 بحث لاعب":
        context.user_data["state"] = "SEARCH"
        await update.message.reply_text("🔍 اكتب اسم اللاعب او رابط الفيس")

# ================= القادة =================
async def handle_leaders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")

    if state == "ADD_LEADER":
        try:
            uid = int(update.message.text)
        except:
            await update.message.reply_text("❌ ايدي غير صحيح")
            return

        if not await is_real_user(context.application, uid):
            await update.message.reply_text("❌ المستخدم غير موجود")
            return

        leaders.add(uid)
        await update.message.reply_text("✅ تم إضافة قائد")
        context.user_data["state"] = None

    elif state == "DEL_LEADER":
        try:
            uid = int(update.message.text)
        except:
            return

        leaders.discard(uid)
        await update.message.reply_text("🗑️ تم حذف القائد")
        context.user_data["state"] = None

# ================= الأندية =================
async def handle_clubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")

    if state == "ADD_CLUB_NAME":
        context.user_data["club_name"] = update.message.text
        context.user_data["state"] = "ADD_CLUB_FB"
        await update.message.reply_text("🔗 رابط فيسبوك الرئيس")

    elif state == "ADD_CLUB_FB":
        if not is_valid_facebook(update.message.text):
            await update.message.reply_text("❌ رابط فيسبوك غير صحيح")
            return

        context.user_data["club_fb"] = update.message.text
        context.user_data["state"] = "ADD_CLUB_ID"
        await update.message.reply_text("🆔 ايدي الرئيس")

    elif state == "ADD_CLUB_ID":
        try:
            uid = int(update.message.text)
        except:
            await update.message.reply_text("❌ ايدي غلط")
            return

        if not await is_real_user(context.application, uid):
            await update.message.reply_text("❌ المستخدم غير موجود")
            return

        name = context.user_data["club_name"]

        clubs[name] = {
            "president": uid,
            "fb": context.user_data["club_fb"],
            "players": []
        }

        await update.message.reply_text(f"✅ تم إنشاء نادي {name}")
        context.user_data["state"] = None

# ================= عرض الأندية =================
async def show_clubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not clubs:
        await update.message.reply_text("❌ ماكو اندية")
        return

    for club, data in clubs.items():
        text = f"🏟️ {club}\n👤 الرئيس: {data['president']}"
        context.user_data["view_club"] = club

        btn = ReplyKeyboardMarkup([
            ["👥 عرض اللاعبين"],
            ["🔙 رجوع"]
        ], resize_keyboard=True)

        await update.message.reply_text(text, reply_markup=btn)

# ================= اللاعبين =================
async def players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "👥 عرض اللاعبين":
        club = context.user_data.get("view_club")

        if not club:
            await update.message.reply_text("❌ خطأ")
            return

        plist = clubs[club]["players"]

        if not plist:
            await update.message.reply_text("❌ ماكو لاعبين")
            return

        for p in plist:
            await update.message.reply_text(
                f"👤 {p['name']}\n🔗 {p['fb']}\n🆔 {p['id']}"
            )

# ================= البحث =================
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "SEARCH":
        return

    text = update.message.text

    for club in clubs:
        for p in clubs[club]["players"]:
            if text in p["name"] or text in p["fb"]:
                await update.message.reply_text(
                    f"📌 {p['name']}\n🏟️ {club}\n🔗 {p['fb']}"
                )
                return

    await update.message.reply_text("❌ ماكو نتيجة")
    context.user_data["state"] = None

# ================= الانتقالات =================
async def open_transfers(update, context):
    global TRANSFERS_OPEN

    if update.effective_user.id != ADMIN_ID:
        return

    TRANSFERS_OPEN = True
    await update.message.reply_text("🟢 تم فتح الانتقالات")

async def close_transfers(update, context):
    global TRANSFERS_OPEN

    if update.effective_user.id != ADMIN_ID:
        return

    TRANSFERS_OPEN = False
    await update.message.reply_text("🔴 تم غلق الانتقالات")

# ================= تشغيل =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_leaders))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_clubs))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, players_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
