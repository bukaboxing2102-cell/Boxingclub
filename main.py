import asyncio
import logging
import aiosqlite
from datetime import date

from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton)
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

        await db.commit()
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
        [InlineKeyboardButton(text="📊 Davomat report", callback_data="report")],
        [InlineKeyboardButton(text="📣 Xabar yuborish", callback_data="broadcast")],
        [InlineKeyboardButton(text="🥊 Murabbiy info", callback_data="coach")]
    ])

# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id FROM users WHERE id=?", (msg.from_user.id,))
        u = await cur.fetchone()

        if not u:
            await db.execute(
                "INSERT INTO users(id,name) VALUES(?,?)",
                (msg.from_user.id, msg.from_user.full_name)
            )
            await db.commit()

    kb = admin_kb() if msg.from_user.id == ADMIN_ID else user_kb()
    await msg.answer("🥊 UMIDOV BOKS CLUB CRM", reply_markup=kb)

# ================= USERS LIST =================
@dp.callback_query(F.data == "users")
async def users(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id,name,phone FROM users")
        rows = await cur.fetchall()

    text = "👥 SPORTCHILAR:\n\n"
    for r in rows:
        text += f"🆔 {r[0]}\n👤 {r[1]}\n📞 {r[2]}\n\n"

    await call.message.edit_text(text)

# ================= PROFILE =================
@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT name,phone,payment,attendance,missed,last_payment,pay_type
        FROM users WHERE id=?
        """, (call.from_user.id,))
        u = await cur.fetchone()

    await call.message.edit_text(f"""
👤 {u[0]}
📞 {u[1]}
💰 {'✔' if u[2] else '❌'} ({u[6]})
📊 Davomat: {u[3]}
❌ Qoldirgan: {u[4]}
📅 Oxirgi to‘lov: {u[5]}
""", reply_markup=user_kb())

# ================= PAYMENT =================
@dp.callback_query(F.data == "pay")
async def pay(call: CallbackQuery):

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta", callback_data="card")],
        [InlineKeyboardButton(text="💵 Naqd", callback_data="cash")]
    ])

    await call.message.edit_text(f"💳 Karta: {CARD}", reply_markup=kb)

# ================= CARD =================
@dp.message(F.photo)
async def card_check(msg: Message):

    = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"card_{msg.from_user.id}")
    ]])

    await bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption="💳 Chek")

    await msg.answer("📩 Yuborildi")

@dp.callback_query(F.data.startswith("card_"))
async def card_ok(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        UPDATE users SET payment=1, pay_type='card', last_payment=?
        WHERE id=?
        """, (date.today().isoformat(), uid))
        await db.commit()

    await bot.send_message(uid, "💳 To‘lov tasdiqlandi")

# ================= CASH =================
@dp.callback_query(F.data == "cash")
async def cash(call: CallbackQuery):

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✔ Tasdiqlash", callback_data=f"cash_{call.from_user.id}")
    ]])

    await bot.send_message(ADMIN_ID, f"💵 NAQD {call.from_user.id}", reply_markup=kb)

