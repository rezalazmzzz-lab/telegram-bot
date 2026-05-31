import telebot
from telebot import types
import sqlite3
import os
from datetime import datetime

# =========================
# CONFIG
# =========================

import os
TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 653170487

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS captains(
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS players(
    user_id INTEGER PRIMARY KEY,
    player_name TEXT,
    team_name TEXT,
    facebook_link TEXT,
    serial_number TEXT UNIQUE,
    screenshot_file_id TEXT,
    approved_by INTEGER,
    approved_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pending_requests(
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    player_name TEXT,
    team_name TEXT,
    facebook_link TEXT,
    serial_number TEXT,
    screenshot_file_id TEXT,
    status TEXT DEFAULT 'pending'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

conn.commit()

# =========================
# DEFAULT SETTINGS
# =========================

cursor.execute(
    "INSERT OR IGNORE INTO settings(key,value) VALUES('transfers','closed')"
)

conn.commit()

# =========================
# HELPERS
# =========================

def is_owner(user_id):
    return user_id == OWNER_ID


def is_captain(user_id):

    if user_id == OWNER_ID:
        return True

    cursor.execute(
        "SELECT * FROM captains WHERE user_id=?",
        (user_id,)
    )

    return cursor.fetchone() is not None


def transfers_open():

    cursor.execute(
        "SELECT value FROM settings WHERE key='transfers'"
    )

    row = cursor.fetchone()

    if row:
        return row[0] == "open"

    return False


def player_exists(user_id):

    cursor.execute(
        "SELECT * FROM players WHERE user_id=?",
        (user_id,)
    )

    return cursor.fetchone() is not None


def main_keyboard(user_id):

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row("📝 التسجيل")
    kb.row("👥 عرض التيمات")
    kb.row("🔍 البحث عن لاعب")

    if is_captain(user_id):
        kb.row("📥 الطلبات")
        kb.row("🔄 الانتقالات")
        kb.row("👑 القادة")

    return kb

# =========================
# START
# =========================

@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "اهلاً بك في نظام دوري eFootball",
        reply_markup=main_keyboard(message.from_user.id)
    )

# =========================
# CAPTAINS MENU
# =========================

@bot.message_handler(func=lambda m: m.text == "👑 القادة")
def captains_menu(message):

    if not is_owner(message.from_user.id):
        return

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row("➕ إضافة قائد")
    kb.row("➖ حذف قائد")
    kb.row("📋 عرض القادة")
    kb.row("🔙 رجوع")

    bot.send_message(
        message.chat.id,
        "قسم القادة",
        reply_markup=kb
    )

# =========================
# BACK
# =========================

@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def back_menu(message):

    bot.send_message(
        message.chat.id,
        "تم الرجوع للقائمة الرئيسية",
        reply_markup=main_keyboard(message.from_user.id)
    )

# =========================
# ADD CAPTAIN
# =========================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة قائد")
def add_captain(message):

    if not is_owner(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "ارسل ID القائد"
    )

    bot.register_next_step_handler(
        msg,
        save_captain
    )

def save_captain(message):

    try:

        captain_id = int(message.text)

        cursor.execute(
            "INSERT OR IGNORE INTO captains(user_id) VALUES(?)",
            (captain_id,)
        )

        conn.commit()

        bot.send_message(
            message.chat.id,
            "تمت إضافة القائد بنجاح"
        )

    except:

        bot.send_message(
            message.chat.id,
            "ID غير صالح"
        )

# =========================
# REMOVE CAPTAIN
# =========================

@bot.message_handler(func=lambda m: m.text == "➖ حذف قائد")
def remove_captain(message):

    if not is_owner(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "ارسل ID القائد المراد حذفه"
    )

    bot.register_next_step_handler(
        msg,
        delete_captain
    )

def delete_captain(message):

    try:

        captain_id = int(message.text)

        cursor.execute(
            "DELETE FROM captains WHERE user_id=?",
            (captain_id,)
        )

        conn.commit()

        bot.send_message(
            message.chat.id,
            "تم حذف القائد"
        )

    except:

        bot.send_message(
            message.chat.id,
            "حدث خطأ"
        )

# =========================
# SHOW CAPTAINS
# =========================

@bot.message_handler(func=lambda m: m.text == "📋 عرض القادة")
def show_captains(message):

    if not is_owner(message.from_user.id):
        return

    cursor.execute(
        "SELECT user_id FROM captains"
    )

    rows = cursor.fetchall()

    text = "القادة:\n\n"

    text += f"المالك: {OWNER_ID}\n\n"

    for row in rows:
        text += f"{row[0]}\n"

    bot.send_message(
        message.chat.id,
        text
    )
    # =========================
# REGISTER SYSTEM
# =========================

register_data = {}

@bot.message_handler(func=lambda m: m.text == "📝 التسجيل")
def register_player(message):

    user_id = message.from_user.id

    if player_exists(user_id):

        if not transfers_open():

            bot.send_message(
                message.chat.id,
                "الانتقالات مغلقة حالياً ولا يمكن تعديل المعلومات."
            )

            return

    msg = bot.send_message(
        message.chat.id,
        "ارسل اسم اللاعب:"
    )

    register_data[user_id] = {}

    bot.register_next_step_handler(
        msg,
        get_player_name
    )


def get_player_name(message):

    user_id = message.from_user.id

    register_data[user_id]["player_name"] = message.text

    msg = bot.send_message(
        message.chat.id,
        "ارسل اسم التيم:"
    )

    bot.register_next_step_handler(
        msg,
        get_team_name
    )


def get_team_name(message):

    user_id = message.from_user.id

    register_data[user_id]["team_name"] = message.text

    msg = bot.send_message(
        message.chat.id,
        "ارسل رابط الفيسبوك:"
    )

    bot.register_next_step_handler(
        msg,
        get_facebook
    )


def get_facebook(message):

    user_id = message.from_user.id

    link = message.text.strip()

    if "facebook.com" not in link and "fb.com" not in link:

        msg = bot.send_message(
            message.chat.id,
            "رابط غير صالح، ارسل رابط فيسبوك صحيح."
        )

        bot.register_next_step_handler(
            msg,
            get_facebook
        )

        return

    register_data[user_id]["facebook_link"] = link

    msg = bot.send_message(
        message.chat.id,
        "ارسل الرقم التسلسلي:"
    )

    bot.register_next_step_handler(
        msg,
        get_serial
    )


def get_serial(message):

    user_id = message.from_user.id

    serial = message.text.strip()

    cursor.execute(
        "SELECT * FROM players WHERE serial_number=?",
        (serial,)
    )

    if cursor.fetchone():

        bot.send_message(
            message.chat.id,
            "هذا الرقم التسلسلي مستخدم مسبقاً."
        )

        return

    register_data[user_id]["serial_number"] = serial

    msg = bot.send_message(
        message.chat.id,
        "ارسل صورة سكرين الرقم التسلسلي:"
    )

    bot.register_next_step_handler(
        msg,
        get_screenshot
    )


def get_screenshot(message):

    user_id = message.from_user.id

    if not message.photo:

        msg = bot.send_message(
            message.chat.id,
            "يرجى ارسال صورة."
        )

        bot.register_next_step_handler(
            msg,
            get_screenshot
        )

        return

    file_id = message.photo[-1].file_id

    register_data[user_id]["screenshot_file_id"] = file_id

    data = register_data[user_id]

    cursor.execute("""
        INSERT INTO pending_requests(
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id
        )
        VALUES(?,?,?,?,?,?)
    """, (
        user_id,
        data["player_name"],
        data["team_name"],
        data["facebook_link"],
        data["serial_number"],
        data["screenshot_file_id"]
    ))

    conn.commit()

    request_id = cursor.lastrowid

    bot.send_message(
        message.chat.id,
        "تم ارسال طلبك بنجاح وهو بانتظار موافقة القادة."
    )

    send_request_to_captains(request_id)

    del register_data[user_id]


# =========================
# SEND REQUEST TO CAPTAINS
# =========================

def send_request_to_captains(request_id):

    cursor.execute("""
        SELECT *
        FROM pending_requests
        WHERE request_id=?
    """, (request_id,))

    req = cursor.fetchone()

    if not req:
        return

    (
        request_id,
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        status
    ) = req

    text = f"""
📥 طلب تسجيل جديد

🆔 الطلب: {request_id}

👤 اللاعب:
{player_name}

🏆 التيم:
{team_name}

🔗 الفيسبوك:
{facebook_link}

📱 الرقم التسلسلي:
{serial_number}
"""

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "✅ موافقة",
            callback_data=f"approve_{request_id}"
        ),
        types.InlineKeyboardButton(
            "❌ رفض",
            callback_data=f"reject_{request_id}"
        )
    )

    recipients = [OWNER_ID]

    cursor.execute(
        "SELECT user_id FROM captains"
    )

    rows = cursor.fetchall()

    for row in rows:

        recipients.append(row[0])

    recipients = list(set(recipients))

    for captain_id in recipients:

        try:

            bot.send_photo(
                captain_id,
                screenshot_file_id,
                caption=text,
                reply_markup=kb
            )

        except:
            pass


