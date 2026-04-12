import asyncio
from datetime import datetime
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import TELEGRAM_TOKEN
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class Form(StatesGroup):
    name = State()
    date_of_birth = State()


@dp.message(Command("start" ))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.name)
    await message.answer(
                         "Привет! Я тестовый бот, давай знакомиться\n"
                         "Шаг 1 из 2 - Как тебя зовут?"
    )
    logger.info("Пользователь %s начал взаимодействие с ботом.", message.from_user.id)

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Диалог отменен. Если хочешь начать заново, напиши /start")


@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текст")
        return
    name = message.text.strip()

    if len(name) < 2 or not any(ch.isalpha() for ch in name):
        await message.answer("⚠️ Имя введено некорректно. Попробуй ещё раз")
        return

    logger.info("Пользователь %s ввел имя: ", message.from_user.id, name)

    await state.update_data(name=name)
    await state.set_state(Form.date_of_birth)
    await message.answer("Шаг 2 из 2 — Напиши дату рождения в формате ДД.MM.ГГГГ (например 25.03.1990)")


@dp.message(Form.date_of_birth)
async def process_date(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    try:
        dob = datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await message.answer("⚠️ Формат даты неверный. Введите в формате ДД.MM.ГГГГ")
        return

    today = datetime.now().date()
    if dob.date() > today:
        await message.answer("⚠️ Дата в будущем, ты ещё не родился) Попробуй ещё раз")
        return

    birth = dob.date()
    # Вычисляем возраст с учётом того, был ли уже день рождения в этом году
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    data = await state.get_data()
    name = data.get("name")

    await message.answer(f"Привет, {name}, тебе сейчас {age}")
    await state.clear()

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Запуск бота...")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")

    try:

        await dp.start_polling(bot)
    except ConnectionError as e:
        logger.error(f"Ошибка соединения с Telegram API: {e}")
        logger.info("Проверьте ваше интернет-соединение и токен бота.")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        logger.info("Бот будет перезапущен...")
    finally:
        try:
            await bot.session.close()
        except Exception as e:
            logger.error(f"Ошибка при закрытии сессии бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())





