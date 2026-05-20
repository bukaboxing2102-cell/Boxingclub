import asyncio
import logging
import aiosqlite
import asyncpg
import os
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import Command

# ================= CONFIG =================
TOKEN = "8729643272:AAEJIOX8RM-IFIek89EHQsUHwtW8DvhJX1M"  # <-- tokeningizni yozing
ADMIN_ID = 5192014741

CARD = "8600120414465784"
BANK_MFO = "01125"
BANK_ACCOUNT = "20208000707363910001"
            
DB = os.getenv("${{Postgres.DATABASE_URL}}")

bot = Bot(TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

broadcast_mode = False


# ================= DATABASE =================
async def init_db():
    conn = await asyncpg.connect (DB)
    
    await conn.execute("""
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

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            status TEXT
        )
        """)

    await conn.close()


# ================= KEYBOARDS =================
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
        [InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="broadcast")]
    ])


def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="📱 Raqam yuborish",
                request_contact=True
            )]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):

    conn = await asyncpg.connect(DB)

    user = await conn.fetchrow(
        "SELECT id FROM users WHERE id=$1",
        msg.from_user.id
    )

    if not user:
        await conn.execute(
            "INSERT INTO users (id, name) VALUES ($1, $2)",
            msg.from_user.id,
            msg.from_user.full_name
        )

    await conn.close()

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
async def phone(msg: Message):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET phone=? WHERE id=?",
            (msg.contact.phone_number, msg.from_user.id)
        )
        await db.commit()

    await msg.answer("✅ Saqlandi")


# ================= PROFILE =================
@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT id,name,phone,payment,pay_type,
               attendance,missed,last_payment
        FROM users
        WHERE id=?
        """, (call.from_user.id,))
        u = await cur.fetchone()

    status = "✅ To‘lagan" if u[3] else "❌ Qarzdor"

    await call.message.edit_text(f"""
👤 PROFIL

🆔 ID: {u[0]}
👤 Ism: {u[1]}
📞 Tel: {u[2]}

💰 Status: {status}
💳 To‘lov turi: {u[4]}
📅 Oxirgi: {u[7]}

📊 Keldi: {u[5]}
❌ Kelmadi: {u[6]}
""")

    await call.answer()


# ================= COACH =================
@dp.callback_query(F.data == "coach")
async def coach(call: CallbackQuery):
    await call.message.edit_text("""
🥊 MURABBIY INFO

👤 Umidov Rajabboy Xushnud o‘g‘li
🏆 Professional Boxing Coach
📞 +99899 741 33 61

KUCH+INTIZOM=GALABA 
""")
    await call.answer()


# ================= PAYMENT =================
@dp.callback_query(F.data == "pay")
async def pay(call: CallbackQuery):

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Naqd", callback_data="cash")]
    ])

    await call.message.edit_text(f"""
💰 TO‘LOV

💳 KARTA:
{CARD}

🏦 BANK:
MFO: {BANK_MFO}
Hisob: {BANK_ACCOUNT}

📸 Karta yoki bank orqali to‘lasangiz chek yuboring

yoki

💵 Naqd to‘lov uchun tugmani bosing
""", reply_markup=kb)

    await call.answer()


# ================= PHOTO PAYMENT =================
@dp.message(F.photo)
async def photo(msg: Message):

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ TASDIQLASH",
            callback_data=f"pay_{msg.from_user.id}"
        )
    ]])

    await bot.send_photo(
        ADMIN_ID,
        msg.photo[-1].file_id,
        caption=f"💳 To‘lov cheki\n🆔 User ID: {msg.from_user.id}",
        reply_markup=kb
    )

    await msg.answer("📩 Chek adminga yuborildi")


@dp.callback_query(F.data.startswith("pay_"))
async def approve(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        UPDATE users
        SET payment=1,
            pay_type='card/bank',
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
        f"💵 Naqd to‘lov so‘rovi\n\n🆔 User ID: {call.from_user.id}",
        reply_markup=kb
    )

    await call.answer("✅ So‘rov adminga yuborildi")


@dp.callback_query(F.data.startswith("cash_"))
async def cash_approve(call: CallbackQuery):

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
    await call.answer("Tasdiqlandi")

    
    # ================= MANUAL PAID / UNPAID =================
@dp.message(Command("paid"))
async def manual_paid(msg: Message):

    if msg.from_user.id != ADMIN_ID:
        return await msg.answer("❌ Siz admin emassiz")

    try:
        args = msg.text.split()

        if len(args) != 2:
            return await msg.answer("❌ Misol: /paid 123456")

        uid = int(args[1])

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT name FROM users WHERE id=?",
                (uid,)
            )
            user = await cur.fetchone()

            if not user:
                return await msg.answer("❌ ID topilmadi")

            await db.execute("""
                UPDATE users
                SET payment=1,
                    pay_type='admin',
                    last_payment=?
                WHERE id=?
            """, (date.today().isoformat(), uid))

            await db.commit()

        try:
            await bot.send_message(
                uid,
                "✅ To‘lovingiz admin tomonidan tasdiqlandi"
            )
        except:
            pass

        await msg.answer(
            f"✅ {user[0]} to‘lovi tasdiqlandi"
        )

    except:
        await msg.answer("❌ ID noto‘g‘ri")


@dp.message(Command("unpaid"))
async def manual_unpaid(msg: Message):

    if msg.from_user.id != ADMIN_ID:
        return await msg.answer("❌ Siz admin emassiz")

    try:
        args = msg.text.split()

        if len(args) != 2:
            return await msg.answer("❌ Misol: /unpaid 123456")

        uid = int(args[1])

        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT name FROM users WHERE id=?",
                (uid,)
            )
            user = await cur.fetchone()

            if not user:
                return await msg.answer("❌ ID topilmadi")

            await db.execute("""
                UPDATE users
                SET payment=0,
                    pay_type='-'
                WHERE id=?
            """, (uid,))

            await db.commit()

        try:
            await bot.send_message(
                uid,
                "❌ To‘lovingiz admin tomonidan bekor qilindi"
            )
        except:
            pass

        await msg.answer(
            f"✅ {user[0]} to‘lovi bekor qilindi"
        )

    except:
        await msg.answer("❌ ID noto‘g‘ri")


# ================= PAID =================
@dp.callback_query(F.data == "paid")
async def paid(call: CallbackQuery):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT id,name,pay_type,last_payment
        FROM users
        WHERE payment=1
        """)
        rows = await cur.fetchall()

    if not rows:
        await call.message.edit_text("❌ To‘laganlar yo‘q")
        await call.answer()
        return

    text = "💰 TO‘LAGANLAR\n\n"
    for r in rows:
        text += f"🆔 {r[0]} | 👤 {r[1]} | {r[2]} | 📅 {r[3]}\n"

    await call.message.edit_text(text)
    await call.answer()


