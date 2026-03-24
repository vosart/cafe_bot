import telebot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TELEGRAM_TOKEN, ADMIN_ID
from ai_handler import ask_ai
from database import init_db, save_booking, get_all_bookings, get_stats
from datetime import datetime

def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def main_menu():
    keyboard = InlineKeyboardMarkup()

    keyboard.add(InlineKeyboardButton("📋 Меню", callback_data="menu"))
    keyboard.add(InlineKeyboardButton("🕐 Часы работы", callback_data="hours"))
    keyboard.add(InlineKeyboardButton("📅 Забронировать столик", callback_data="book"))
    keyboard.add(InlineKeyboardButton("❓ Задать вопрос", callback_data="question"))

    return keyboard

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в кафе *Уют*!\n\nЧем могу помочь?",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def handle_menu(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "📋 *Наше меню:*\n\n"
        "☕ Американо — 150 руб\n"
        "☕ Капучино — 200 руб\n"
        "🍲 Борщ — 280 руб\n"
        "🍝 Паста карбонара — 350 руб\n"
        "🍰 Тирамису — 220 руб",
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "hours")
def hours_handler(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🕐 Часы работы: пн-пт 09:00-22:00, сб-вс 10:00-23:00",
        parse_mode="Markdown"
    )

booking_data = {}

@bot.callback_query_handler(func=lambda call: call.data == "book")
def book_handler(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📅 *Бронирование столика*\n\n"
        "Шаг 1 из 4\n"
        "Введите ваше имя:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_name)

def get_name(message):
    name = message.text.strip()
    if len(name) < 2:
        msg = bot.send_message(
            message.chat.id,
            "⚠️ Имя слишком короткое. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_name)
        return
    booking_data[message.chat.id] = {"name": name}

    msg = bot.send_message(
        message.chat.id,
        "Шаг 2 из 4\n"
        "Введите дату брони\n_(например: 25.03.2026)_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_date)

def get_date(message):
    date = message.text.strip()
    if is_valid_date(date) == False:
        msg = bot.send_message(
            message.chat.id,
            "⚠️ Формат даты неверный. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_date)
        return
    booking_data[message.chat.id]["date"] =  date

    msg = bot.send_message(
        message.chat.id,
        "Шаг 3 из 4\n"
        "Введите количество гостей",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_guests)

def get_guests(message):
    guests = message.text.strip()
    if guests.isdigit() == False:
        msg = bot.send_message(
            message.chat.id,
            "⚠️ Вы ввели не число. Введите ещё раз:"
        )
        bot.register_next_step_handler(msg, get_guests)
        return
    if int(guests) < 1 or int(guests) > 20:
        msg = bot.send_message(
            message.chat.id,
            "⚠️ Количество гостей от 1 до 20. Введите ещё раз:"
            )
        bot.register_next_step_handler(msg, get_guests)
        return
    booking_data[message.chat.id]["guests"] = guests

    msg = bot.send_message(
        message.chat.id,
        "Шаг 4 из 4\n"
        "Введите свой номер телефона",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_phone)

def get_phone(message):
    phone = message.text.strip()
    if len(phone) < 5 or len(phone) > 15:
        msg = bot.send_message(
            message.chat.id,
            "⚠️ Неверное количество цифр в номере. Введите ещё раз:"
            )
        bot.register_next_step_handler(msg, get_phone)
        return
    booking_data[message.chat.id]["phone"] = phone

    data = booking_data[message.chat.id]

    booking_id = save_booking(
        name=data["name"],
        phone=data["phone"],
        date=data["date"],
        guests=data["guests"]
        )

    bot.send_message(
        message.chat.id,
        f"✅ Бронь принята!\n"
        f"👤 Имя: {data["name"]}\n"
        f"📅 Дата: {data["date"]}\n"
        f"👥 Гостей: {data["guests"]}\n"
        f"📞 Телефон: {data["phone"]}\n"
        f"Номер брони: #{booking_id}\n"
        f"Ждём вас! 🎉\n",
        parse_mode="Markdown"
    )

    bot.send_message(
        message.chat.id,
        "Чем ещё могу помочь?",
        reply_markup=main_menu()
    )
    del booking_data[message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == "question")
def question_handler(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "❓ Напишите ваш вопрос, и я отвечу:"
    )
    bot.register_next_step_handler(msg, get_answer)

def get_answer(message):
    thinking_msg = bot.send_message(
        message.chat.id,
        "⏳ Думаю над ответом..."
    )
    answer = ask_ai(message.text)

    bot.delete_message(message.chat.id, thinking_msg.message_id)
    bot.send_message(
        message.chat.id,
        f"🤖 {answer}",
        reply_markup=main_menu()
    )

def admin_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📋 Все брони", callback_data="admin_bookings")
    )
    markup.row(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    )
    return markup

@bot.message_handler(commands=["admin"])
def admin_handler(message):

    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Нет доступа")
        return

    bot.send_message(
        message.chat.id,
        "👨‍💼 *Панель администратора*",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data== "admin_bookings")
def admin_bookings_handler(call):
    bot.answer_callback_query(call.id)

    all_bookings = get_all_bookings()

    if not all_bookings:
        bot.send_message(
            call.message.chat.id,
            "Броней пока нет...",
            parse_mode="Markdown")
        return

    for row in all_bookings[:10]:
        bot.send_message(
            call.message.chat.id,
            f"#{row[0]} | {row[1]} | {row[3]} | количество гостей: {row[4]} | {row[2]}",
            parse_mode="Markdown"
        )

    if len(all_bookings) > 10:
        bot.send_message(
            call.message.chat.id,
            f"...и ещё {len(all_bookings) - 10} броней"
                         )

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_handler(call):
    bot.answer_callback_query(call.id)
    stats = get_stats()
    bot.send_message(
        call.message.chat.id,
        "📊 Статистика\n\n"
        f"Всего броней: {stats["total"]}\n"
        f"Сегодня: {stats["today"]}\n"
        f"Всего гостей: {stats["total_guests"]}\n",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    init_db()
    print("Бот запущен...")
    bot.infinity_polling()