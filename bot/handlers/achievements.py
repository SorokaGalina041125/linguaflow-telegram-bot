"""Обработчики достижений"""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError, IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database.database import async_session_maker
from bot.database.models import (
    Achievement,
    Statistics,
    TrainingSession,
    User,
    UserAchievement,
    Word,
)
from bot.database.repository import get_user_by_telegram_id

# FIX: Добавлен logger для обработки ошибок транзакций (P0.1)
logger = logging.getLogger(__name__)


async def achievements_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню достижений"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    async with async_session_maker() as session:
        # FIX: Использование репозитория вместо дублированного кода (P1.1)
        user = await get_user_by_telegram_id(session, user_id)

        if not user:
            await query.edit_message_text("Ошибка: пользователь не найден.")
            return

        # Получаем все достижения
        result = await session.execute(select(Achievement))
        all_achievements = result.scalars().all()

        # Получаем разблокированные достижения пользователя
        result = await session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        unlocked_achievements = {ua.achievement_id for ua in result.scalars().all()}

        # Подсчитываем статистику для проверки достижений
        await check_achievements(session, user_id)

        # Формируем список достижений
        unlocked_count = len(unlocked_achievements)
        total_count = len(all_achievements)

        text = "⭐ *Достижения*\n\n"
        text += f"Разблокировано: {unlocked_count}/{total_count}\n\n"

        for achievement in all_achievements:
            if achievement.id in unlocked_achievements:
                text += f"✅ {achievement.icon} *{achievement.name}*\n"
                text += f"   {achievement.description}\n\n"
            else:
                text += f"🔒 {achievement.icon} *{achievement.name}*\n"
                text += f"   {achievement.description}\n\n"

    keyboard = [
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def check_achievements(session, user_id: int):
    """Проверка и разблокировка достижений"""
    # FIX: Использование репозитория вместо дублированного кода (P1.1)
    user = await get_user_by_telegram_id(session, user_id)

    if not user:
        return

    # Получаем все достижения
    result = await session.execute(select(Achievement))
    all_achievements = result.scalars().all()

    # Получаем уже разблокированные достижения
    result = await session.execute(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
    )
    unlocked_ids = {ua.achievement_id for ua in result.scalars().all()}

    for achievement in all_achievements:
        if achievement.id in unlocked_ids:
            continue

        condition = achievement.condition
        if not condition or not isinstance(condition, dict):
            continue

        condition_type = condition.get("type")
        if not condition_type:
            continue

        unlocked = False

        if condition_type == "first_training":
            # Проверяем, была ли хотя бы одна тренировка
            result = await session.execute(
                select(func.count(TrainingSession.id)).where(TrainingSession.user_id == user_id)
            )
            count = result.scalar_one() or 0
            unlocked = count > 0

        elif condition_type == "words_added":
            # Проверяем количество добавленных слов
            required_count = condition.get("count", 10)
            result = await session.execute(
                select(func.count(Word.id)).where(Word.user_id == user.id)
            )
            count = result.scalar_one() or 0
            unlocked = count >= required_count

        elif condition_type == "accuracy":
            # Проверяем точность в последней тренировке
            threshold = condition.get("threshold", 90)
            result = await session.execute(
                select(TrainingSession)
                .where(TrainingSession.user_id == user_id)
                .order_by(TrainingSession.created_at.desc())
                .limit(1)
            )
            last_session = result.scalar_one_or_none()
            if last_session and last_session.accuracy >= threshold:
                unlocked = True

        elif condition_type == "words_mastered":
            # Проверяем количество освоенных слов
            required_count = condition.get("count", 100)
            result = await session.execute(
                select(func.count(Statistics.word_id)).where(
                    Statistics.user_id == user_id, Statistics.mastered_level >= 3
                )
            )
            count = result.scalar_one() or 0
            unlocked = count >= required_count

        if unlocked:
            # Разблокируем достижение
            user_achievement = UserAchievement(
                user_id=user_id, achievement_id=achievement.id, progress={}
            )
            session.add(user_achievement)

    try:
        await session.commit()
    except IntegrityError as e:
        # FIX: Улучшена обработка специфичных исключений БД (P1.2)
        await session.rollback()
        logger.error(f"Integrity error in check_achievements: {e}", exc_info=True)
    except DatabaseError as e:
        # FIX: Добавлен rollback для обработки ошибок транзакций (P0.1)
        await session.rollback()
        logger.error(f"Database error in check_achievements: {e}", exc_info=True)
    except Exception as e:
        # Общая обработка остальных исключений
        await session.rollback()
        logger.error(f"Unexpected error in check_achievements: {e}", exc_info=True)
