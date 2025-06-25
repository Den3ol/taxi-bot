import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Загрузка токена из .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
GROUP_ID = -1002701798085  # Замените на ваш ID группы

# Логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Главное меню
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Такси 🚕")],
        [KeyboardButton(text="Доставка 🛵")],
        [KeyboardButton(text="Трезвый водитель 😇")],
        [KeyboardButton(text="Перегон автомобиля 🚗")]
    ],
    resize_keyboard=True
)

# Кнопки для отправки геолокации и телефона
request_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
        [KeyboardButton(text="📞 Отправить номер телефона", request_contact=True)],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Хранилище данных
user_data = {}

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        f"Здравствуйте, {message.from_user.full_name}!\nВыберите услугу:",
        reply_markup=menu
    )

@dp.message(F.text.in_({"Такси 🚕", "Доставка 🛵", "Трезвый водитель 😇", "Перегон автомобиля 🚗"}))
async def service_selected(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = {"service": message.text}
    await message.answer(
        "Пожалуйста, отправьте геолокацию и номер телефона:",
        reply_markup=request_buttons
    )

@dp.message(F.location)
async def handle_location(message: Message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["location"] = message.location
    await check_and_notify(message)

@dp.message(F.contact)
async def handle_contact(message: Message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["phone"] = message.contact.phone_number
    await check_and_notify(message)

@dp.message(F.text == "⬅️ Назад")
async def back_to_menu(message: Message):
    await message.answer("Вы вернулись в главное меню. Выберите услугу:", reply_markup=menu)
    user_data.pop(message.from_user.id, None)

async def check_and_notify(message: Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {})

    if "location" in data and "phone" in data:
        loc = data["location"]
        service = data["service"]
        phone = data["phone"]
        user = message.from_user

        msg = f"""
🚨 <b>Новый заказ</b>
<b>Услуга:</b> {service}
<b>Имя:</b> {user.full_name}
<b>Телефон:</b> <code>{phone}</code>
<b>Username:</b> @{user.username if user.username else '—'}
<b>Локация:</b> 📍 https://www.google.com/maps?q={loc.latitude},{loc.longitude}
<b>User ID:</b> <code>{user.id}</code>
"""

        await bot.send_message(GROUP_ID, msg)
        await message.answer("✅ Спасибо! Ваш заказ принят. Оператор скоро с вами свяжется.", reply_markup=ReplyKeyboardRemove())
        user_data.pop(user_id, None)

# Команды из меню
@dp.message(Command("order"))
async def handle_order(message: Message):
    await message.answer("Чтобы заказать такси, нажмите кнопку «Такси 🚕» в меню ниже.")

@dp.message(Command("sobriety"))
async def handle_sobriety(message: Message):
    await message.answer("Чтобы вызвать трезвого водителя, выберите «Трезвый водитель 😇».")

@dp.message(Command("price"))
async def handle_price(message: Message):
    await message.answer("Цены зависят от расстояния и времени суток. Уточните у оператора после отправки геолокации.")

@dp.message(Command("contact"))
async def handle_contact_cmd(message: Message):
    await message.answer("📞 Диспетчер: +82 10-4307-1105\nВы также можете отправить заявку через бота.")

@dp.message(Command("info"))
async def handle_info(message: Message):
    await message.answer("🚖 Taxi Cheongju — круглосуточная служба заказа такси, доставки и трезвого водителя в городе Чхонджу.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
