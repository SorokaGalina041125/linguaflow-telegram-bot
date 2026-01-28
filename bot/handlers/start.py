"""Обработчик команды /start и главного меню"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import DatabaseError, IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import BOT_NAME
from bot.database.database import async_session_maker
from bot.database.models import User
from bot.database.repository import get_user_by_telegram_id

# FIX: Добавлен logger для обработки ошибок транзакций (P0.1)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    telegram_id = user.id

    # Регистрируем или получаем пользователя
    async with async_session_maker() as session:
        try:
            # FIX: Использование репозитория вместо дублированного кода (P1.1)
            db_user = await get_user_by_telegram_id(session, telegram_id)

            if not db_user:
                db_user = User(telegram_id=telegram_id)
                session.add(db_user)
                await session.commit()
                await session.refresh(db_user)
        except IntegrityError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            logger.error(f"Integrity error in start_command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Ошибка целостности данных при регистрации. Попробуйте еще раз."
            )
            return
        except DatabaseError as e:
            # FIX: Добавлен rollback для обработки ошибок транзакций (P0.1)
            await session.rollback()
            logger.error(f"Database error in start_command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка при регистрации. Попробуйте еще раз через несколько секунд."
            )
            return
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in start_command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла неожиданная ошибка. Попробуйте еще раз."
            )
            return

    # Приветственное сообщение
    welcome_text = (
        f"👋 *Добро пожаловать в {BOT_NAME}!*\n\n"
        "🎓 *Внимание!* настоящий бот разработан в рамках учебной программы.\n\n"
        "✨ *Что я умею:*\n"
        "• 📚 Тренировка со словами IT-тематики\n"
        "• ➕ Добавление своих слов в личный словарь\n"
        "• 🔙 Управление личной коллекцией слов\n"
        "• 📊 Отслеживание прогресса обучения\n"
        "• 🎮 Интерактивные тренировки с вариантами ответов\n"
        "• 🔄 Выбор направления перевода (RU→EN или EN→RU)\n\n"
        "Выбери действие ниже и начнем наше путешествие в мир английского! 🚀"
    )

    # Клавиатура главного меню
    keyboard = [
        [InlineKeyboardButton("🎯 Начать тренировку", callback_data="training_start")],
        [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="statistics_menu")],
        [InlineKeyboardButton("⭐ Достижения", callback_data="achievements_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик возврата в главное меню"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🎯 Начать тренировку", callback_data="training_start")],
        [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="statistics_menu")],
        [InlineKeyboardButton("⭐ Достижения", callback_data="achievements_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🏠 *Главное меню*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=reply_markup
    )
