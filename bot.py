import os
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ التوكن من Railway
TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 653170487

leaders = set([OWNER_ID])
clubs = {}
requests = []
transfer_open = False

# ---------- MENUS ----------
def main_menu():
    return ReplyKeyboardMarkup([
        ["👑 إدارة القادة", "🏟 إدارة الأندية"],
        ["📥 الطلبات", "🔍 بحث لاعب"]
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

# ---------- HELPERS ----------
async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def valid_fb(link):
    return link.startswith("https://www.facebook.com/")

def get_user_club(uid):
    for c in clubs:
        if clubs[c]["president"] == uid:
            return c
    return None

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 البوت شغال", reply_markup=main_menu())

# ---------- HANDLER ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfer_open

    text = update.message.text
    uid = update.effective_user.id
    state = context.user_data.get("state")

    # رجوع
    if text == "🔙 رجوع":
        context.user_data.clear()
        return await update.message.reply_text("رجعنا", reply_markup=main_menu())

    # ===== القادة =====
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
            return await update.message.reply_text("❌ خليه يسوي /start")

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

    # ===== الأندية =====
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

    # إضافة نادي
    if text == "➕ إضافة نادي":
        context.user_data["state"] = "pres_name"
        return await update.message.reply_text("اسم رئيس النادي:")

    if state == "pres_name":
        context.user_data["pres_name"] = text
        context.user_data["state"] = "pres_fb"
        return await update.message.reply_text("رابط الفيس:")

    if state == "pres_fb":
        if not valid_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["pres_fb"] = text
        context.user_data["state"] = "pres_id"
        return await update.message.reply_text("ID التلكرام:")

    if state == "pres_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ خليه يسوي /start")

        context.user_data["pres_id"] = int(text)
        context.user_data["state"] = "club_name"
        return await update.message.reply_text("اسم النادي:")

    if state == "club_name":
        clubs[text] = {
            "president": context.user_data["pres_id"],
            "pres_name": context.user_data["pres_name"],
            "fb": context.user_data["pres_fb"],
            "players": []
        }

        # 🔥 إعطاء صلاحية للرئيس
        leaders.add(context.user_data["pres_id"])

        context.user_data.clear()
        return await update.message.reply_text("✅ تم إنشاء النادي وإعطاء الصلاحيات")

    # عرض الأندية
    if text == "📋 عرض الأندية":
        if not clubs:
            return await update.message.reply_text("❌ ماكو أندية")

        keyboard = []
        for c in clubs:
            keyboard.append([f"👥 عرض لاعبين {c}"])

        return await update.message.reply_text(
            "🏟 الأندية:",
            reply_markup=ReplyKeyboardMarkup(keyboard + [["🔙 رجوع"]], resize_keyboard=True)
        )

    # عرض لاعبين
    if text.startswith("👥 عرض لاعبين"):
        club = text.replace("👥 عرض لاعبين ", "")

        players = clubs[club]["players"]

        if not players:
            return await update.message.reply_text("❌ ماكو لاعبين")

        msg = f"🏟 {club}\n"

        for p in players:
            msg += f"\n🔹 {p['id']} | {p['name']}\n🔗 {p['fb']}\n📸 {p['screen']}\n"

        return await update.message.reply_text(msg)

    # ===== إضافة لاعب (طلب) =====
    if text == "➕ إضافة لاعب":
        if not transfer_open:
            return await update.message.reply_text("❌ الانتقالات مغلقة")

        club = get_user_club(uid)
        if not club:
            return await update.message.reply_text("❌ انت مو رئيس نادي")

        context.user_data["club"] = club
        context.user_data["state"] = "p_name"
        return await update.message.reply_text("اسم اللاعب:")

    if state == "p_name":
        context.user_data["name"] = text
        context.user_data["state"] = "p_fb"
        return await update.message.reply_text("رابط الفيس:")

    if state == "p_fb":
        if not valid_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["fb"] = text
        context.user_data["state"] = "p_screen"
        return await update.message.reply_text("رابط السكرين:")

    if state == "p_screen":
        requests.append({
            "club": context.user_data["club"],
            "name": context.user_data["name"],
            "fb": context.user_data["fb"],
            "screen": text
        })

        context.user_data.clear()
        return await update.message.reply_text("📥 تم إرسال الطلب")

    # ===== الطلبات =====
    if text == "📥 الطلبات":
        if uid not in leaders:
            return await update.message.reply_text("❌ فقط القادة")

        if not requests:
            return await update.message.reply_text("❌ ماكو طلبات")

        msg = ""
        for i, r in enumerate(requests):
            msg += f"{i} - {r['name']} ({r['club']})\n"

        context.user_data["state"] = "approve"
        return await update.message.reply_text(msg + "\nارسل رقم الطلب")

    if state == "approve":
        i = int(text)
        context.user_data["req"] = i
        context.user_data["state"] = "decision"
        return await update.message.reply_text("✅ موافقة او ❌ رفض")

    if state == "decision":
        r = requests[context.user_data["req"]]

        if "موافقة" in text:
            players = clubs[r["club"]]["players"]
            players.append({
                "id": len(players)+1,
                "name": r["name"],
                "fb": r["fb"],
                "screen": r["screen"]
            })
            await update.message.reply_text("✅ تمت الموافقة")

        else:
            await update.message.reply_text("❌ تم الرفض")

        requests.pop(context.user_data["req"])
        context.user_data.clear()

    # ===== البحث =====
    if text == "🔍 بحث لاعب":
        context.user_data["state"] = "search"
        return await update.message.reply_text("اكتب الاسم او الفيس")

    if state == "search":
        for c in clubs:
            for p in clubs[c]["players"]:
                if text in p["name"] or text in p["fb"]:
                    context.user_data.clear()
                    return await update.message.reply_text(
                        f"{p['name']}\n{c}\n{p['fb']}\n{p['screen']}"
                    )

        return await update.message.reply_text("❌ ماكو")

# ---------- RUN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
