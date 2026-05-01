import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

clubs = {}
players = {}
leaders = []
transfer_open = False
user_state = {}

# ================== KEYBOARDS ==================

main_menu = ReplyKeyboardMarkup([
    ["👑 إدارة القادة", "🏟 إدارة الأندية"],
    ["📨 الطلبات", "🔍 بحث لاعب"]
], resize_keyboard=True)

leaders_menu = ReplyKeyboardMarkup([
    ["➕ إضافة قائد", "➖ حذف قائد"],
    ["🟢 فتح الانتقالات", "🔴 غلق الانتقالات"],
    ["🔙 رجوع"]
], resize_keyboard=True)

clubs_menu = ReplyKeyboardMarkup([
    ["📋 عرض الأندية", "➕ إضافة نادي"],
    ["🔙 رجوع"]
], resize_keyboard=True)

# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اهلا بك 👋", reply_markup=main_menu)

# ================== HANDLER ==================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfer_open

    text = update.message.text
    user_id = update.message.from_user.id

    # رجوع
    if text == "🔙 رجوع":
        user_state.pop(user_id, None)
        await update.message.reply_text("رجعنا للقائمة الرئيسية", reply_markup=main_menu)
        return

    # إدارة القادة
    if text == "👑 إدارة القادة":
        if user_id not in leaders:
            await update.message.reply_text("❌ فقط القادة")
            return
        await update.message.reply_text("إدارة القادة:", reply_markup=leaders_menu)

    elif text == "➕ إضافة قائد":
        user_state[user_id] = "add_leader"
        await update.message.reply_text("أرسل ID القائد")

    elif text == "➖ حذف قائد":
        user_state[user_id] = "remove_leader"
        await update.message.reply_text("أرسل ID للحذف")

    elif text == "🟢 فتح الانتقالات":
        transfer_open = True
        await update.message.reply_text("🟢 تم فتح الانتقالات")

    elif text == "🔴 غلق الانتقالات":
        transfer_open = False
        await update.message.reply_text("🔴 تم غلق الانتقالات")

    # إدارة الأندية
    elif text == "🏟 إدارة الأندية":
        await update.message.reply_text("إدارة الأندية:", reply_markup=clubs_menu)

    elif text == "➕ إضافة نادي":
        if user_id not in leaders:
            await update.message.reply_text("❌ فقط القادة")
            return
        user_state[user_id] = "club_name"
        await update.message.reply_text("أرسل اسم النادي")

    elif text == "📋 عرض الأندية":
        if not clubs:
            await update.message.reply_text("لا توجد أندية")
            return
        msg = ""
        for c in clubs:
            msg += f"🏟 {c}\n"
        await update.message.reply_text(msg)

    # بحث لاعب
    elif text == "🔍 بحث لاعب":
        user_state[user_id] = "search"
        await update.message.reply_text("أرسل اسم اللاعب أو رابط فيسبوك")

    # ================== STATES ==================

    elif user_id in user_state:

        state = user_state[user_id]

        # إضافة قائد
        if state == "add_leader":
            try:
                leaders.append(int(text))
                await update.message.reply_text("✅ تم إضافة قائد")
            except:
                await update.message.reply_text("❌ ID غير صالح")
            user_state.pop(user_id)

        elif state == "remove_leader":
            try:
                leaders.remove(int(text))
                await update.message.reply_text("✅ تم حذف القائد")
            except:
                await update.message.reply_text("❌ غير موجود")
            user_state.pop(user_id)

        # إضافة نادي
        elif state == "club_name":
            clubs[text] = {"players": []}
            context.user_data["club"] = text
            user_state[user_id] = "club_leader"
            await update.message.reply_text("أرسل ID رئيس النادي")

        elif state == "club_leader":
            try:
                clubs[context.user_data["club"]]["leader"] = int(text)
                user_state[user_id] = "club_fb"
                await update.message.reply_text("أرسل رابط الفيسبوك")
            except:
                await update.message.reply_text("❌ ID غلط")

        elif state == "club_fb":
            if "facebook.com" not in text:
                await update.message.reply_text("❌ رابط غير صحيح")
                return
            clubs[context.user_data["club"]]["fb"] = text
            await update.message.reply_text("✅ تم إضافة النادي")
            user_state.pop(user_id)

        # بحث لاعب
        elif state == "search":
            found = False
            for p in players.values():
                if text in p["name"] or text in p["fb"]:
                    msg = f"""
👤 {p['name']}
🔗 {p['fb']}
📱 {p['phone']}
"""
                    await update.message.reply_text(msg)
                    found = True
            if not found:
                await update.message.reply_text("❌ لم يتم العثور")
            user_state.pop(user_id)

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
