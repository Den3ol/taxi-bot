import logging
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, BotCommand, Update
)
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.webhook.aiohttp_server import setup_application
from aiohttp import web

# Загрузка переменных из .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Railway URL + /webhook

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
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

# Кнопки для запроса геолокации и телефона
request_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
        [KeyboardButton(text="📞 Отправить номер телефона", request_contact=True)],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Временное хранилище
user_data = {}

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Здравствуйте, {message.from_user.full_name}!\nВыберите услугу:",
        reply_markup=menu
    )

@dp.message(F.text.in_({"Такси 🚕", "Доставка 🛵", "Трезвый водитель 😇", "Перегон автомобиля 🚗"}))
async def select_service(message: Message):
    user_data[message.from_user.id] = {"service": message.text}
    await message.answer(
        "Пожалуйста, отправьте геолокацию и номер телефона:",
        reply_markup=request_buttons
    )

@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
    user_data.pop(message.from_user.id, None)
    await message.answer("Вы вернулись в главное меню. Выберите услугу:", reply_markup=menu)

@dp.message(F.location)
async def handle_location(message: Message):
    user_id = message.from_user.id
    location = message.location
    if user_id in user_data:
        user_data[user_id]["location"] = location
    await check_and_notify(message)

@dp.message(F.contact)
async def get_contact(message: Message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["phone"] = message.contact.phone_number
    await check_and_notify(message)

async def check_and_notify(message: Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {})

    if "location" in data and "phone" in data:
        loc = data["location"]
        phone = data["phone"]
        service = data["service"]
        user = message.from_user

        latitude = loc.latitude
        longitude = loc.longitude
        kakao_link = f"https://map.kakao.com/link/map/{latitude},{longitude}"

        msg = (
            f"<b>🚨 Новый заказ</b>\n"
            f"<b>Услуга:</b> {service}\n"
            f"<b>Имя:</b> {user.full_name}\n"
            f"<b>Телефон:</b> <code>{phone}</code>\n"
            f"<b>Username:</b> @{user.username if user.username else '—'}\n"
            f"<b>Локация (KakaoMap):</b> <a href=\"{kakao_link}\">📍 Открыть</a>\n"
            f"<b>User ID:</b> <code>{user.id}</code>"
        )

        await bot.send_message(chat_id=GROUP_ID, text=msg, disable_web_page_preview=True)
        await message.answer("✅ Спасибо! Ваш заказ принят. Оператор скоро с вами свяжется.", reply_markup=ReplyKeyboardRemove())
        user_data.pop(user_id, None)

@dp.message(Command("contact"))
async def contact_info(message: Message):
    await message.answer("📞 Диспетчер: +82 10-4307-1105", reply_markup=menu)

@dp.message(Command("info"))
async def info(message: Message):
    await message.answer("🚖 Taxi Cheongju — круглосуточная служба заказа такси, доставки и трезвого водителя в городе Чхонджу.", reply_markup=menu)

@dp.message()
async def unknown(message: Message):
    await message.answer("Пожалуйста, выберите команду из меню:", reply_markup=menu)

async def set_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="🔄 Перезапустить бота"),
        BotCommand(command="contact", description="📞 Диспетчер"),
        BotCommand(command="info", description="ℹ️ Информация о боте"),
    ])

async def on_startup(app: web.Application):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    await set_bot_commands()

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post("/webhook", dp.handler())
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))