# =========================
# REQUESTS MENU
# =========================

@bot.message_handler(func=lambda m: m.text == "📥 الطلبات")
def requests_menu(message):

    if not is_captain(message.from_user.id):
        return

    cursor.execute("""
        SELECT request_id,
        player_name,
        team_name
        FROM pending_requests
        WHERE status='pending'
        ORDER BY request_id DESC
    """)

    rows = cursor.fetchall()

    if not rows:

        bot.send_message(
            message.chat.id,
            "لا توجد طلبات حالياً."
        )

        return

    kb = types.InlineKeyboardMarkup()

    for row in rows:

        request_id = row[0]
        player_name = row[1]
        team_name = row[2]

        kb.add(
            types.InlineKeyboardButton(
                f"{player_name} | {team_name}",
                callback_data=f"showreq_{request_id}"
            )
        )

    bot.send_message(
        message.chat.id,
        "الطلبات المعلقة:",
        reply_markup=kb
    )
    # =========================
# SHOW REQUEST DETAILS
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("showreq_"))
def show_request(call):

    if not is_captain(call.from_user.id):
        return

    request_id = int(call.data.split("_")[1])

    cursor.execute("""
        SELECT *
        FROM pending_requests
        WHERE request_id=?
    """, (request_id,))

    req = cursor.fetchone()

    if not req:
        bot.answer_callback_query(
            call.id,
            "الطلب غير موجود"
        )
        return

    (
        request_id,
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        status
    ) = req

    text = f"""
📥 طلب تسجيل

🆔 {request_id}

👤 {player_name}

🏆 {team_name}

🔗 {facebook_link}

📱 {serial_number}
"""

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "✅ موافقة",
            callback_data=f"approve_{request_id}"
        ),
        types.InlineKeyboardButton(
            "❌ رفض",
            callback_data=f"reject_{request_id}"
        )
    )

    bot.send_photo(
        call.message.chat.id,
        screenshot_file_id,
        caption=text,
        reply_markup=kb
    )

