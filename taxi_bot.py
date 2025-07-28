import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import Response
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, BotCommand, Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command

# 1. Загрузка .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
WEBHOOK_SECRET = os.getenv("cheongjutaxi")
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 2. Логирование
logging.basicConfig(level=logging.INFO)

# 3. Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# 4. Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    await bot.set_my_commands([
        BotCommand(command="start", description="🔄 Перезапуск"),
        BotCommand(command="contact", description="📞 Контакт"),
        BotCommand(command="info", description="ℹ️ Описание")
    ])
    print("✅ Webhook установлен:", WEBHOOK_URL)

    yield
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()


# 5. Приложение
app = FastAPI(lifespan=lifespan)


# 6. Webhook-обработка
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    body = await request.body()
    logging.info(f"📩 Получен webhook: {body.decode()}")
    update = Update.model_validate_json(body.decode())
    await dp.feed_update(bot, update)
    return Response(status_code=200)


# 7. Клавиатуры
menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Такси 🚕")],
    [KeyboardButton(text="Доставка 🙵")],
    [KeyboardButton(text="Трезвый водитель 😇")],
    [KeyboardButton(text="Перегон автомобиля 🚗")]
], resize_keyboard=True)

request_buttons = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
    [KeyboardButton(text="📞 Отправить номер телефона", request_contact=True)],
    [KeyboardButton(text="⬅️ Назад")]
], resize_keyboard=True, one_time_keyboard=True)

# 8. Хранилище
user_data = {}


# 9. Хендлеры
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Здравствуйте, {message.from_user.full_name}!\nВыберите услугу:",
        reply_markup=menu
    )


@dp.message(F.text.in_({"Такси 🚕", "Доставка 🙵", "Трезвый водитель 😇", "Перегон автомобиля 🚗"}))
async def select_service(message: Message):
    user_data[message.from_user.id] = {"service": message.text}
    await message.answer("Пожалуйста, отправьте геолокацию и номер телефона:", reply_markup=request_buttons)


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):
    user_data.pop(message.from_user.id, None)
    await message.answer("Вы вернулись в главное меню. Выберите услугу:", reply_markup=menu)


@dp.message(F.location)
async def handle_location(message: Message):
    user_data.setdefault(message.from_user.id, {})["location"] = message.location
    await check_and_notify(message)


@dp.message(F.contact)
async def get_contact(message: Message):
    user_data.setdefault(message.from_user.id, {})["phone"] = message.contact.phone_number
    await check_and_notify(message)


async def check_and_notify(message: Message):
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    if "location" in data and "phone" in data:
        loc = data["location"]
        phone = data["phone"]
        service = data["service"]
        user = message.from_user

        kakao_link = f"https://map.kakao.com/link/map/{loc.latitude},{loc.longitude}"
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
        await message.answer("✅ Спасибо! Ваш заказ принят. Оператор скоро с вами свяжется.",
                             reply_markup=ReplyKeyboardRemove())
        user_data.pop(user_id, None)


@dp.message(Command("contact"))
async def contact_info(message: Message):
    await message.answer("📞 Диспетчер: +82 10-4307-1105", reply_markup=menu)


@dp.message(Command("info"))
async def info(message: Message):
    await message.answer(
        "🚖 Taxi Cheongju — круглосуточная служба заказа такси, доставки и трезвого водителя в городе Чхонджу.",
        reply_markup=menu)


@dp.message()
async def unknown(message: Message):
    await message.answer("Пожалуйста, выберите команду из меню:", reply_markup=menu)