@dp.callback_query(F.data.startswith("cash_"))
async def cash_ok(call: CallbackQuery):

    uid = int(call.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        UPDATE users SET payment=1, pay_type='cash', last_payment=?
        WHERE id=?
        """, (date.today().isoformat(), uid))
        await db.commit()

    await bot.send_message(uid, "💵 Naqd tasdiqlandi")

# ================= ATTENDANCE =================
@dp.callback_query(F.data == "report")
async def report(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name,attendance,missed FROM users")
        rows = await cur.fetchall()

    text = "📊 REPORT\n\n"
    for r in rows:
        status = "🟢 GOOD" if r[1] > r[2] else "🔴 BAD"
        text += f"{r[0]} | ➕{r[1]} ❌{r[2]} {status}\n"

    await call.message.edit_text(text)

# ================= DEBTORS =================
@dp.callback_query(F.data == "debt")
async def debt(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name,last_payment FROM users WHERE payment=0")
        rows = await cur.fetchall()

    text = "❌ QARZDORLAR\n\n"
    for r in rows:
        text += f"{r[0]} | {r[1]}\n"

    await call.message.edit_text(text)

# ================= BROADCAST =================
@dp.callback_query(F.data == "broadcast")
async def broadcast(call: CallbackQuery):

    await call.message.answer("📣 Xabar yozing:")

    @dp.message()
    async def send(msg: Message):
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("SELECT id FROM users")
            users = await cur.fetchall()

        for u in users:
            try:
                await bot.send_message(u[0], msg.text)
            except Exception:
                pass

        await msg.answer("✔ Yuborildi")

# ================= COACH INFO =================
@dp.callback_query(F.data == "coach")
async def coach(call: CallbackQuery):
    await call.message.edit_text("""
🥊 MURABBIY:
👤 Umidov Rajabboy Xushnud ogli
📞 +99899 741 33 61

💪 Professional boxing coach
""")
# ================= Sportchilar =================
@dp.message(F.text == "👥 Sportchilar")
async def sportchilar(message: Message):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute(
            "SELECT id, name FROM users"
        )

        users = await cursor.fetchall()

    buttons = []

    for user in users:

        buttons.append([
            InlineKeyboardButton(
                text=f"✅ {user[1]}",
                callback_data=f"att_{user[0]}"
            )
        ])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await message.answer(
        "🥊 Davomat olish:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("att_"))
async def attendance(callback: CallbackQuery):

    user_id = callback.data.split("_")[1]

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        UPDATE users
        SET attendance = attendance + 1
        WHERE id = ?
        """, (user_id,))

        await db.commit()

    await callback.answer("✅ Davomat olindi")

    await callback.message.answer(
        "✅ Davomat qo‘shildi"
    )

    # ================= To'laganlar =================
   
@dp.callback_query(F.data == "paid")
async def paid(call: CallbackQuery):

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("""
        SELECT name, pay_type, last_payment
        FROM users
        WHERE payment=1
        """)
        rows = await cur.fetchall()

    if not rows:
        await call.message.edit_text("❌ Hali to‘lagan sportchilar yo‘q")
        return

    text = "💰 TO‘LAGAN SPORTCHILAR\n\n"

    for r in rows:
        text += f"👤 {r[0]}\n💳 {r[1]}\n📅 {r[2]}\n\n"

    await call.message.edit_text(text)

# ================= ATTEDANCE SYSTEM =================

from datetime import datetime

@dp.message(F.text == "📊 Davomat report")
async def davomat(message: Message):

    async with aiosqlite.connect(DB) as db:

        cursor = await db.execute(
            "SELECT id, name FROM users"
        )

        users = await cursor.fetchall()

    for user in users:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Keldi",
                        callback_data=f"came_{user[0]}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Kelmadi",
                        callback_data=f"missed_{user[0]}"
                    )
                ]
            ]
        )

        await message.answer(
            f"🥊 {user[1]}",
            reply_markup=keyboard
        )


@dp.callback_query(F.data.startswith("came_"))
async def came(callback: CallbackQuery):

    user_id = callback.data.split("_")[1]

    sana = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        INSERT INTO attendance
        (user_id, date, status)
        VALUES (?, ?, ?)
        """, (
            user_id,
            sana,
            "keldi"
        ))

        await db.commit()

    await callback.answer("✅ Keldi")


@dp.callback_query(F.data.startswith("missed_"))
async def missed(callback: CallbackQuery):

    user_id = callback.data.split("_")[1]

    sana = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        INSERT INTO attendance
        (user_id, date, status)
        VALUES (?, ?, ?)
        """, (
            user_id,
            sana,
            "kelmadi"
        ))

        await db.commit()

    await callback.answer("❌ Kelmadi")

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())