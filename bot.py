import os
import re
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ✅ ياخذ التوكن من Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

leaders = {}
clubs = {}
transfers_open = False
user_state = {}

# ================= MENUS =================

def main_menu():
    return ReplyKeyboardMarkup([
        ["👑 إدارة القادة", "🏟️ إدارة الأندية"],
        ["📩 الطلبات", "🔍 بحث لاعب"]
    ], resize_keyboard=True)

def back_button():
    return ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك", reply_markup=main_menu())

# ================= VALIDATION =================

def is_valid_facebook(url):
    return "facebook.com" in url

# ================= HANDLER =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global transfers_open
    text = update.message.text
    user_id = update.message.from_user.id

    # ===== رجوع =====
    if text == "🔙 رجوع":
        user_state.pop(user_id, None)
        await update.message.reply_text("رجعنا للقائمة الرئيسية", reply_markup=main_menu())
        return

    # ===== إدارة القادة =====
    if text == "👑 إدارة القادة":
        await update.message.reply_text("اختر:", reply_markup=ReplyKeyboardMarkup([
            ["➕ إضافة قائد", "➖ حذف قائد"],
            ["🔙 رجوع"]
        ], resize_keyboard=True))
        return

    if text == "➕ إضافة قائد":
        user_state[user_id] = "add_leader_id"
        await update.message.reply_text("📌 أرسل ID القائد:", reply_markup=back_button())
        return

    if user_state.get(user_id) == "add_leader_id":
        if not text.isdigit():
            await update.message.reply_text("❌ لازم رقم صحيح")
            return
        context.user_data["leader_id"] = text
        user_state[user_id] = "add_leader_fb"
        await update.message.reply_text("📌 أرسل رابط الفيسبوك:")
        return

    if user_state.get(user_id) == "add_leader_fb":
        if not is_valid_facebook(text):
            await update.message.reply_text("❌ رابط غير صحيح")
            return
        leader_id = context.user_data["leader_id"]
        leaders[leader_id] = text
        user_state.pop(user_id)
        await update.message.reply_text("✅ تم إضافة القائد", reply_markup=main_menu())
        return

    # ===== إدارة الأندية =====
    if text == "🏟️ إدارة الأندية":
        await update.message.reply_text("اختر:", reply_markup=ReplyKeyboardMarkup([
            ["📋 عرض الأندية", "➕ إضافة نادي"],
            ["🟢 فتح الانتقالات", "🔴 غلق الانتقالات"],
            ["🔙 رجوع"]
        ], resize_keyboard=True))
        return

    # ===== إضافة نادي =====
    if text == "➕ إضافة نادي":
        user_state[user_id] = "club_name"
        await update.message.reply_text("📌 أرسل اسم النادي:", reply_markup=back_button())
        return

    if user_state.get(user_id) == "club_name":
        context.user_data["club_name"] = text
        user_state[user_id] = "club_leader_id"
        await update.message.reply_text("📌 أرسل ID رئيس النادي:")
        return

    if user_state.get(user_id) == "club_leader_id":
        if not text.isdigit():
            await update.message.reply_text("❌ ID غير صحيح")
            return
        context.user_data["club_leader_id"] = text
        user_state[user_id] = "club_leader_fb"
        await update.message.reply_text("📌 أرسل رابط فيسبوك الرئيس:")
        return

    if user_state.get(user_id) == "club_leader_fb":
        if not is_valid_facebook(text):
            await update.message.reply_text("❌ رابط غير صحيح")
            return

        name = context.user_data["club_name"]
        clubs[name] = {
            "leader_id": context.user_data["club_leader_id"],
            "leader_fb": text,
            "players": []
        }

        user_state.pop(user_id)
        await update.message.reply_text("✅ تم إضافة النادي", reply_markup=main_menu())
        return

    # ===== عرض الأندية =====
    if text == "📋 عرض الأندية":
        if not clubs:
            await update.message.reply_text("ماكو أندية")
            return

        msg = "🏟️ الأندية:\n"
        for club in clubs:
            msg += f"\n- {club} ({len(clubs[club]['players'])} لاعب)"

        await update.message.reply_text(msg)
        return

    # ===== الانتقالات =====
    if text == "🟢 فتح الانتقالات":
        transfers_open = True
        await update.message.reply_text("🟢 تم فتح الانتقالات")
        return

    if text == "🔴 غلق الانتقالات":
        transfers_open = False
        await update.message.reply_text("🔴 تم غلق الانتقالات")
        return

    # ===== إضافة لاعب =====
    if text == "➕ إضافة لاعب":
        if not transfers_open:
            await update.message.reply_text("❌ الانتقالات مغلقة")
            return

        user_state[user_id] = "player_name"
        await update.message.reply_text("📌 اسم اللاعب:")
        return

    if user_state.get(user_id) == "player_name":
        context.user_data["player_name"] = text
        user_state[user_id] = "player_fb"
        await update.message.reply_text("📌 رابط فيسبوك اللاعب:")
        return

    if user_state.get(user_id) == "player_fb":
        if not is_valid_facebook(text):
            await update.message.reply_text("❌ رابط غير صحيح")
            return

        context.user_data["player_fb"] = text
        user_state[user_id] = "player_id"
        await update.message.reply_text("📌 الرقم التسلسلي:")
        return

    if user_state.get(user_id) == "player_id":
        context.user_data["player_id"] = text

        if not clubs:
            await update.message.reply_text("❌ ماكو نادي")
            return

        club_name = list(clubs.keys())[0]

        clubs[club_name]["players"].append({
            "name": context.user_data["player_name"],
            "fb": context.user_data["player_fb"],
            "id": text
        })

        user_state.pop(user_id)
        await update.message.reply_text("✅ تم إضافة اللاعب")
        return

# ================= RUN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    app.run_polling()

if __name__ == "__main__":
    main()
