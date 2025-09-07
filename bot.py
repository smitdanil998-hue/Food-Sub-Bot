import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
from config import BOT_TOKEN, PAYMENT_DETAILS, ADMIN_ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Database ---
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    address TEXT,
    subscription INTEGER DEFAULT 0,
    status TEXT DEFAULT 'inactive'
)""")
conn.commit()


# --- Keyboards ---
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("📦 Оформить подписку"))
main_kb.add(KeyboardButton("📅 Мои доставки"))
main_kb.add(KeyboardButton("💳 Подтвердить оплату"))

sub_kb = ReplyKeyboardMarkup(resize_keyboard=True)
sub_kb.add("5 обедов - 1750₽", "10 обедов - 3500₽")
sub_kb.add("15 обедов - 5250₽", "20 обедов - 7000₽")
sub_kb.add("🔙 Назад")


# --- Handlers ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        await message.answer("👋 Добро пожаловать! Давайте зарегистрируемся.
Введите ваше имя:")
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (message.from_user.id,))
        conn.commit()
        return
    await message.answer("Главное меню:", reply_markup=main_kb)


@dp.message_handler(lambda m: m.text and m.text.startswith("📦"))
async def subscribe(message: types.Message):
    await message.answer("Выберите тариф:", reply_markup=sub_kb)


@dp.message_handler(lambda m: m.text in [
    "5 обедов - 1750₽", "10 обедов - 3500₽",
    "15 обедов - 5250₽", "20 обедов - 7000₽"
])
async def set_subscription(message: types.Message):
    subs = {
        "5 обедов - 1750₽": (5, 1750),
        "10 обедов - 3500₽": (10, 3500),
        "15 обедов - 5250₽": (15, 5250),
        "20 обедов - 7000₽": (20, 7000),
    }
    count, price = subs[message.text]
    cursor.execute("UPDATE users SET subscription=?, status=? WHERE user_id=?",
                   (count, "waiting_payment", message.from_user.id))
    conn.commit()
    await message.answer(f"Вы выбрали {count} обедов за {price}₽.
"
                         f"Переведите оплату по реквизитам:
{PAYMENT_DETAILS}

"
                         f"После оплаты нажмите «💳 Подтвердить оплату»",
                         reply_markup=main_kb)


@dp.message_handler(lambda m: m.text == "💳 Подтвердить оплату")
async def confirm_payment(message: types.Message):
    await message.answer("Загрузите фото чека или скриншот перевода.")
    # Следующий шаг - ловим фото


@dp.message_handler(content_types=["photo"])
async def handle_photo(message: types.Message):
    cursor.execute("UPDATE users SET status=? WHERE user_id=?",
                   ("payment_check", message.from_user.id))
    conn.commit()
    await message.photo[-1].download(f"check_{message.from_user.id}.jpg")
    await message.answer("✅ Чек отправлен администратору на проверку.")
    await bot.send_message(ADMIN_ID, f"Пользователь {message.from_user.full_name} отправил чек.")
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id)


@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    text = "📋 Пользователи:
"
    for u in users:
        text += f"ID: {u[0]}, Имя: {u[1]}, Подписка: {u[4]}, Статус: {u[5]}
"
    await message.answer(text)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
