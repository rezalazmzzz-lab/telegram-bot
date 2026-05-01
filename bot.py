import os
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# ================= DATA =================
leaders = {653170487}  # 👑 انت
clubs = {}  # club_name: {owner_id, owner_name, fb, players:[]}
requests = []  # طلبات اللاعبين
transfer_open = False

# ================= MENUS =================
def main_menu():
    return ReplyKeyboardMarkup([
        ["👑 القادة", "🏟 الأندية"],
        ["📥 الطلبات", "🔍 بحث لاعب"]
    ], resize_keyboard=True)

def back():
    return ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True)

# ================= VALIDATION =================
def is_fb(link):
    return "facebook.com" in link

async def valid_user(app, uid):
    try:
        await app.bot.get_chat(uid)
        return True
    except:
        return False

def find_player(text):
    for c in clubs:
        for p in clubs[c]["players"]:
            if text in p["name"] or text in p["fb"]:
                return c, p
    return None, None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً", reply_markup=main_menu())

# ================= HANDLER =================
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfer_open

    text = update.message.text
    uid = update.effective_user.id
    state = context.user_data.get("s")

    # رجوع
    if text == "🔙 رجوع":
        context.user_data.clear()
        return await update.message.reply_text("رجعنا", reply_markup=main_menu())

    # ================= القادة =================
    if text == "👑 القادة":
        if uid not in leaders:
            return await update.message.reply_text("❌ مو قائد")
        return await update.message.reply_text("👑 إدارة القادة", reply_markup=ReplyKeyboardMarkup([
            ["➕ قائد"],
            ["🔙 رجوع"]
        ], resize_keyboard=True))

    if text == "➕ قائد":
        context.user_data["s"] = "leader_id"
        return await update.message.reply_text("ارسل ID:")

    if state == "leader_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ هذا ID غير موجود")

        context.user_data["lid"] = int(text)
        context.user_data["s"] = "leader_fb"
        return await update.message.reply_text("ارسل رابط الفيس:")

    if state == "leader_fb":
        if not is_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        leaders.add(context.user_data["lid"])
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إضافة قائد")

    # ================= الأندية =================
    if text == "🏟 الأندية":
        return await update.message.reply_text("🏟 إدارة الأندية", reply_markup=ReplyKeyboardMarkup([
            ["➕ نادي", "📋 عرض"],
            ["🔄 فتح", "🔒 غلق"],
            ["🔙 رجوع"]
        ], resize_keyboard=True))

    # إضافة نادي
    if text == "➕ نادي":
        if uid not in leaders:
            return await update.message.reply_text("❌ فقط القادة")

        context.user_data["s"] = "owner_name"
        return await update.message.reply_text("اسم رئيس النادي:")

    if state == "owner_name":
        context.user_data["oname"] = text
        context.user_data["s"] = "owner_fb"
        return await update.message.reply_text("رابط الفيس:")

    if state == "owner_fb":
        if not is_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["ofb"] = text
        context.user_data["s"] = "owner_id"
        return await update.message.reply_text("ID التلكرام:")

    if state == "owner_id":
        if not text.isdigit():
            return await update.message.reply_text("❌ ID غلط")

        if not await valid_user(context.application, int(text)):
            return await update.message.reply_text("❌ ID غير موجود")

        context.user_data["oid"] = int(text)
        context.user_data["s"] = "club_name"
        return await update.message.reply_text("اسم النادي:")

    if state == "club_name":
        clubs[text] = {
            "owner_id": context.user_data["oid"],
            "owner_name": context.user_data["oname"],
            "fb": context.user_data["ofb"],
            "players": []
        }
        context.user_data.clear()
        return await update.message.reply_text("✅ تم إنشاء النادي")

    # عرض الأندية
    if text == "📋 عرض":
        msg = ""
        for c in clubs:
            msg += f"\n🏟 {c}\n👤 {clubs[c]['owner_name']}\n"
        return await update.message.reply_text(msg or "ماكو أندية")

    # ================= الانتقالات =================
    if text == "🔄 فتح" and uid in leaders:
        transfer_open = True
        return await update.message.reply_text("🟢 تم فتح الانتقالات")

    if text == "🔒 غلق" and uid in leaders:
        transfer_open = False
        return await update.message.reply_text("🔴 تم غلق الانتقالات")

    # ================= رئيس النادي =================
    for c in clubs:
        if uid == clubs[c]["owner_id"]:

            # إضافة لاعب
            if text == "➕ لاعب":
                if not transfer_open:
                    return await update.message.reply_text("❌ مغلقة")

                context.user_data["s"] = "p_name"
                context.user_data["club"] = c
                return await update.message.reply_text("اسم اللاعب:")

    # بيانات اللاعب
    if state == "p_name":
        context.user_data["pn"] = text
        context.user_data["s"] = "p_fb"
        return await update.message.reply_text("فيس:")

    if state == "p_fb":
        if not is_fb(text):
            return await update.message.reply_text("❌ رابط غلط")

        context.user_data["pf"] = text
        context.user_data["s"] = "p_serial"
        return await update.message.reply_text("Serial:")

    if state == "p_serial":
        # منع التكرار
        for c in clubs:
            for p in clubs[c]["players"]:
                if p["serial"] == text or p["fb"] == context.user_data["pf"]:
                    return await update.message.reply_text("❌ لاعب مكرر")

        # إرسال طلب
        requests.append({
            "name": context.user_data["pn"],
            "fb": context.user_data["pf"],
            "serial": text,
            "club": context.user_data["club"]
        })

        context.user_data.clear()
        return await update.message.reply_text("📥 تم إرسال الطلب")

    # ================= الطلبات =================
    if text == "📥 الطلبات" and uid in leaders:
        if not requests:
            return await update.message.reply_text("❌ ماكو طلبات")

        for i, r in enumerate(requests):
            await update.message.reply_text(
                f"{i}\n{r['name']} - {r['club']}"
            )
        context.user_data["s"] = "review"

    if state == "review":
        try:
            idx = int(text)
            r = requests[idx]
        except:
            return await update.message.reply_text("❌ رقم غلط")

        clubs[r["club"]]["players"].append(r)
        requests.pop(idx)

        context.user_data.clear()
        return await update.message.reply_text("✅ تمت الموافقة")

    # ================= البحث =================
    if text == "🔍 بحث لاعب":
        context.user_data["s"] = "search"
        return await update.message.reply_text("اكتب الاسم او الفيس")

    if state == "search":
        c, p = find_player(text)
        context.user_data.clear()

        if not p:
            return await update.message.reply_text("❌ ماكو")

        return await update.message.reply_text(
            f"👤 {p['name']}\n🏟 {c}\n🔗 {p['fb']}\n📱 {p['serial']}"
        )

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    app.run_polling()

if __name__ == "__main__":
    main()
