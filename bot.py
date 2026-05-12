# ======================================
# ADMIN MENU
# ======================================

@dp.message(F.text == "🛠 الإدارة")
async def admin_panel(message: Message):

    if not await is_leader(message.from_user.id):

        return await message.answer(
            "❌ هذا القسم للقادة فقط"
        )

    buttons = [

        [KeyboardButton(text="📥 الطلبات")],

        [KeyboardButton(text="🔓 فتح الانتقالات")],

        [KeyboardButton(text="🔒 غلق الانتقالات")]

    ]

    if message.from_user.id == OWNER_ID:

        buttons.append([
            KeyboardButton(text="➕ اضافة قائد")
        ])

        buttons.append([
            KeyboardButton(text="➖ حذف قائد")
        ])

    buttons.append([
        KeyboardButton(text="🔙 رجوع")
    ])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await message.answer(
        "🛠 لوحة الإدارة",
        reply_markup=keyboard
    )

# ======================================
# BACK
# ======================================

@dp.message(F.text == "🔙 رجوع")
async def back_home(message: Message):

    await message.answer(
        "🏠 القائمة الرئيسية",
        reply_markup=await main_menu(message.from_user.id)
    )

# ======================================
# ADD LEADER
# ======================================

@dp.message(F.text == "➕ اضافة قائد")
async def add_leader(message: Message, state: FSMContext):

    if message.from_user.id != OWNER_ID:

        return await message.answer(
            "❌ هذا الزر للمالك فقط"
        )

    await message.answer(
        "🆔 ارسل ايدي الشخص"
    )

    await state.set_state(AddLeader.user_id)

@dp.message(AddLeader.user_id)
async def save_leader(message: Message, state: FSMContext):

    try:

        user_id = int(message.text)

    except:

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

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
# REMOVE LEADER
# ======================================

@dp.message(F.text == "➖ حذف قائد")
async def remove_leader(message: Message, state: FSMContext):

    if message.from_user.id != OWNER_ID:

        return await message.answer(
            "❌ هذا الزر للمالك فقط"
        )

    await message.answer(
        "🆔 ارسل ايدي القائد"
    )

    await state.set_state(RemoveLeader.user_id)

@dp.message(RemoveLeader.user_id)
async def delete_leader(message: Message, state: FSMContext):

    try:

        user_id = int(message.text)

    except:

        return await message.answer(
            "❌ ارسل ايدي صحيح"
        )

    if user_id == OWNER_ID:

        return await message.answer(
            "❌ لا يمكن حذف المالك"
        )

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