# ================= DEBT =================
@dp.callback_query(F.data == "debt")
async def debt(call: CallbackQuery):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT id,name
        FROM users
        WHERE payment=0
        """)
        rows = await cur.fetchall()

    if not rows:
        await call.message.edit_text("✅ Qarzdorlar yo‘q")
        await call.answer()
        return

    text = "❌ QARZDORLAR\n\n"
    for r in rows:
        text += f"🆔 {r[0]} | 👤 {r[1]}\n"

    await call.message.edit_text(text)
    await call.answer()


# ================= ATTENDANCE =================
@dp.callback_query(F.data == "attendance_menu")
async def attendance_menu(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
            SELECT id,name,attendance,missed
            FROM users
        """)
        rows = await cur.fetchall()

    text = "📊 DAVOMAT HISOBOTI\n\n"
    for r in rows:
        text += f"👤 {r[1]}\n✅ {r[2]} | ❌ {r[3]}\n\n"

    await call.message.answer(text)

    for r in rows:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ Keldi",
                    callback_data=f"came_{r[0]}"
                ),
                InlineKeyboardButton(
                    text="❌ Kelmadi",
                    callback_data=f"missed_{r[0]}"
                )
            ]]
        )
        await call.message.answer(
            f"🥊 {r[1]}",
            reply_markup=kb
        )

    await call.answer()


@dp.callback_query(F.data.startswith("came_"))
async def came(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    today = str(date.today())

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT * FROM attendance WHERE user_id=? AND date=?",
            (uid, today)
        )

        if await cur.fetchone():
            await call.answer("Allaqachon belgilangan")
            return

        await db.execute(
            "INSERT INTO attendance(user_id,date,status) VALUES(?,?,?)",
            (uid, today, "came")
        )

        await db.execute(
            "UPDATE users SET attendance=attendance+1 WHERE id=?",
            (uid,)
        )

        await db.commit()

    await bot.send_message(uid, "✅ Keldingiz belgilandi")
    await call.answer()


@dp.callback_query(F.data.startswith("missed_"))
async def missed(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    today = str(date.today())

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT * FROM attendance WHERE user_id=? AND date=?",
            (uid, today)
        )

        if await cur.fetchone():
            await call.answer("Allaqachon belgilangan")
            return

        await db.execute(
            "INSERT INTO attendance(user_id,date,status) VALUES(?,?,?)",
            (uid, today, "missed")
        )

        await db.execute(
            "UPDATE users SET missed=missed+1 WHERE id=?",
            (uid,)
        )

        await db.commit()

    await bot.send_message(uid, "❌ Kelmadingiz belgilandi")
    await call.answer()


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
        text += f"🆔 {r[0]} | {r[1]} | {r[2]}\n"

    await call.message.edit_text(text)
    await call.answer()


# ================= BROADCAST =================
@dp.callback_query(F.data == "broadcast")
async def bc(call: CallbackQuery):
    global broadcast_mode

    if call.from_user.id != ADMIN_ID:
        return

    broadcast_mode = True
    await call.message.answer("📣 Xabar yozing")
    await call.answer()


@dp.message()
async def broadcast_handler(msg: Message):
    global broadcast_mode

    if msg.from_user.id != ADMIN_ID or not broadcast_mode:
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id FROM users")
        users = await cur.fetchall()

    for u in users:
        try:
            await bot.send_message(u[0], f"📣 {msg.text}")
        except:
            pass

    broadcast_mode = False
    await msg.answer("✅ Yuborildi")


# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())