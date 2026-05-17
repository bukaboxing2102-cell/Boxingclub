import asyncio
import logging
import aiosqlite
from datetime import date, datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.filters import Command

# ================= CONFIG =================
TOKEN = "8729643272:AAEKIM3A5s1bzRrc9Epf6swoLtmLEw2HN4E"
ADMIN_ID = 5192014741
CARD = "8600120414465784"
DB = "club.db"

bot = Bot(TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT DEFAULT '-',
            payment INTEGER DEFAULT 0,
            pay_type TEXT DEFAULT '-',
            attendance INTEGER DEFAULT 0,
            missed INTEGER DEFAULT 0,
            last_payment TEXT DEFAULT '2000-01-01'
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            status TEXT
        )
        """)

        await db.commit()


# ================= KEYBOARDS =================
def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Telefon raqam yuborish",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
def user_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Profil", callback_data="profile")],
        [InlineKeyboardButton(text="💰 To‘lov", callback_data="pay")],
        [InlineKeyboardButton(text="🥊 Murabbiy", callback_data="coach")]
    ])


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Sportchilar", callback_data="users")],
        [InlineKeyboardButton(text="💰 To‘laganlar", callback_data="paid")],
        [InlineKeyboardButton(text="❌ Qarzdorlar", callback_data="debt")],
        [InlineKeyboardButton(text="📊 Davomat", callback_data="attendance_menu")],
        [InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="broadcast")],
        [InlineKeyboardButton(text="🥊 Murabbiy info", callback_data="coach")]
    ])


# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id FROM users WHERE id=?",
            (msg.from_user.id,)
        )
        user = await cur.fetchone()

        if not user:
            await db.execute(
                "INSERT INTO users(id,name) VALUES(?,?)",
                (msg.from_user.id, msg.from_user.full_name)
            )
            await db.commit()

    kb = admin_kb() if msg.from_user.id == ADMIN_ID else user_kb()

   await msg.answer(
    "📱 Telefon raqamingizni yuboring",
    reply_markup=phone_kb()
)

await msg.answer(
    "🥊 UMIDOV BOKS CLUB CRM",
    reply_markup=kb
)


# ================= PHONE =================
@dp.message(F.contact)
async def save_phone(msg: Message):

    phone = msg.contact.phone_number

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET phone=? WHERE id=?",
            (phone, msg.from_user.id)
        )
        await db.commit()

    await msg.answer("✅ Telefon raqamingiz saqlandi")
    
    
# ================= USERS =================
@dp.callback_query(F.data == "users")
async def users(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id,name,phone FROM users"
        )
        rows = await cur.fetchall()

    text = "👥 SPORTCHILAR\n\n"

    for r in rows:
        text += f"🆔 {r[0]}\n👤 {r[1]}\n📞 {r[2]}\n\n"

    await call.message.edit_text(text)
    await call.answer()


# ================= PROFILE =================
@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT name,phone,payment,attendance,
        missed,last_payment,pay_type
        FROM users
        WHERE id=?
        """, (call.from_user.id,))
        u = await cur.fetchone()

    await call.message.edit_text(
        f"""
👤 {u[0]}
📞 {u[1]}
💰 {'✅' if u[2] else '❌'} ({u[6]})
📊 Davomat: {u[3]}
❌ Qoldirgan: {u[4]}
📅 Oxirgi to‘lov: {u[5]}
""",
        reply_markup=user_kb()
    )
    await call.answer()


# ================= PAYMENT =================
@dp.callback_query(F.data == "pay")
async def pay(call: CallbackQuery):

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta", callback_data="card")],
        [InlineKeyboardButton(text="💵 Naqd", callback_data="cash")]
    ])

    await call.message.edit_text(
        f"💳 Karta: {CARD}",
        reply_markup=kb
    )
    await call.answer()


# ================= CARD =================
@dp.callback_query(F.data == "card")
async def card(call: CallbackQuery):
    await call.message.answer("📸 Chek rasmini yuboring")
    await call.answer()


@dp.message(F.photo)
async def card_check(msg: Message):

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=f"card_{msg.from_user.id}"
        )
    ]])

    await bot.send_photo(
        ADMIN_ID,
        msg.photo[-1].file_id,
        caption="💳 To‘lov cheki",
        reply_markup=kb
    )

    await msg.answer("📩 Chek yuborildi")


@dp.callback_query(F.data.startswith("card_"))
async def card_ok(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        UPDATE users
        SET payment=1,
            pay_type='card',
            last_payment=?
        WHERE id=?
        """, (date.today().isoformat(), uid))
        await db.commit()

    await bot.send_message(uid, "✅ To‘lov tasdiqlandi")
    await call.answer("Tasdiqlandi")


# ================= CASH =================
@dp.callback_query(F.data == "cash")
async def cash(call: CallbackQuery):

     kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=f"cash_{call.from_user.id}"
        )
    ]])

    await bot.send_message(
        ADMIN_ID,
        f"💵 Naqd to‘lov: {call.from_user.id}",
        reply_markup=kb
    )

    await call.answer("Adminga yuborildi")


@dp.callback_query(F.data.startswith("cash_"))
async def cash_ok(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        UPDATE users
        SET payment=1,
            pay_type='cash',
            last_payment=?
        WHERE id=?
        """, (date.today().isoformat(), uid))
        await db.commit()

    await bot.send_message(uid, "✅ Naqd to‘lov tasdiqlandi")
    await call.answer()


