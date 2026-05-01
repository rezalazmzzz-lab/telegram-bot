import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ياخذ التوكن من Railway
TOKEN = os.getenv("BOT_TOKEN")

# بيانات مؤقتة (بدلها لاحقاً بداتابيس)
clubs = {}
players = {}
transfers_open = False

# القوائم
main_menu = ReplyKeyboardMarkup([
    ["🏟️ عرض الأندية"],
    ["👑 إدارة القادة"],
    ["📬 الطلبات"],
    ["🔍 بحث لاعب"]
], resize_keyboard=True)

back_menu = ReplyKeyboardMarkup([
    ["🔙 رجوع"]
], resize_keyboard=True)

admin_menu = ReplyKeyboardMarkup([
    ["➕ إضافة قائد", "➖ حذف قائد"],
    ["🔄 فتح الانتقالات", "⛔ غلق الانتقالات"],
    ["🔙 رجوع"]
], resize_keyboard=True)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك في بوت الاتحاد", reply_markup=main_menu)


# عرض الأندية
async def show_clubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not clubs:
        await update.message.reply_text("❌ ماكو أندية")
        return

    msg = "🏟️ الأندية:\n\n"
    for club, data in clubs.items():
        msg += f"• {club}\n"
    await update.message.reply_text(msg)


# إدارة القادة
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 إدارة القادة:", reply_markup=admin_menu)


# فتح الانتقالات
async def open_transfers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfers_open
    transfers_open = True
    await update.message.reply_text("✅ تم فتح الانتقالات")


# غلق الانتقالات
async def close_transfers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfers_open
    transfers_open = False
    await update.message.reply_text("⛔ تم غلق الانتقالات")


# إضافة قائد (تحقق بسيط)
async def add_leader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 ارسل ID + رابط فيسبوك", reply_markup=back_menu)
    context.user_data["adding_leader"] = True


# استقبال بيانات القائد
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # رجوع
    if text == "🔙 رجوع":
        await update.message.reply_text("رجعنا للقائمة الرئيسية", reply_markup=main_menu)
        context.user_data.clear()
        return

    # إضافة قائد
    if context.user_data.get("adding_leader"):
        parts = text.split()

        if len(parts) != 2:
            await update.message.reply_text("❌ لازم ID + رابط فيسبوك")
            return

        user_id, fb = parts

        if not fb.startswith("https://"):
            await update.message.reply_text("❌ رابط الفيسبوك غير صحيح")
            return

        await update.message.reply_text("✅ تم إضافة القائد بنجاح")
        context.user_data.clear()
        return

    # البحث عن لاعب
    if context.user_data.get("search"):
        name = text.lower()
        result = ""

        for p in players.values():
            if name in p["name"].lower():
                result += f"👤 {p['name']} - {p['fb']}\n"

        if result == "":
            result = "❌ ماكو لاعب"

        await update.message.reply_text(result)
        context.user_data.clear()
        return

    # القائمة الرئيسية
    if text == "🏟️ عرض الأندية":
        await show_clubs(update, context)

    elif text == "👑 إدارة القادة":
        await handle_admin(update, context)

    elif text == "🔍 بحث لاعب":
        await update.message.reply_text("🔎 اكتب اسم اللاعب")
        context.user_data["search"] = True

    elif text == "📬 الطلبات":
        await update.message.reply_text("📬 لا توجد طلبات حالياً")

    elif text == "➕ إضافة قائد":
        await add_leader(update, context)

    elif text == "🔄 فتح الانتقالات":
        await open_transfers(update, context)

    elif text == "⛔ غلق الانتقالات":
        await close_transfers(update, context)

    else:
        await update.message.reply_text("❌ أمر غير معروف")


# MAIN
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
