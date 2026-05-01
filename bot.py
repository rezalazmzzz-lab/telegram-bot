import os
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

leaders = set([OWNER_ID])
clubs = {}
transfer_open = False

# ---------------- MENUS ----------------
def main_menu():
    return ReplyKeyboardMarkup([
        ["👑 إدارة القادة", "🏟 إدارة الأندية"],
        ["🔍 بحث لاعب"]
    ], resize_keyboard=True)

def leaders_menu():
    return ReplyKeyboardMarkup([
        ["➕ إضافة قائد", "❌ حذف قائد"],
        ["🔙 رجوع"]
    ], resize_keyboard=True)

def clubs_menu():
    return ReplyKeyboardMarkup([
        ["➕ إضافة نادي", "📋 عرض الأندية"],
        ["🟢 فتح الانتقالات", "🔴 غلق الانتقالات"],
        ["🔙 رجوع"]
    ], resize_keyboard=True)

# ---------------- VALIDATION ----------------
async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def valid_fb(link):
    return link.startswith("https://www.facebook.com/")

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 البوت شغال", reply_markup=main_menu())

# ---------------- HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfer_open

    text = update.message.text
    uid = update.effective_user.id
    state = context.user_data.get("state")

    # رجوع
    if text == "🔙 رجوع":
        context.user_data.clear()
        return await update.message.reply_text("رجعنا", reply_markup=main_menu())

    # ========= القادة =========
    if text == "👑 إدارة القادة":
        if uid != OWNER_ID:
            return await update.message.reply_text("❌ فقط المالك")
        return await update.message.reply_text("👑", reply_markup=leaders_menu())

    if text == "➕ إضافة قائد":
        context.user_data["state"] = "add_leader"
        return await update.message.reply_text("ارسل ID:")

    if state == "add_leader":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ خليه يدخل البوت /start")

        leaders.add(int(text))
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إضافة قائد")

    if text == "❌ حذف قائد":
        context.user_data["state"] = "del_leader"
        return await update.message.reply_text("ارسل ID:")

    if state == "del_leader":
        try:
            leaders.remove(int(text))
            await update.message.reply_text("✅ تم الحذف")
        except:
            await update.message.reply_text("❌ مو موجود")
        context.user_data.clear()

    # ========= الأندية =========
    if text == "🏟 إدارة الأندية":
        if uid not in leaders:
            return await update.message.reply_text("❌ ما عندك صلاحية")
        return await update.message.reply_text("🏟", reply_markup=clubs_menu())

    if text == "🟢 فتح الانتقالات" and uid in leaders:
        transfer_open = True
        return await update.message.reply_text("🟢 مفتوحة")

    if text == "🔴 غلق الانتقالات" and uid in leaders:
        transfer_open = False
        return await update.message.reply_text("🔴 مغلقة")

    if text == "➕ إضافة نادي":
        context.user_data["state"] = "owner_name"
        return await update.message.reply_text("اسم رئيس النادي:")

    if state == "owner_name":
        context.user_data["owner_name"] = text
        context.user_data["state"] = "owner_fb"
        return await update.message.reply_text("رابط الفيس:")

    if state == "owner_fb":
        if not valid_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["owner_fb"] = text
        context.user_data["state"] = "owner_id"
        return await update.message.reply_text("ID التلكرام:")

    if state == "owner_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ خليه يسوي /start")

        context.user_data["owner_id"] = int(text)
        context.user_data["state"] = "club_name"
        return await update.message.reply_text("اسم النادي:")

    if state == "club_name":
        clubs[text] = {
            "owner_id": context.user_data["owner_id"],
            "owner_name": context.user_data["owner_name"],
            "fb": context.user_data["owner_fb"],
            "players": []
        }
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إنشاء النادي")

    # عرض الأندية + اللاعبين
    if text == "📋 عرض الأندية":
        if not clubs:
            return await update.message.reply_text("❌ ماكو أندية")

        for c in clubs:
            msg = f"🏟 {c}\n👤 {clubs[c]['owner_name']}\n"

            if clubs[c]["players"]:
                msg += "\n👥 اللاعبين:\n"
                for p in clubs[c]["players"]:
                    msg += (
                        f"\n🔹 رقم: {p['id']}"
                        f"\n👤 {p['name']}"
                        f"\n🔗 {p['fb']}"
                        f"\n📸 {p['screen']}\n"
                        "----------------"
                    )
            else:
                msg += "\n❌ ماكو لاعبين"

            await update.message.reply_text(msg)

    # ========= إضافة لاعب =========
    for c in clubs:
        if uid == clubs[c]["owner_id"]:

            if text == "➕ إضافة لاعب":
                if not transfer_open:
                    return await update.message.reply_text("❌ مغلقة")

                context.user_data["state"] = "p_name"
                context.user_data["club"] = c
                return await update.message.reply_text("اسم اللاعب:")

    if state == "p_name":
        context.user_data["pname"] = text
        context.user_data["state"] = "p_fb"
        return await update.message.reply_text("فيس:")

    if state == "p_fb":
        if not valid_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["pfb"] = text
        context.user_data["state"] = "p_screen"
        return await update.message.reply_text("رابط السكرين:")

    if state == "p_screen":
        club = context.user_data["club"]
        players = clubs[club]["players"]

        players.append({
            "id": len(players) + 1,
            "name": context.user_data["pname"],
            "fb": context.user_data["pfb"],
            "screen": text
        })

        context.user_data.clear()
        return await update.message.reply_text("✅ تم إضافة اللاعب")

    # ========= البحث =========
    if text == "🔍 بحث لاعب":
        context.user_data["state"] = "search"
        return await update.message.reply_text("اكتب الاسم او الفيس")

    if state == "search":
        for c in clubs:
            for p in clubs[c]["players"]:
                if text in p["name"] or text in p["fb"]:
                    context.user_data.clear()
                    return await update.message.reply_text(
                        f"👤 {p['name']}\n🏟 {c}\n🔗 {p['fb']}\n📸 {p['screen']}"
                    )

        return await update.message.reply_text("❌ ماكو")

# ---------------- RUN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
