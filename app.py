import json

from flask import Flask, request
import telebot
import telebot.types
from bot import bot
from database import init_db

app = Flask(__name__)

init_db()
bot.remove_webhook()
bot.set_webhook(url='https://vosart.pythonanywhere.com/webhook')

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

if __name__ == "__main__":
    app.run()