# =========================
# APPROVE REQUEST
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_request(call):

    if not is_captain(call.from_user.id):
        return

    request_id = int(call.data.split("_")[1])

    cursor.execute("""
        SELECT *
        FROM pending_requests
        WHERE request_id=?
    """, (request_id,))

    req = cursor.fetchone()

    if not req:
        bot.answer_callback_query(
            call.id,
            "الطلب غير موجود"
        )
        return

    if req[7] != "pending":

        bot.answer_callback_query(
            call.id,
            "تمت معالجة الطلب مسبقاً"
        )
        return

    (
        request_id,
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        status
    ) = req

    cursor.execute("""
        DELETE FROM players
        WHERE user_id=?
    """, (user_id,))

    cursor.execute("""
        INSERT INTO players(
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        approved_by,
        approved_date
        )
        VALUES(?,?,?,?,?,?,?,?)
    """, (
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        call.from_user.id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    cursor.execute("""
        UPDATE pending_requests
        SET status='approved'
        WHERE request_id=?
    """, (request_id,))

    conn.commit()

    try:
        bot.send_message(
            user_id,
            "✅ تمت الموافقة على تسجيلك بنجاح."
        )
    except:
        pass

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

    bot.answer_callback_query(
        call.id,
        "تمت الموافقة"
    )

# =========================
# REJECT REQUEST
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def reject_request(call):

    if not is_captain(call.from_user.id):
        return

    request_id = int(call.data.split("_")[1])

    cursor.execute("""
        SELECT *
        FROM pending_requests
        WHERE request_id=?
    """, (request_id,))

    req = cursor.fetchone()

    if not req:
        return

    if req[7] != "pending":

        bot.answer_callback_query(
            call.id,
            "تمت معالجة الطلب مسبقاً"
        )
        return

    user_id = req[1]

    cursor.execute("""
        UPDATE pending_requests
        SET status='rejected'
        WHERE request_id=?
    """, (request_id,))

    conn.commit()

    try:
        bot.send_message(
            user_id,
            "❌ نعتذر عن الموافقة، يرجى التأكد من المعلومات وإعادة المحاولة."
        )
    except:
        pass

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

    bot.answer_callback_query(
        call.id,
        "تم الرفض"
    )

# =========================
# SHOW TEAMS
# =========================

@bot.message_handler(func=lambda m: m.text == "👥 عرض التيمات")
def show_teams(message):

    cursor.execute("""
        SELECT team_name, COUNT(*)
        FROM players
        GROUP BY team_name
        ORDER BY team_name
    """)

    rows = cursor.fetchall()

    if not rows:

        bot.send_message(
            message.chat.id,
            "لا توجد تيمات حالياً."
        )
        return

    kb = types.InlineKeyboardMarkup()

    for team_name, count_players in rows:

        kb.add(
            types.InlineKeyboardButton(
                f"{team_name} ({count_players})",
                callback_data=f"team_{team_name}"
            )
        )

    bot.send_message(
        message.chat.id,
        "اختر التيم:",
        reply_markup=kb
    )

# =========================
# PLAYERS INSIDE TEAM
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("team_"))
def team_players(call):

    team_name = call.data[5:]

    cursor.execute("""
        SELECT user_id, player_name
        FROM players
        WHERE team_name=?
        ORDER BY player_name
    """, (team_name,))

    rows = cursor.fetchall()

    kb = types.InlineKeyboardMarkup()

    for user_id, player_name in rows:

        kb.add(
            types.InlineKeyboardButton(
                player_name,
                callback_data=f"player_{user_id}"
            )
        )

    bot.send_message(
        call.message.chat.id,
        f"لاعبو {team_name}",
        reply_markup=kb
    )

# =========================
# PLAYER INFO
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("player_"))
def player_info(call):

    user_id = int(call.data.split("_")[1])

    cursor.execute("""
        SELECT
        player_name,
        team_name,
        facebook_link,
        serial_number
        FROM players
        WHERE user_id=?
    """, (user_id,))

    row = cursor.fetchone()

    if not row:
        return

    text = f"""
👤 الاسم:
{row[0]}

🏆 التيم:
{row[1]}

📱 الرقم التسلسلي:
{row[3]}

🔗 الفيسبوك:
{row[2]}
"""

    bot.send_message(
        call.message.chat.id,
        text
    )

