import asyncio
import logging
from typing import Optional

from config import TELEGRAM_TOKEN, ADMIN_ID
from ai_handler_async import ask_ai_async

try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.filters import Command
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import StatesGroup, State
    from aiogram.fsm.storage.memory import MemoryStorage
except Exception as e:
    Bot = Dispatcher = types = Message = InlineKeyboardMarkup = InlineKeyboardButton = Command = FSMContext = StatesGroup = State = MemoryStorage = None
    logging.getLogger(__name__).warning("aiogram not installed: %s", e)

import db_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if Bot is None:
    logger.error("aiogram is not installed. Install requirements from requirements_async.txt")

storage = MemoryStorage() if MemoryStorage is not None else None
bot = Bot(token=TELEGRAM_TOKEN) if Bot is not None else None
dp = Dispatcher(storage=storage) if Dispatcher is not None else None


def is_valid_date(date_str: str) -> bool:
    from datetime import datetime

    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except Exception:
        return False


def main_menu() -> Optional[InlineKeyboardMarkup]:
    if InlineKeyboardMarkup is None:
        return None
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(text="📋 Меню", callback_data="menu"),
        InlineKeyboardButton(text="🕐 Часы работы", callback_data="hours"),
        InlineKeyboardButton(text="📅 Забронировать столик", callback_data="book"),
        InlineKeyboardButton(text="📂 Мои брони", callback_data="booking_page_0"),
        InlineKeyboardButton(text="❓ Задать вопрос", callback_data="question"),
    )
    return markup


# FSM states for booking
class Booking(StatesGroup):
    name = State()
    date = State()
    guests = State()
    phone = State()


if dp is not None:
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer(
            "👋 Добро пожаловать в кафе *Уют*!\\n\\nЧем могу помочь?",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    @dp.message(Command("book"))
    async def cmd_book(message: Message, state: FSMContext):
        await state.clear()
        await state.set_state(Booking.name)
        await message.answer("📅 *Бронирование столика*\\n\\nШаг 1 из 4\\nВведите ваше имя:", parse_mode="Markdown")

    @dp.message(Booking.name)
    async def process_name(message: Message, state: FSMContext):
        name = (message.text or "").strip()
        if len(name) < 2:
            await message.answer("⚠️ Имя слишком короткое. Введите ещё раз:")
            return
        await state.update_data(name=name)
        await state.set_state(Booking.date)
        await message.answer("Шаг 2 из 4\\nВведите дату брони (например: 25.03.2026):", parse_mode="Markdown")

    @dp.message(Booking.date)
    async def process_date(message: Message, state: FSMContext):
        date = (message.text or "").strip()
        if not is_valid_date(date):
            await message.answer("⚠️ Формат даты неверный. Введите ещё раз:")
            return
        await state.update_data(date=date)
        await state.set_state(Booking.guests)
        await message.answer("Шаг 3 из 4\\nВведите количество гостей:", parse_mode="Markdown")

    @dp.message(Booking.guests)
    async def process_guests(message: Message, state: FSMContext):
        guests_text = (message.text or "").strip()
        if not guests_text.isdigit():
            await message.answer("⚠️ Вы ввели не число. Введите ещё раз:")
            return
        guests = int(guests_text)
        if guests < 1 or guests > 20:
            await message.answer("⚠️ Количество гостей от 1 до 20. Введите ещё раз:")
            return
        await state.update_data(guests=guests)
        await state.set_state(Booking.phone)
        await message.answer("Шаг 4 из 4\\nВведите свой номер телефона:", parse_mode="Markdown")

    @dp.message(Booking.phone)
    async def process_phone(message: Message, state: FSMContext):
        phone = (message.text or "").strip()
        if len(phone) < 5 or len(phone) > 15:
            await message.answer("⚠️ Неверное количество цифр в номере. Введите ещё раз:")
            return
        data = await state.get_data()
        name = data.get("name")
        date = data.get("date")
        guests = data.get("guests")
        try:
            booking_id = await db_async.save_booking(
                name=name,
                phone=phone,
                date=date,
                guests=guests,
                telegram_id=message.from_user.id,
            )
            logger.info("Новая бронь #%s от пользователя %s на %s (%s гостей)", booking_id, message.from_user.id, date, guests)
        except Exception as e:
            logger.exception("Ошибка БД при сохранении брони: %s", e)
            await message.answer("⚠️ Ошибка в БД. Попробуйте позже...")
            await state.clear()
            return

        # notify admin
        if InlineKeyboardMarkup is not None:
            confirm_markup = InlineKeyboardMarkup(row_width=2)
            confirm_markup.add(
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{booking_id}_{message.from_user.id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{booking_id}_{message.from_user.id}"),
            )
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🔔 *Новая бронь*\\n\\n"
                    f"🔔 Бронь #{booking_id}\\n\\n"
                    f"👤 Имя: {name}\\n"
                    f"📅 Дата: {date}\\n"
                    f"👥 Гостей: {guests}\\n"
                    f"📞 Телефон: {phone}\\n"
                    f"👤 Telegram ID: {message.from_user.id}",
                    parse_mode="Markdown",
                    reply_markup=confirm_markup,
                )
            except Exception:
                logger.exception("Не удалось отправить уведомление админу")
        await message.answer(
            "✅ Бронь принята!\\n\\n" +
            f"🔔 Бронь #{booking_id}\\n\n" +
            f"👤 Имя: {name}\\n📅 Дата: {date}\\n👥 Гостей: {guests}\\n📞 Телефон: {phone}\\n\n" +
            "Ждём вас! 🎉",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
        await state.clear()

    @dp.callback_query()
    async def handle_callbacks(callback: types.CallbackQuery):
        data = callback.data or ""
        if data.startswith("confirm_") or data.startswith("reject_"):
            parts = data.split("_")
            action = parts[0]
            booking_id = int(parts[1])
            user_id = int(parts[2])
            if action == "confirm":
                await db_async.update_booking_status(booking_id, "confirmed")
                try:
                    await bot.send_message(user_id, f"✅ Ваша бронь *#{booking_id}* подтверждена!\\nЖдём вас в кафе *Уют*! 🎉", parse_mode="Markdown")
                except Exception:
                    logger.warning("Не удалось отправить уведомление пользователю %s", user_id)
                try:
                    await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=(callback.message.text + "\\n\\n✅ *Подтверждено*"), parse_mode="Markdown")
                except Exception:
                    pass
                await callback.answer("Бронь подтверждена")
            else:
                await db_async.update_booking_status(booking_id, "rejected")
                try:
                    await bot.send_message(user_id, f"❌ Ваша бронь *#{booking_id}* отклонена. Для уточнения деталей свяжитесь с нами.", parse_mode="Markdown")
                except Exception:
                    logger.warning("Не удалось отправить уведомление пользователю %s", user_id)
                try:
                    await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=(callback.message.text + "\\n\\n❌ *Отклонено*"), parse_mode="Markdown")
                except Exception:
                    pass
                await callback.answer("Бронь отклонена!")

else:
    # fallback dummy handlers
    def cmd_start(message):
        pass

    def cmd_book(message):
        pass


async def main():
    if bot is None or dp is None:
        logger.error("Bot or Dispatcher not available. Install aiogram.")
        return
    await db_async.init_db()
    logger.info("Запуск async-бота с FSM бронирования (PoC)...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
