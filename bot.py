# ======================================
# FIX ADD LEADER
# ======================================

@dp.message(AddLeader.user_id)
async def save_leader(message: Message, state: FSMContext):

    if not message.text.isdigit():

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

    user_id = int(message.text)

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "INSERT OR IGNORE INTO leaders (user_id) VALUES (?)",
            (user_id,)
        )

        await db.commit()

    await message.answer(
        "✅ تم اضافة القائد"
    )

    await state.clear()

# ======================================
# FIX REMOVE LEADER
# ======================================

@dp.message(RemoveLeader.user_id)
async def delete_leader(message: Message, state: FSMContext):

    if not message.text.isdigit():

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

    user_id = int(message.text)

    async with aiosqlite.connect("union.db") as db:

        await db.execute(
            "DELETE FROM leaders WHERE user_id=?",
            (user_id,)
        )

        await db.commit()

    await message.answer(
        "✅ تم حذف القائد"
    )

    await state.clear()

# ======================================
# FIX SEARCH
# ======================================

@dp.message(SearchPlayer.text)
async def search_player(message: Message, state: FSMContext):

    if not message.text:

        return

    text = message.text

    async with aiosqlite.connect("union.db") as db:

        async with db.execute("""
        SELECT team, player_name, facebook, phone, status
        FROM players
        WHERE player_name LIKE ?
        OR facebook LIKE ?
        """, (

            f"%{text}%",
            f"%{text}%"

        )) as cursor:

            rows = await cursor.fetchall()

    if not rows:

        await message.answer(
            "❌ لم يتم العثور على اللاعب"
        )

        return

    result = ""

    for row in rows:

        result += f"🏆 التيم : {row[0]}\n"
        result += f"👤 اللاعب : {row[1]}\n"
        result += f"🌐 الفيس : {row[2]}\n"
        result += f"📱 الرقم : {row[3]}\n"
        result += f"📌 الحالة : {row[4]}\n"
        result += "━━━━━━━━━━\n"

    await message.answer(result)

    await state.clear()

# ======================================
# FIX SCREENSHOT
# ======================================

@dp.message(Register.screenshot, F.photo)
async def reg_screen(message: Message, state: FSMContext):

    data = await state.get_data()

    photo = message.photo[-1].file_id

    async with aiosqlite.connect("union.db") as db:

        await db.execute("""
        INSERT INTO players
        (
            user_id,
            team,
            player_name,
            facebook,
            phone,
            screenshot,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (

            message.from_user.id,
            data['team'],
            data['player'],
            data['facebook'],
            data['phone'],
            photo,
            "pending"

        ))

        await db.commit()

    leaders = []

    async with aiosqlite.connect("union.db") as db:

        async with db.execute(
            "SELECT user_id FROM leaders"
        ) as cursor:

            rows = await cursor.fetchall()

            leaders = [x[0] for x in rows]

    text = f"""
📥 طلب تسجيل جديد

🏆 التيم : {data['team']}
👤 اللاعب : {data['player']}
🌐 الفيس : {data['facebook']}
📱 الرقم : {data['phone']}
🆔 الايدي : {message.from_user.id}
"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [

                InlineKeyboardButton(
                    text="✅ قبول",
                    callback_data=f"accept_{message.from_user.id}"
                ),

                InlineKeyboardButton(
                    text="❌ رفض",
                    callback_data=f"reject_{message.from_user.id}"
                )

            ]

        ]
    )

    for leader in leaders:

        try:

            await bot.send_photo(
                leader,
                photo,
                caption=text,
                reply_markup=keyboard
            )

        except:
            pass

    await message.answer(
        "✅ سيتم مراجعة طلبك من قبل القادة وبعد الموافقة سيتم اضافتك الى التيم"
    )

    await state.clear()

# ======================================
# NO PHOTO
# ======================================

@dp.message(Register.screenshot)
async def no_photo(message: Message):

    await message.answer(
        "❌ يرجى ارسال صورة فقط"
    )

# ======================================
# UNKNOWN COMMAND
# ======================================

@dp.message()
async def unknown(message: Message):

    await message.answer(
        "❌ الامر غير معروف"
    )
