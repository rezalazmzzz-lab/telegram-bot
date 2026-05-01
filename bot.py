import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils import executor

# ✅ جلب التوكن من Railway
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 🗄️ بيانات مؤقتة
users = {}
leaders = set()
clubs = {}
requests = []

OWNER_ID = 653170487  # 👑 هذا ID مالك البوت

# 🎛️ الواجهة الرئيسية
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("إدارة الأندية", "إدارة القادة")
main_kb.add("بحث لاعب", "الطلبات")

# =========================
# 🔰 START
# =========================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    users[msg.from_user.id] = True
    await msg.reply("أهلاً بك 👋", reply_markup=main_kb)

# =========================
# 👑 إدارة القادة
# =========================
@dp.message_handler(lambda m: m.text == "إدارة القادة")
async def leaders_menu(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ ما عندك صلاحية")

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("إضافة قائد", "حذف قائد", "رجوع")

    await msg.reply("إدارة القادة:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "إضافة قائد")
async def add_leader(msg: types.Message):
    await msg.reply("ارسل ID:")

    @dp.message_handler()
    async def process_id(m: types.Message):
        try:
            uid = int(m.text)

            if uid not in users:
                return await m.reply("❌ المستخدم لازم يدخل البوت")

            leaders.add(uid)
            await m.reply("✅ تم إضافة قائد")
        except:
            await m.reply("❌ ID غير صحيح")

        dp.message_handlers.unregister(process_id)

# =========================
# 🏟️ إدارة الأندية
# =========================
@dp.message_handler(lambda m: m.text == "إدارة الأندية")
async def clubs_menu(msg: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("إضافة نادي", "عرض الأندية", "رجوع")

    await msg.reply("إدارة الأندية:", reply_markup=kb)

# ➕ إضافة نادي
@dp.message_handler(lambda m: m.text == "إضافة نادي")
async def add_club(msg: types.Message):
    await msg.reply("اسم النادي؟")

    @dp.message_handler()
    async def get_name(m: types.Message):
        club_name = m.text
        await m.reply("ID رئيس النادي؟")

        @dp.message_handler()
        async def get_owner(o: types.Message):
            try:
                owner_id = int(o.text)

                if owner_id not in users:
                    return await o.reply("❌ المستخدم مو داخل البوت")

                clubs[club_name] = {
                    "owner": owner_id,
                    "players": []
                }

                await o.reply(f"✅ تم إضافة نادي {club_name}")
            except:
                await o.reply("❌ ID خطأ")

            dp.message_handlers.unregister(get_owner)
            dp.message_handlers.unregister(get_name)

# 📋 عرض الأندية
@dp.message_handler(lambda m: m.text == "عرض الأندية")
async def show_clubs(msg: types.Message):
    if not clubs:
        return await msg.reply("❌ ماكو أندية")

    text = "🏟️ الأندية:\n"
    for c in clubs:
        text += f"- {c}\n"

    await msg.reply(text)

# =========================
# 👥 طلب إضافة لاعب
# =========================
@dp.message_handler(lambda m: m.text == "بحث لاعب")
async def add_player(msg: types.Message):
    user_id = msg.from_user.id

    club_name = None
    for c, data in clubs.items():
        if data["owner"] == user_id:
            club_name = c

    if not club_name:
        return await msg.reply("❌ انت مو رئيس نادي")

    await msg.reply("اكتب اسم اللاعب:")

    @dp.message_handler()
    async def process_player(m: types.Message):
        requests.append({
            "club": club_name,
            "player": m.text
        })

        await m.reply("📩 تم إرسال الطلب للقادة")

        dp.message_handlers.unregister(process_player)

# =========================
# 📥 الطلبات
# =========================
@dp.message_handler(lambda m: m.text == "الطلبات")
async def show_requests(msg: types.Message):
    if msg.from_user.id not in leaders and msg.from_user.id != OWNER_ID:
        return await msg.reply("❌ ما عندك صلاحية")

    if not requests:
        return await msg.reply("❌ لا توجد طلبات")

    for r in requests:
        await msg.reply(f"📌 نادي: {r['club']}\n👤 لاعب: {r['player']}")

# =========================
# ▶️ تشغيل البوت
# =========================
if __name__ == "__main__":
    if not API_TOKEN:
        print("❌ BOT_TOKEN غير موجود في Environment Variables")
    else:
        executor.start_polling(dp, skip_updates=True)
