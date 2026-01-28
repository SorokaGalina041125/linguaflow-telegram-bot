"""Конфигурация бота"""

import os

from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")

# Bot Name
BOT_NAME = "LinguaFlow_Bot"

# FIX: Константы для валидации длины входных данных (P0.2)
MAX_WORD_LENGTH = 255  # Соответствует String(255) в модели Word
MAX_EXAMPLE_LENGTH = 2000  # Соответствует Text в модели Word
MAX_TRANSLATION_LENGTH = 500  # Запас для русского перевода
