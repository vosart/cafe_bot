import math
import logging
import telebot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_TOKEN, ADMIN_ID
from ai_handler import ask_ai
from database import (
    init_db,
    save_booking,
    get_all_bookings,
    get_stats,
    update_booking_status,
    get_user_bookings,
    get_booking_by_id,
    get_menu,
    get_menu_by_category,
    add_menu_item,
)
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

STATUS_MAP = {
    "pending": "⏳ Ожидает",
    "confirmed": "✅ Подтверждена",
    "cancelled": "❌ Отменена",
}


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False


bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot.remove_webhook()


def main_menu():
    keyboard = InlineKeyboardMarkup()

    keyboard.add(InlineKeyboardButton("📋 Меню", callback_data="menu"))
    keyboard.add(InlineKeyboardButton("🕐 Часы работы", callback_data="hours"))
    keyboard.add(InlineKeyboardButton("📅 Забронировать столик", callback_data="book"))
    keyboard.add(InlineKeyboardButton("📂 Мои брони", callback_data="booking_page_0"))
    keyboard.add(InlineKeyboardButton("❓ Задать вопрос", callback_data="question"))

    return keyboard


def format_booking(booking_id, name, date, guests, phone):
    return (
        f"🔔 Бронь #{booking_id}\n\n"
        f"👤 Имя: {name}\n"
        f"📅 Дата: {date}\n"
        f"👥 Гостей: {guests}\n"
        f"📞 Телефон: {phone}\n"
    )


@bot.message_handler(commands=["start"])
def start(message):
    logger.info("Пользователь %s запустил бота", message.from_user.id)
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в кафе *Уют*!\n\nЧем могу помочь?",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "menu")
def handle_menu(call):
    data = get_menu()
    categories = {}
    for item in data:
        category = item[1]
        if category not in categories:
            categories[category] = []
        categories[category].append(item)]
    
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "📋 *Выберите категорию*\n\n"
        f"{category for category in categories.keys()}\n"}"
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: call.data == "hours")
def hours_handler(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🕐 Часы работы: пн-пт 09:00-22:00, сб-вс 10:00-23:00",
        parse_mode="Markdown",
    )


booking_data = {}


@bot.callback_query_handler(func=lambda call: call.data == "book")
def book_handler(call):
    bot.answer_callback_query(call.id)
    logger.info("Пользователь %s начал бронирование", call.from_user.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📅 *Бронирование столика*\n\nШаг 1 из 4\nВведите ваше имя:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, get_name)


