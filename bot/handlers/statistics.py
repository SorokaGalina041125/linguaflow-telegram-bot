"""Обработчики статистики"""

import logging
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.exc import DatabaseError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database.database import async_session_maker
from bot.database.models import Statistics, TrainingSession, User, Word
from bot.database.repository import get_user_by_telegram_id

# FIX: Добавлен logger для обработки ошибок транзакций (P0.1)
logger = logging.getLogger(__name__)


async def statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню статистики"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    async with async_session_maker() as session:
        try:
            # FIX: Использование репозитория вместо дублированного кода (P1.1)
            user = await get_user_by_telegram_id(session, user_id)

            if not user:
                await query.edit_message_text("Ошибка: пользователь не найден.")
                return

            # Общая статистика тренировок
            result = await session.execute(
                select(
                    func.count(TrainingSession.id).label("total_sessions"),
                    func.sum(TrainingSession.total_questions).label("total_questions"),
                    func.sum(TrainingSession.correct_answers).label("total_correct"),
                    func.avg(TrainingSession.accuracy).label("avg_accuracy"),
                ).where(TrainingSession.user_id == user_id)
            )
            stats = result.first()

            total_sessions = stats.total_sessions or 0
            total_questions = stats.total_questions or 0
            total_correct = stats.total_correct or 0
            avg_accuracy = float(stats.avg_accuracy or 0)

            # Статистика по словам
            result = await session.execute(
                select(func.count(Statistics.word_id)).where(Statistics.user_id == user_id)
            )
            words_studied = result.scalar_one() or 0

            # Слова с высоким уровнем освоения
            result = await session.execute(
                select(func.count(Statistics.word_id)).where(
                    Statistics.user_id == user_id, Statistics.mastered_level >= 3
                )
            )
            words_mastered = result.scalar_one() or 0

            # Статистика за сегодня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            result = await session.execute(
                select(
                    func.count(TrainingSession.id).label("today_sessions"),
                    func.sum(TrainingSession.total_questions).label("today_questions"),
                ).where(TrainingSession.user_id == user_id, TrainingSession.created_at >= today_start)
            )
            today_stats = result.first()
            today_sessions = today_stats.today_sessions or 0
            today_questions = today_stats.today_questions or 0
        except DatabaseError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            logger.error(f"Database error in statistics_menu: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при загрузке статистики. Попробуйте еще раз.")
            return
        except Exception as e:
            # Общая обработка остальных исключений
            logger.error(f"Unexpected error in statistics_menu: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла неожиданная ошибка. Попробуйте еще раз.")
            return

    text = (
        f"📊 *Моя статистика*\n\n"
        f"🎯 *Общая статистика:*\n"
        f"• Тренировок пройдено: {total_sessions}\n"
        f"• Всего вопросов: {total_questions}\n"
        f"• Правильных ответов: {total_correct}\n"
        f"• Средняя точность: {avg_accuracy:.1f}%\n\n"
        f"📚 *Словарь:*\n"
        f"• Изучено слов: {words_studied}\n"
        f"• Освоено слов (уровень 3+): {words_mastered}\n\n"
        f"📅 *Сегодня:*\n"
        f"• Тренировок: {today_sessions}\n"
        f"• Вопросов: {today_questions}"
    )

    keyboard = [
        [InlineKeyboardButton("📈 Детальная статистика", callback_data="statistics_detailed")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def statistics_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная статистика"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    async with async_session_maker() as session:
        try:
            # Последние тренировки
            result = await session.execute(
                select(TrainingSession)
                .where(TrainingSession.user_id == user_id)
                .order_by(desc(TrainingSession.created_at))
                .limit(5)
            )
            recent_sessions = result.scalars().all()

            # Слова, требующие повторения
            result = await session.execute(
                select(Statistics, Word)
                .join(Word, Statistics.word_id == Word.id)
                .where(Statistics.user_id == user_id, Statistics.mastered_level < 3)
                .order_by(Statistics.mastered_level)
                .limit(5)
            )
            words_to_review = result.all()
        except DatabaseError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            logger.error(f"Database error in statistics_detailed: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при загрузке детальной статистики. Попробуйте еще раз.")
            return
        except Exception as e:
            # Общая обработка остальных исключений
            logger.error(f"Unexpected error in statistics_detailed: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла неожиданная ошибка. Попробуйте еще раз.")
            return

        text = "📈 *Детальная статистика*\n\n"

        if recent_sessions:
            text += "🕐 *Последние тренировки:*\n"
            for session in recent_sessions:
                text += (
                    f"• {session.created_at.strftime('%d.%m %H:%M')} - "
                    f"{session.total_questions} вопросов, "
                    f"точность {session.accuracy:.1f}%\n"
                )
            text += "\n"

        if words_to_review:
            text += "📚 *Слова для повторения:*\n"
            for stats, word in words_to_review:
                level_emoji = "⭐" * stats.mastered_level + "⚪" * (5 - stats.mastered_level)
                text += f"• {level_emoji} {word.english_word} = {word.russian_translation}\n"
        else:
            text += "✅ Все слова хорошо изучены!\n"

    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data="statistics_menu")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
