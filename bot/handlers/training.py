"""Обработчики тренировок"""

import logging
import random

from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError, IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database.database import async_session_maker
from bot.database.models import Answer, Statistics, TrainingSession, User, Word
from bot.database.repository import get_user_by_telegram_id

# FIX: Добавлен logger для обработки ошибок транзакций (P0.1)
logger = logging.getLogger(__name__)


async def training_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало тренировки - выбор направления перевода"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 → 🇷🇺 EN→RU", callback_data="training_direction_en_ru"),
            InlineKeyboardButton("🇷🇺 → 🇬🇧 RU→EN", callback_data="training_direction_ru_en"),
        ],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🎯 *Выберите направление перевода:*\n\n"
        "• EN→RU: вам покажут английское слово, нужно выбрать русский перевод\n"
        "• RU→EN: вам покажут русское слово, нужно выбрать английский перевод",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def training_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления и начало тренировки"""
    query = update.callback_query
    await query.answer()

    direction = query.data.split("_")[-2:]  # ['en', 'ru'] или ['ru', 'en']
    direction_str = "_".join(direction)  # 'en_ru' или 'ru_en'

    # Сохраняем направление в контексте пользователя
    context.user_data["training_direction"] = direction_str

    # Создаем новую сессию тренировки
    user_id = query.from_user.id

    async with async_session_maker() as session:
        try:
            # FIX: Использование репозитория вместо дублированного кода (P1.1)
            user = await get_user_by_telegram_id(session, user_id)

            if not user:
                await query.edit_message_text("Ошибка: пользователь не найден. Используйте /start")
                return

            # Создаем сессию тренировки
            training_session = TrainingSession(
                user_id=user_id,
                session_type="multiple_choice",
                total_questions=0,
                correct_answers=0,
                accuracy=0.0,
            )
            session.add(training_session)
            await session.commit()
            await session.refresh(training_session)

            # Сохраняем ID сессии в контексте
            context.user_data["training_session_id"] = training_session.id
        except IntegrityError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            logger.error(f"Integrity error in training_direction: {e}", exc_info=True)
            await query.edit_message_text("❌ Ошибка целостности данных. Попробуйте еще раз.")
            return
        except DatabaseError as e:
            # FIX: Добавлен rollback для обработки ошибок транзакций (P0.1)
            await session.rollback()
            logger.error(f"Database error in training_direction: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при создании тренировки. Попробуйте еще раз.")
            return
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in training_direction: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла неожиданная ошибка. Попробуйте еще раз.")
            return

    # Начинаем тренировку
    await ask_question(update, context)


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Задать вопрос пользователю"""
    query = update.callback_query if update.callback_query else None
    telegram_id = update.effective_user.id
    direction = context.user_data.get("training_direction", "en_ru")

    async with async_session_maker() as session:
        try:
            # FIX: Использование репозитория вместо дублированного кода (P1.1)
            user = await get_user_by_telegram_id(session, telegram_id)

            if not user:
                text = "Ошибка: пользователь не найден. Используйте /start"
                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                if query:
                    await query.edit_message_text(text, reply_markup=reply_markup)
                elif update.message:
                    await update.message.reply_text(text, reply_markup=reply_markup)
                return

            # Получаем 4 случайных слова — лимит в запросе вместо загрузки 100 (экономия памяти и времени)
            result = await session.execute(
                select(Word)
                .where((Word.user_id.is_(None)) | (Word.user_id == user.id), Word.is_public)
                .order_by(func.random())
                .limit(4)
            )
            words = result.scalars().all()
        except DatabaseError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            logger.error(f"Database error in ask_question: {e}", exc_info=True)
            text = "❌ Произошла ошибка при загрузке слов. Попробуйте еще раз."
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(text, reply_markup=reply_markup)
            elif update.message:
                await update.message.reply_text(text, reply_markup=reply_markup)
            return
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in ask_question: {e}", exc_info=True)
            text = "❌ Произошла неожиданная ошибка. Попробуйте еще раз."
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(text, reply_markup=reply_markup)
            elif update.message:
                await update.message.reply_text(text, reply_markup=reply_markup)
            return

        if not words:
            text = "📚 *Словарь пуст*\n\nДобавьте слова в словарь, чтобы начать тренировку!"
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if query:
                await query.edit_message_text(
                    text, parse_mode="Markdown", reply_markup=reply_markup
                )
            elif update.message:
                await update.message.reply_text(
                    text, parse_mode="Markdown", reply_markup=reply_markup
                )
            return

        if len(words) < 2:
            text = "📚 *Мало слов для тренировки*\n\nДобавьте ещё слова (нужно минимум 2 разных)."
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query:
                await query.edit_message_text(
                    text, parse_mode="Markdown", reply_markup=reply_markup
                )
            elif update.message:
                await update.message.reply_text(
                    text, parse_mode="Markdown", reply_markup=reply_markup
                )
            return

        # Работаем с 4 (или меньшим) количеством слов: одно — правильный ответ, остальные — неправильные
        random.shuffle(words)
        correct_word = words[0]
        wrong_words = list(words[1:])
        # Добиваем до 3 неправильных вариантов дубликатами, если слов меньше 4
        while len(wrong_words) < 3:
            wrong_words.append(wrong_words[0] if wrong_words else correct_word)
        wrong_words = wrong_words[:3]

        # Формируем варианты ответов
        if direction == "en_ru":
            question_text = f"🇬🇧 *Переведите слово:*\n\n*{correct_word.english_word}*"
            correct_answer = correct_word.russian_translation
            options = [w.russian_translation for w in wrong_words] + [correct_answer]
        else:  # ru_en
            question_text = f"🇷🇺 *Переведите слово:*\n\n*{correct_word.russian_translation}*"
            correct_answer = correct_word.english_word
            options = [w.english_word for w in wrong_words] + [correct_answer]

        # Перемешиваем варианты
        random.shuffle(options)
        correct_index = options.index(correct_answer)

        # Сохраняем правильный ответ в контексте
        context.user_data["correct_word_id"] = correct_word.id
        context.user_data["correct_answer_index"] = correct_index

        # Создаем клавиатуру с вариантами
        keyboard = []
        for i, option in enumerate(options):
            keyboard.append(
                [InlineKeyboardButton(f"{chr(65 + i)}. {option}", callback_data=f"answer_{i}")]
            )
        keyboard.append(
            [InlineKeyboardButton("❌ Завершить тренировку", callback_data="training_end")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"{question_text}\n\nВыберите правильный вариант:"

        if query:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа пользователя"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    answer_index = int(query.data.split("_")[1])
    correct_index = context.user_data.get("correct_answer_index")
    correct_word_id = context.user_data.get("correct_word_id")
    session_id = context.user_data.get("training_session_id")

    # Проверяем наличие необходимых данных
    if correct_index is None or correct_word_id is None or session_id is None:
        await query.edit_message_text(
            "Ошибка: данные тренировки не найдены. Начните тренировку заново."
        )
        return

    is_correct = answer_index == correct_index

    async with async_session_maker() as session:
        try:
            # Получаем слово
            result = await session.execute(select(Word).where(Word.id == correct_word_id))
            word = result.scalar_one_or_none()

            if not word:
                await query.edit_message_text("Ошибка: слово не найдено")
                return

            # Обновляем сессию
            training_session = await session.get(TrainingSession, session_id)
            if not training_session:
                await query.edit_message_text("Ошибка: сессия тренировки не найдена.")
                return

            training_session.total_questions += 1
            if is_correct:
                training_session.correct_answers += 1
            training_session.accuracy = (
                training_session.correct_answers / training_session.total_questions * 100
            )

            # Сохраняем ответ
            answer = Answer(
                session_id=session_id,
                user_id=user_id,
                word_id=correct_word_id,
                question_type="multiple_choice",
                user_answer=str(answer_index),
                is_correct=is_correct,
            )
            session.add(answer)

            # Обновляем статистику
            stats_result = await session.execute(
                select(Statistics).where(
                    Statistics.user_id == user_id, Statistics.word_id == correct_word_id
                )
            )
            stats = stats_result.scalar_one_or_none()

            if not stats:
                stats = Statistics(
                    user_id=user_id, word_id=correct_word_id, mastered_level=0, next_review=None
                )
                session.add(stats)

            if is_correct:
                stats.mastered_level = min(stats.mastered_level + 1, 5)
            else:
                stats.mastered_level = max(stats.mastered_level - 1, 0)

            await session.commit()
        except IntegrityError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            logger.error(f"Integrity error in handle_answer: {e}", exc_info=True)
            await query.edit_message_text("❌ Ошибка целостности данных при сохранении ответа. Попробуйте еще раз.")
            return
        except DatabaseError as e:
            # FIX: Добавлен rollback для обработки ошибок транзакций (P0.1)
            await session.rollback()
            logger.error(f"Database error in handle_answer: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при сохранении ответа. Попробуйте еще раз.")
            return
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in handle_answer: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла неожиданная ошибка. Попробуйте еще раз.")
            return

        # Формируем ответ
        direction = context.user_data.get("training_direction", "en_ru")
        if direction == "en_ru":
            correct_text = f"✅ *Правильно!*\n\n*{word.english_word}* = {word.russian_translation}"
        else:
            correct_text = f"✅ *Правильно!*\n\n*{word.russian_translation}* = {word.english_word}"

        if not is_correct:
            if direction == "en_ru":
                correct_text = (
                    f"❌ *Неправильно*\n\n"
                    f"Правильный ответ: *{word.english_word}* = {word.russian_translation}"
                )
            else:
                correct_text = (
                    f"❌ *Неправильно*\n\n"
                    f"Правильный ответ: *{word.russian_translation}* = {word.english_word}"
                )

        if word.example_sentence:
            correct_text += f"\n\n💡 *Пример:*\n🇬🇧 {word.example_sentence}"
            if word.example_sentence_ru:
                correct_text += f"\n🇷🇺 {word.example_sentence_ru}"

        # Показываем результат и продолжаем
        keyboard = [[InlineKeyboardButton("➡️ Следующий вопрос", callback_data="next_question")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            correct_text, parse_mode="Markdown", reply_markup=reply_markup
        )


async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к следующему вопросу"""
    query = update.callback_query
    await query.answer()

    # Очищаем данные предыдущего вопроса
    context.user_data.pop("correct_answer_index", None)
    context.user_data.pop("correct_word_id", None)

    await ask_question(update, context)


async def training_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение тренировки"""
    query = update.callback_query
    await query.answer()

    session_id = context.user_data.get("training_session_id")

    async with async_session_maker() as session:
        try:
            if session_id:
                training_session = await session.get(TrainingSession, session_id)
            else:
                training_session = None

            if training_session:
                accuracy = training_session.accuracy
                total = training_session.total_questions
                correct = training_session.correct_answers

                text = (
                    f"🏁 *Тренировка завершена!*\n\n"
                    f"📊 *Результаты:*\n"
                    f"• Всего вопросов: {total}\n"
                    f"• Правильных ответов: {correct}\n"
                    f"• Точность: {accuracy:.1f}%"
                )
            else:
                text = "Тренировка завершена."
        except DatabaseError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            logger.error(f"Database error in training_end: {e}", exc_info=True)
            text = "Тренировка завершена."
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in training_end: {e}", exc_info=True)
            text = "Тренировка завершена."

    # Очищаем данные тренировки
    context.user_data.pop("training_session_id", None)
    context.user_data.pop("training_direction", None)
    context.user_data.pop("correct_answer_index", None)
    context.user_data.pop("correct_word_id", None)

    keyboard = [
        [InlineKeyboardButton("🎯 Начать новую тренировку", callback_data="training_start")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