def get_name(message):
    name = message.text.strip()
    if len(name) < 2:
        msg = bot.send_message(
            message.chat.id, "⚠️ Имя слишком короткое. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_name)
        return
    booking_data[message.chat.id] = {"name": name}

    msg = bot.send_message(
        message.chat.id,
        "Шаг 2 из 4\nВведите дату брони\n_(например: 25.03.2026)_",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, get_date)


def get_date(message):
    date = message.text.strip()
    if is_valid_date(date) == False:
        msg = bot.send_message(
            message.chat.id, "⚠️ Формат даты неверный. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_date)
        return
    booking_data[message.chat.id]["date"] = date

    msg = bot.send_message(
        message.chat.id, "Шаг 3 из 4\nВведите количество гостей", parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_guests)


def get_guests(message):
    guests = message.text.strip()
    if guests.isdigit() == False:
        msg = bot.send_message(message.chat.id, "⚠️ Вы ввели не число. Введите ещё раз:")
        bot.register_next_step_handler(msg, get_guests)
        return

    if int(guests) < 1 or int(guests) > 20:
        msg = bot.send_message(
            message.chat.id, "⚠️ Количество гостей от 1 до 20. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_guests)
        return

    booking_data[message.chat.id]["guests"] = guests

    msg = bot.send_message(
        message.chat.id,
        "Шаг 4 из 4\nВведите свой номер телефона",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, get_phone)


def get_phone(message):
    phone = message.text.strip()
    if len(phone) < 5 or len(phone) > 15:
        msg = bot.send_message(
            message.chat.id, "⚠️ Неверное количество цифр в номере. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_phone)
        return
    booking_data[message.chat.id]["phone"] = phone

    data = booking_data[message.chat.id]

    try:
        booking_id = save_booking(
            name=data["name"],
            phone=data["phone"],
            date=data["date"],
            guests=data["guests"],
            telegram_id=message.from_user.id,
        )
        logger.info(
            "Новая бронь #%s от пользователя %s на %s (%s гостей)",
            booking_id,
            message.from_user.id,
            data["date"],
            data["guests"],
        )
    except Exception as e:
        logger.error("Ошибка БД при сохранении брони: %s", e)
        bot.send_message(message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
        return

    bot.send_message(
        message.chat.id,
        f"✅ Бронь принята!\n\n"
        + format_booking(
            booking_id, data["name"], data["date"], data["guests"], data["phone"]
        )
        + f"Ждём вас! 🎉\n",
        parse_mode="Markdown",
    )

    # Уведомление админу
    confirm_markup = InlineKeyboardMarkup()
    confirm_markup.row(
        InlineKeyboardButton(
            "✅ Подтвердить",
            callback_data=f"confirm_{booking_id}_{message.from_user.id}",
        ),
        InlineKeyboardButton(
            "❌ Отклонить", callback_data=f"reject_{booking_id}_{message.from_user.id}"
        ),
    )

    bot.send_message(
        ADMIN_ID,
        f"🔔 *Новая бронь*\n\n"
        + format_booking(
            booking_id, data["name"], data["date"], data["guests"], data["phone"]
        )
        + f"👤 Telegram ID: {message.from_user.id}",
        parse_mode="Markdown",
        reply_markup=confirm_markup,
    )

    bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())
    del booking_data[message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == "booking_page_0")
def user_bookings_handler(call):
    bot.answer_callback_query(call.id)

    try:
        data = get_user_bookings(call.from_user.id)
    except Exception as e:
        logger.error(
            "Ошибка БД при получении броней пользователя %s: %s", call.from_user.id, e
        )
        bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
        return

    if not data:
        bot.send_message(call.message.chat.id, "У вас нет броней")
    else:
        for row in data:
            cancel_markup = InlineKeyboardMarkup()
            cancel_markup.row(
                InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{row[0]}")
            )
            bot.send_message(
                call.message.chat.id,
                format_booking(row[0], row[1], row[3], row[4], row[2])
                + f"📌 Статус: {STATUS_MAP.get(row[6])}\n",
                parse_mode="Markdown",
                reply_markup=cancel_markup,
            )


@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def handle_user_booking_cancel(call):
    bot.answer_callback_query(call.id)
    booking_id = int(call.data.split("_")[1])
    update_booking_status(booking_id, "cancelled")
    logger.info("Пользователь %s отменил бронь #%s", call.from_user.id, booking_id)
    bot.send_message(
        call.message.chat.id,
        f"✅ Ваша бронь *#{booking_id}* отменена!\n",
        parse_mode="Markdown",
    )

    try:
        data = get_booking_by_id(booking_id)
    except Exception as e:
        logger.error("Ошибка БД при получении брони #%s: %s", booking_id, e)
        bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
        return

    bot.send_message(
        ADMIN_ID,
        f"🚫 Пользователь отменил бронь!\n\n"
        + format_booking(data[0], data[1], data[3], data[4], data[2]),
        parse_mode="Markdown",
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("confirm_")
    or call.data.startswith("reject_")
)
def handle_booking_status(call):
    parts = call.data.split("_")
    action = parts[0]
    booking_id = int(parts[1])
    user_id = int(parts[2])

    if action == "confirm":
        try:
            update_booking_status(booking_id, "confirmed")
            logger.info(
                "Админ подтвердил бронь #%s для пользователя %s", booking_id, user_id
            )
        except Exception as e:
            logger.error("Ошибка БД при подтверждении брони #%s: %s", booking_id, e)
            bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
            return

        try:
            bot.send_message(
                user_id,
                f"✅ Ваша бронь *#{booking_id}* подтверждена!\n"
                f"Ждём вас в кафе *Уют*! 🎉",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(
                "Не удалось отправить уведомление пользователю %s: %s", user_id, e
            )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n✅ *Подтверждено*",
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id, "Бронь подтверждена")

    elif action == "reject":
        try:
            update_booking_status(booking_id, "rejected")
            logger.info(
                "Админ отклонил бронь #%s для пользователя %s", booking_id, user_id
            )
        except Exception as e:
            logger.error("Ошибка БД при отклонении брони #%s: %s", booking_id, e)
            bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
            return

        try:
            bot.send_message(
                user_id,
                f"❌ Ваша бронь *#{booking_id}* отклонена.\n"
                f"Для уточнения деталей свяжитесь с нами.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(
                "Не удалось отправить уведомление пользователю %s: %s", user_id, e
            )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n❌ *Отклонено*",
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id, "Бронь отклонена!")


@bot.callback_query_handler(func=lambda call: call.data == "question")
def question_handler(call):
    bot.answer_callback_query(call.id)
    logger.info("Пользователь %s задаёт вопрос AI", call.from_user.id)
    msg = bot.send_message(call.message.chat.id, "❓ Напишите ваш вопрос, и я отвечу:")
    bot.register_next_step_handler(msg, get_answer)


def get_answer(message):
    logger.info("AI-запрос от пользователя %s: %s", message.from_user.id, message.text)
    thinking_msg = bot.send_message(message.chat.id, "⏳ Думаю над ответом...")
    answer = ask_ai(message.text)

    bot.delete_message(message.chat.id, thinking_msg.message_id)
    bot.send_message(message.chat.id, f"🤖 {answer}", reply_markup=main_menu())


def admin_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📋 Все брони", callback_data="admin_bookings"))
    markup.row(InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    return markup


@bot.message_handler(commands=["admin"])
def admin_handler(message):
    if message.from_user.id != ADMIN_ID:
        logger.warning(
            "Попытка доступа к /admin от пользователя %s", message.from_user.id
        )
        bot.send_message(message.chat.id, "⛔ Нет доступа")
        return

    logger.info("Админ %s открыл панель управления", message.from_user.id)

    bot.send_message(
        message.chat.id,
        "👨‍💼 *Панель администратора*",
        parse_mode="Markdown",
        reply_markup=admin_menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_bookings")
def admin_bookings_handler(call):
    bot.answer_callback_query(call.id)

    try:
        all_bookings = get_all_bookings()
    except Exception as e:
        logger.error("Ошибка БД при получении всех броней: %s", e)
        bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
        return

    if not all_bookings:
        bot.send_message(
            call.message.chat.id, "Броней пока нет...", parse_mode="Markdown"
        )
        return

    for row in all_bookings[:10]:
        status_emoji = STATUS_MAP.get(row[6] or "pending", "⏳")
        bot.send_message(
            call.message.chat.id,
            f"{status_emoji} #{row[0]} | {row[1]} | {row[3]} | количество гостей: {row[4]} | {row[2]}",
        )

    if len(all_bookings) > 10:
        bot.send_message(
            call.message.chat.id, f"...и ещё {len(all_bookings) - 10} броней"
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("booking_page_"))
def booking_page_handler(call):
    bot.answer_callback_query(call.id)
    page_size = 3
    page = int(call.data.split("_")[2])

    try:
        data = get_user_bookings(call.from_user.id)
    except Exception as e:
        logger.error(
            "Ошибка БД при получении броней пользователя %s: %s", call.from_user.id, e
        )
        bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
        return

    if data is None:
        bot.send_message(call.message.chat.id, "⚠️ Ошибка базы данных, попробуйте позже")
        return
    if not data:
        bot.send_message(call.message.chat.id, f"Броней пока нет")
        return
    total_pages = math.ceil(len(data) / 3)
    start = page * page_size
    end = start + page_size
    bookings = data[start:end]

    for row in bookings:
        bot.send_message(
            call.message.chat.id,
            f"🔔 Бронь {row[0]} Имя: {row[1]} Дата: {row[3]} Гостей: {row[4]} Телефон: {row[2]} | {STATUS_MAP.get(row[6])}",
        )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"booking_page_{page - 1}" if page > 0 else "none"
        ),
        InlineKeyboardButton(
            f"Страница {page + 1} из {total_pages}", callback_data="none"
        ),
        InlineKeyboardButton(
            "Вперёд ➡️",
            callback_data=f"booking_page_{page + 1}"
            if page < total_pages - 1
            else "none",
        ),
    )
    bot.send_message(call.message.chat.id, "📋 Выберите страницу:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_handler(call):
    bot.answer_callback_query(call.id)

    try:
        stats = get_stats()
    except Exception as e:
        logger.error("Ошибка БД при получении статистики: %s", e)
        bot.send_message(call.message.chat.id, "⚠️ Ошибка в БД. Попробуйте позже...")
        return

    bot.send_message(
        call.message.chat.id,
        "📊 Статистика\n\n"
        f"Всего броней: {stats['total']}\n"
        f"Сегодня: {stats['today']}\n"
        f"Всего гостей: {stats['total_guests']}\n",
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    init_db()
    logger.info("Бот запущен...")
    bot.infinity_polling()
