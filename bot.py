import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 653170487

leaders = set([OWNER_ID])
clubs = {}
requests = []
transfer_open = False

# ================= MENUS =================
def main_menu():
    return ReplyKeyboardMarkup([
        ["👑 إدارة القادة", "🏟 إدارة الأندية"],
        ["📥 الطلبات", "🔍 بحث لاعب"]
    ], resize_keyboard=True)

def back():
    return ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True)

# ================= VALIDATION =================
async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def valid_fb(link):
    return link.startswith("https://www.facebook.com/")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 البوت شغال", reply_markup=main_menu())

# ================= MAIN HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfer_open

    text = update.message.text
    uid = update.effective_user.id
    state = context.user_data.get("state")

    # رجوع
    if text == "🔙 رجوع":
        context.user_data.clear()
        return await update.message.reply_text("رجعنا", reply_markup=main_menu())

    # ================= القادة =================
    if text == "👑 إدارة القادة":
        if uid != OWNER_ID:
            return await update.message.reply_text("❌ فقط المالك")
        return await update.message.reply_text("👑 القادة", reply_markup=ReplyKeyboardMarkup([
            ["➕ إضافة قائد"],
            ["🔙 رجوع"]
        ], resize_keyboard=True))

    if text == "➕ إضافة قائد":
        context.user_data["state"] = "add_leader"
        return await update.message.reply_text("ارسل ID:")

    if state == "add_leader":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ خليه يدخل البوت اول")

        leaders.add(int(text))
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إضافة قائد")

    # ================= الأندية =================
    if text == "🏟 إدارة الأندية":
        return await update.message.reply_text("🏟", reply_markup=ReplyKeyboardMarkup([
            ["➕ إضافة نادي", "📋 عرض الأندية"],
            ["🟢 فتح الانتقالات", "🔴 غلق الانتقالات"],
            ["🔙 رجوع"]
        ], resize_keyboard=True))

    if text == "🟢 فتح الانتقالات" and uid in leaders:
        transfer_open = True
        return await update.message.reply_text("🟢 مفتوحة")

    if text == "🔴 غلق الانتقالات" and uid in leaders:
        transfer_open = False
        return await update.message.reply_text("🔴 مغلقة")

    if text == "➕ إضافة نادي":
        if uid not in leaders:
            return await update.message.reply_text("❌ فقط القادة")

        context.user_data["state"] = "club_owner_name"
        return await update.message.reply_text("اسم رئيس النادي:")

    if state == "club_owner_name":
        context.user_data["owner_name"] = text
        context.user_data["state"] = "club_owner_fb"
        return await update.message.reply_text("رابط الفيس:")

    if state == "club_owner_fb":
        if not valid_fb(text):
            return await update.message.reply_text("❌ رابط غير صحيح")

        context.user_data["owner_fb"] = text
        context.user_data["state"] = "club_owner_id"
        return await update.message.reply_text("ID التلكرام:")

    if state == "club_owner_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ خليه يدخل البوت")

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

    if text == "📋 عرض الأندية":
        if not clubs:
            return await update.message.reply_text("❌ ماكو أندية")

        msg = ""
        for c in clubs:
            msg += f"\n🏟 {c}\n👤 {clubs[c]['owner_name']}\n"
        return await update.message.reply_text(msg)

    # ================= إضافة لاعب =================
    for c in clubs:
        if uid == clubs[c]["owner_id"]:

            if text == "➕ إضافة لاعب":
                if not transfer_open:
                    return await update.message.reply_text("❌ الانتقالات مغلقة")

                context.user_data["state"] = "player_name"
                context.user_data["club"] = c
                return await update.message.reply_text("اسم اللاعب:")

    if state == "player_name":
        context.user_data["pname"] = text
        context.user_data["state"] = "player_fb"
        return await update.message.reply_text("فيس اللاعب:")

    if state == "player_fb":
        if not valid_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["pfb"] = text
        context.user_data["state"] = "player_serial"
        return await update.message.reply_text("serial:")

    if state == "player_serial":
        requests.append({
            "name": context.user_data["pname"],
            "fb": context.user_data["pfb"],
            "serial": text,
            "club": context.user_data["club"]
        })
        context.user_data.clear()
        return await update.message.reply_text("📥 انرسل طلب")

    # ================= الطلبات =================
    if text == "📥 الطلبات":
        if uid not in leaders:
            return await update.message.reply_text("❌ فقط القادة")

        if not requests:
            return await update.message.reply_text("❌ ماكو طلبات")

        msg = ""
        for i, r in enumerate(requests):
            msg += f"{i} - {r['name']} ({r['club']})\n"
        context.user_data["state"] = "approve"
        return await update.message.reply_text(msg + "\nارسل الرقم للموافقة")

    if state == "approve":
        try:
            i = int(text)
            r = requests[i]
        except:
            return await update.message.reply_text("❌ رقم غلط")

        clubs[r["club"]]["players"].append(r)
        requests.pop(i)

        context.user_data.clear()
        return await update.message.reply_text("✅ تمت الموافقة")

    # ================= البحث =================
    if text == "🔍 بحث لاعب":
        context.user_data["state"] = "search"
        return await update.message.reply_text("اكتب الاسم او الفيس")

    if state == "search":
        for c in clubs:
            for p in clubs[c]["players"]:
                if text in p["name"] or text in p["fb"]:
                    context.user_data.clear()
                    return await update.message.reply_text(
                        f"👤 {p['name']}\n🏟 {c}\n🔗 {p['fb']}\n📱 {p['serial']}"
                    )

        return await update.message.reply_text("❌ ماكو")

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == "__main__":
    main()