# =========================
# SEARCH PLAYER
# =========================

@bot.message_handler(func=lambda m: m.text == "🔍 البحث عن لاعب")
def search_player(message):

    msg = bot.send_message(
        message.chat.id,
        "ارسل اسم اللاعب:"
    )

    bot.register_next_step_handler(
        msg,
        do_search
    )

def do_search(message):

    keyword = message.text.strip()

    cursor.execute("""
        SELECT
        user_id,
        player_name,
        team_name
        FROM players
        WHERE player_name LIKE ?
        ORDER BY player_name
    """, (f"%{keyword}%",))

    rows = cursor.fetchall()

    if not rows:

        bot.send_message(
            message.chat.id,
            "لا توجد نتائج."
        )
        return

    kb = types.InlineKeyboardMarkup()

    for user_id, player_name, team_name in rows:

        kb.add(
            types.InlineKeyboardButton(
                f"{player_name} | {team_name}",
                callback_data=f"player_{user_id}"
            )
        )

    bot.send_message(
        message.chat.id,
        "نتائج البحث:",
        reply_markup=kb
    )
    # =========================
# TRANSFERS MENU
# =========================

@bot.message_handler(func=lambda m: m.text == "🔄 الانتقالات")
def transfers_menu(message):

    if not is_captain(message.from_user.id):
        return

    cursor.execute(
        "SELECT value FROM settings WHERE key='transfers'"
    )

    status = cursor.fetchone()[0]

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    kb.row("🟢 فتح الانتقالات")
    kb.row("🔴 غلق الانتقالات")
    kb.row("🔙 رجوع")

    bot.send_message(
        message.chat.id,
        f"حالة الانتقالات الحالية: {status}",
        reply_markup=kb
    )

# =========================
# OPEN TRANSFERS
# =========================

@bot.message_handler(func=lambda m: m.text == "🟢 فتح الانتقالات")
def open_transfers(message):

    if not is_captain(message.from_user.id):
        return

    cursor.execute("""
        UPDATE settings
        SET value='open'
        WHERE key='transfers'
    """)

    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ تم فتح الانتقالات."
    )

# =========================
# CLOSE TRANSFERS
# =========================

@bot.message_handler(func=lambda m: m.text == "🔴 غلق الانتقالات")
def close_transfers(message):

    if not is_captain(message.from_user.id):
        return

    cursor.execute("""
        UPDATE settings
        SET value='closed'
        WHERE key='transfers'
    """)

    conn.commit()

    bot.send_message(
        message.chat.id,
        "🔒 تم غلق الانتقالات."
    )

# =========================
# UPDATE PLAYER AFTER TRANSFER
# =========================

def update_player_data(
    user_id,
    player_name,
    team_name,
    facebook_link,
    serial_number,
    screenshot_file_id,
    approved_by
):

    cursor.execute("""
        DELETE FROM players
        WHERE user_id=?
    """, (user_id,))

    cursor.execute("""
        INSERT INTO players(
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        approved_by,
        approved_date
        )
        VALUES(?,?,?,?,?,?,?,?)
    """, (
        user_id,
        player_name,
        team_name,
        facebook_link,
        serial_number,
        screenshot_file_id,
        approved_by,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()

# =========================
# CLEAN OLD REQUESTS
# =========================

def cleanup_old_requests():

    cursor.execute("""
        DELETE FROM pending_requests
        WHERE status='approved'
    """)

    cursor.execute("""
        DELETE FROM pending_requests
        WHERE status='rejected'
    """)

    conn.commit()

# =========================
# BOT START
# =========================

print("Bot Started...")

bot.infinity_polling(
    timeout=60,
    long_polling_timeout=60
)
