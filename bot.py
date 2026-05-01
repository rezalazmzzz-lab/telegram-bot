from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_BOT_TOKEN"

clubs = {}
players = {}
leaders = []

transfer_open = False

# ------------------- القوائم -------------------

main_menu = ReplyKeyboardMarkup([
    ["👑 إدارة القادة", "🏟 إدارة الأندية"],
    ["📩 الطلبات", "🔍 بحث لاعب"]
], resize_keyboard=True)

leaders_menu = ReplyKeyboardMarkup([
    ["➕ قائد", "➖ حذف قائد"],
    ["🔙 رجوع"]
], resize_keyboard=True)

clubs_menu = ReplyKeyboardMarkup([
    ["➕ إضافة نادي", "📋 عرض الأندية"],
    ["🟢 فتح الانتقالات", "🔴 غلق الانتقالات"],
    ["🔙 رجوع"]
], resize_keyboard=True)

back_menu = ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True)

# ------------------- أدوات -------------------

def is_valid_id(user_id):
    return str(user_id).isdigit() and len(str(user_id)) >= 6

# ------------------- START -------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 بوت الاتحاد", reply_markup=main_menu)

# ------------------- HANDLER -------------------

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfer_open
    
    text = update.message.text
    user_id = update.effective_user.id

    # رجوع
    if text == "🔙 رجوع":
        context.user_data.clear()
        await update.message.reply_text("🔙 رجعنا", reply_markup=main_menu)
        return

    # القوائم
    if text == "👑 إدارة القادة":
        await update.message.reply_text("👑 إدارة القادة", reply_markup=leaders_menu)
        return

    if text == "🏟 إدارة الأندية":
        await update.message.reply_text("🏟 إدارة الأندية", reply_markup=clubs_menu)
        return

    # ------------------- القادة -------------------

    if text == "➕ قائد":
        context.user_data["add_leader"] = True
        await update.message.reply_text("📌 ارسل ID:")
        return

    if context.user_data.get("add_leader"):
        if not is_valid_id(text):
            await update.message.reply_text("❌ ID غير صحيح")
            return
        
        leaders.append(int(text))
        context.user_data.clear()
        await update.message.reply_text("✅ تم إضافة قائد")
        return

    # ------------------- الانتقالات -------------------

    if text == "🟢 فتح الانتقالات":
        transfer_open = True
        await update.message.reply_text("🟢 تم فتح الانتقالات")
        return

    if text == "🔴 غلق الانتقالات":
        transfer_open = False
        await update.message.reply_text("🔴 تم غلق الانتقالات")
        return

    # ------------------- الأندية -------------------

    if text == "➕ إضافة نادي":
        context.user_data["club_name"] = True
        await update.message.reply_text("📌 ارسل اسم النادي:")
        return

    if context.user_data.get("club_name"):
        context.user_data["club"] = text
        context.user_data["club_id"] = True
        await update.message.reply_text("📌 ارسل ID رئيس النادي:")
        return

    if context.user_data.get("club_id"):
        if not is_valid_id(text):
            await update.message.reply_text("❌ ID غير صحيح")
            return
        
        context.user_data["president_id"] = int(text)
        context.user_data["club_fb"] = True
        await update.message.reply_text("📌 ارسل رابط فيسبوك:")
        return

    if context.user_data.get("club_fb"):
        if "facebook.com" not in text:
            await update.message.reply_text("❌ رابط غير صحيح")
            return
        
        club_name = context.user_data["club"]
        clubs[club_name] = {
            "president": context.user_data["president_id"],
            "players": []
        }

        context.user_data.clear()
        await update.message.reply_text(f"✅ تم إنشاء نادي {club_name}")
        return

    # عرض الأندية
    if text == "📋 عرض الأندية":
        if not clubs:
            await update.message.reply_text("❌ لا يوجد أندية")
        else:
            msg = "📋 الأندية:\n\n"
            for c in clubs:
                msg += f"🏟 {c}\n"
            await update.message.reply_text(msg)
        return

    # ------------------- إضافة لاعب -------------------

    if text == "➕ لاعب":
        if not transfer_open:
            await update.message.reply_text("❌ الانتقالات مغلقة")
            return
        
        context.user_data["player_name"] = True
        await update.message.reply_text("📌 اسم اللاعب:")
        return

    if context.user_data.get("player_name"):
        context.user_data["name"] = text
        context.user_data["player_fb"] = True
        await update.message.reply_text("📌 رابط الفيسبوك:")
        return

    if context.user_data.get("player_fb"):
        if "facebook.com" not in text:
            await update.message.reply_text("❌ رابط غير صحيح")
            return
        
        context.user_data["fb"] = text
        context.user_data["serial"] = True
        await update.message.reply_text("📌 الرقم التسلسلي:")
        return

    if context.user_data.get("serial"):
        pid = len(players) + 1
        players[pid] = {
            "name": context.user_data["name"],
            "fb": context.user_data["fb"],
            "serial": text
        }

        context.user_data.clear()
        await update.message.reply_text("✅ تم إضافة اللاعب")
        return

    # ------------------- البحث -------------------

    if text == "🔍 بحث لاعب":
        context.user_data["search"] = True
        await update.message.reply_text("📌 اكتب الاسم او الرابط:")
        return

    if context.user_data.get("search"):
        found = False

        for p in players.values():
            if text in p["name"] or text in p["fb"]:
                await update.message.reply_text(
                    f"👤 {p['name']}\n📘 {p['fb']}\n📱 {p['serial']}"
                )
                found = True

        if not found:
            await update.message.reply_text("❌ ماكو لاعب")

        context.user_data.clear()
        return

# ------------------- تشغيل -------------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

app.run_polling()
