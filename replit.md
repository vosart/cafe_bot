# Cafe Uyut Telegram Bot

A Telegram bot for a cafe named "Уют" (Cozy) that automates customer interactions.

## Features
- Display menu and working hours
- Handle table reservations
- AI-powered assistant (YandexGPT) to answer guest questions
- Admin statistics and booking management

## Tech Stack
- **Language:** Python 3.12
- **Bot Framework:** pyTelegramBotAPI (TeleBot)
- **Database:** SQLite (bookings and statistics)
- **AI:** YandexGPT via OpenAI-compatible client
- **Config:** python-dotenv

## Project Structure
- `bot.py` — Main bot logic and command handlers
- `ai_handler.py` — YandexGPT integration
- `database.py` — SQLite schema and CRUD operations
- `config.py` — Environment variable loader
- `cafe_info.txt` — Knowledge base for the AI assistant
- `requirements.txt` — Python dependencies

## Required Secrets
- `CAFE_BOT` — Telegram bot token (from @BotFather)
- `ADMIN_ID` — Telegram user ID of the admin (numeric)
- `YANDEX_CLOUD_API_KEY` — Yandex Cloud API key
- `YANDEX_CLOUD_MODEL` — YandexGPT model URI
- `YANDEX_CLOUD_FOLDER` — Yandex Cloud folder ID

## Running
The bot runs as a console workflow: `python bot.py`