# ================= PAID =================
@dp.callback_query(F.data == "paid")
async def paid(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT name,pay_type,last_payment
        FROM users
        WHERE payment=1
        """)
        rows = await cur.fetchall()

    if not rows:
        await call.message.edit_text("❌ To‘laganlar yo‘q")
        return

    text = "💰 TO‘LAGANLAR\n\n"

    for r in rows:
        text += f"{r[0]} | {r[1]} | {r[2]}\n"

    await call.message.edit_text(text)
    await call.answer()


# ================= DEBT =================
@dp.callback_query(F.data == "debt")
async def debt(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT name,last_payment
        FROM users
        WHERE payment=0
        """)
        rows = await cur.fetchall()

    text = "❌ QARZDORLAR\n\n"

    for r in rows:
        text += f"{r[0]} | {r[1]}\n"

    await call.message.edit_text(text)
    await call.answer()


# ================= ATTENDANCE =================
@dp.callback_query(F.data == "attendance_menu")
async def attendance_menu(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:

        cur = await db.execute("""
        SELECT name, attendance, missed
        FROM users
        """)

        rows = await cur.fetchall()

    text = "📊 DAVOMAT HISOBOTI\n\n"

    for r in rows:
        text += f"""
👤 {r[0]}
✅ Keldi: {r[1]}
❌ Qoldirdi: {r[2]}

"""

    await call.message.answer(text)

    async with aiosqlite.connect(DB) as db:

        cur = await db.execute(
            "SELECT id,name FROM users"
        )

        users = await cur.fetchall()

    for user in users:

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ Keldi",
                    callback_data=f"came_{user[0]}"
                ),

                InlineKeyboardButton(
                    text="❌ Kelmadi",
                    callback_data=f"missed_{user[0]}"
                )
            ]]
        )

        await call.message.answer(
            f"🥊 {user[1]}",
            reply_markup=kb
        )

    await call.answer()


# ================= CAME =================
@dp.callback_query(F.data.startswith("came_"))
async def came_user(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    today = str(date.today())

    async with aiosqlite.connect(DB) as db:

        cur = await db.execute("""
        SELECT * FROM attendance
        WHERE user_id=? AND date=?
        """, (uid, today))

        check = await cur.fetchone()

        if check:
            await call.answer(
                "Bugun davomat qilingan ✅"
            )
            return

        await db.execute("""
        INSERT INTO attendance(user_id,date,status)
        VALUES(?,?,?)
        """, (uid, today, "came"))

        await db.execute("""
        UPDATE users
        SET attendance = attendance + 1
        WHERE id=?
        """, (uid,))

        await db.commit()

    await call.answer("Keldi belgilandi ✅")


# ================= MISSED =================
@dp.callback_query(F.data.startswith("missed_"))
async def missed_user(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    today = str(date.today())

    async with aiosqlite.connect(DB) as db:

        cur = await db.execute("""
        SELECT * FROM attendance
        WHERE user_id=? AND date=?
        """, (uid, today))

        check = await cur.fetchone()

        if check:
            await call.answer(
                "Bugun davomat qilingan ✅"
            )
            return

        await db.execute("""
        INSERT INTO attendance(user_id,date,status)
        VALUES(?,?,?)
        """, (uid, today, "missed"))

        await db.execute("""
        UPDATE users
        SET missed = missed + 1
        WHERE id=?
        """, (uid,))

        await db.commit()

    await call.answer("Kelmadi belgilandi ❌")

# ================= COACH =================
@dp.callback_query(F.data == "coach")
async def coach(call: CallbackQuery):
    await call.message.edit_text("""
🥊 MURABBIY

👤 Umidov Rajabboy Xushnud o‘g‘li
📞 +99899 741 33 61

💪 Professional Boxing Coach
""")
    await call.answer()

# ================= BROADCAST =================
broadcast_mode = False


@dp.callback_query(F.data == "broadcast")
async def broadcast(call: CallbackQuery):
    global broadcast_mode

    if call.from_user.id != ADMIN_ID:
        return

    broadcast_mode = True
    await call.message.answer("📣 Xabar matnini yuboring:")
    await call.answer()


@dp.message()
async def all_messages(msg: Message):
    global broadcast_mode

    if msg.from_user.id == ADMIN_ID and broadcast_mode:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("SELECT id FROM users")
            users = await cur.fetchall()

        sent = 0

        for u in users:
            try:
                await bot.send_message(u[0], msg.text)
                sent += 1
            except:
                pass

        broadcast_mode = False
        await msg.answer(f"✅ {sent} ta sportchiga yuborildi")
# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())