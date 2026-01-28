"""Обработчики словаря"""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import DatabaseError, IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import MAX_EXAMPLE_LENGTH, MAX_TRANSLATION_LENGTH, MAX_WORD_LENGTH
from bot.database.database import async_session_maker
from bot.database.models import Category, User, Word
from bot.database.repository import get_user_by_telegram_id

# FIX: Добавлен logger для обработки ошибок транзакций (P0.1)
logger = logging.getLogger(__name__)


async def dictionary_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню словаря"""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    # Подсчитываем количество слов пользователя
    async with async_session_maker() as session:
        # FIX: Использование репозитория вместо дублированного кода (P1.1)
        user = await get_user_by_telegram_id(session, telegram_id)

        if not user:
            await query.edit_message_text("Ошибка: пользователь не найден.")
            return

        result = await session.execute(
            select(func.count(Word.id)).where(
                or_(
                    Word.user_id.is_(None),  # Общие слова
                    Word.user_id == user.id,  # Личные слова
                ),
                Word.is_public,
            )
        )
        total_words = result.scalar_one()

    keyboard = [
        [InlineKeyboardButton("➕ Добавить слово", callback_data="dictionary_add")],
        [InlineKeyboardButton("🔍 Поиск по словарю", callback_data="dictionary_search")],
        [InlineKeyboardButton("📋 Мои слова", callback_data="dictionary_my_words")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📚 *Мой словарь*\n\nВсего слов: {total_words}\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def dictionary_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления слова"""
    query = update.callback_query
    await query.answer()

    context.user_data["dictionary_state"] = "waiting_english"

    await query.edit_message_text(
        "➕ *Добавление нового слова*\n\nВведите английское слово:", parse_mode="Markdown"
    )


async def dictionary_add_english(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода английского слова"""
    english_word = update.message.text.strip()
    
    # FIX: Валидация формата и длины слова для предотвращения ошибок БД (P0.2, P1.3)
    if not english_word:
        await update.message.reply_text("❌ Слово не может быть пустым. Введите английское слово:")
        return
    
    # Проверка на строку, состоящую только из пробелов
    if not english_word.replace(" ", ""):
        await update.message.reply_text("❌ Слово не может состоять только из пробелов. Введите английское слово:")
        return
    
    if len(english_word) > MAX_WORD_LENGTH:
        await update.message.reply_text(
            f"❌ Слово слишком длинное (максимум {MAX_WORD_LENGTH} символов). "
            f"Введите более короткое слово:"
        )
        return
    
    context.user_data["new_word_english"] = english_word
    context.user_data["dictionary_state"] = "waiting_russian"

    await update.message.reply_text(
        f"✅ Английское слово: *{english_word}*\n\nТеперь введите русский перевод:",
        parse_mode="Markdown",
    )


async def dictionary_add_russian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода русского перевода"""
    russian_translation = update.message.text.strip()
    
    # FIX: Валидация формата и длины перевода для предотвращения ошибок БД (P0.2, P1.3)
    if not russian_translation:
        await update.message.reply_text("❌ Перевод не может быть пустым. Введите русский перевод:")
        return
    
    # Проверка на строку, состоящую только из пробелов
    if not russian_translation.replace(" ", ""):
        await update.message.reply_text("❌ Перевод не может состоять только из пробелов. Введите русский перевод:")
        return
    
    if len(russian_translation) > MAX_TRANSLATION_LENGTH:
        await update.message.reply_text(
            f"❌ Перевод слишком длинный (максимум {MAX_TRANSLATION_LENGTH} символов). "
            f"Введите более короткий перевод:"
        )
        return
    
    context.user_data["new_word_russian"] = russian_translation
    context.user_data["dictionary_state"] = "waiting_example"

    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустить пример", callback_data="dictionary_add_skip_example")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Русский перевод: *{russian_translation}*\n\n"
        "Введите пример использования (или пропустите):",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def dictionary_add_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода примера"""
    example = update.message.text.strip()
    
    # FIX: Валидация формата и длины примера для предотвращения ошибок БД (P0.2, P1.3)
    # Проверка на строку, состоящую только из пробелов (если не пустая)
    if example and not example.replace(" ", ""):
        await update.message.reply_text(
            "❌ Пример не может состоять только из пробелов. Введите пример или пропустите:"
        )
        return
    
    if len(example) > MAX_EXAMPLE_LENGTH:
        await update.message.reply_text(
            f"❌ Пример слишком длинный (максимум {MAX_EXAMPLE_LENGTH} символов). "
            f"Введите более короткий пример или пропустите:"
        )
        return
    
    await save_new_word(update, context, example if example else None)


async def dictionary_add_skip_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск примера"""
    query = update.callback_query
    await query.answer()

    await save_new_word(update, context, None)


async def save_new_word(update: Update, context: ContextTypes.DEFAULT_TYPE, example: str = None):
    """Сохранение нового слова в БД"""
    user_id = update.effective_user.id
    english_word = context.user_data.get("new_word_english")
    russian_translation = context.user_data.get("new_word_russian")

    # Определяем способ отправки ответа
    query = update.callback_query
    message = update.message if update.message else (query.message if query else None)

    if not english_word or not russian_translation:
        keyboard = [
            [InlineKeyboardButton("➕ Добавить слово заново", callback_data="dictionary_add")],
            [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if message:
            await message.reply_text(
                "Ошибка: не все данные введены. Попробуйте снова.", reply_markup=reply_markup
            )
        return

    async with async_session_maker() as session:
        try:
            # FIX: Использование репозитория вместо дублированного кода (P1.1)
            user = await get_user_by_telegram_id(session, user_id)

            if not user:
                keyboard = [
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if message:
                    await message.reply_text(
                        "Ошибка: пользователь не найден. Используйте /start", reply_markup=reply_markup
                    )
                return

            # Проверяем, не существует ли уже такое слово у пользователя
            result = await session.execute(
                select(Word).where(Word.english_word == english_word, Word.user_id == user.id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить другое слово", callback_data="dictionary_add")],
                    [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                text = f"⚠️ Слово *{english_word}* уже есть в вашем словаре!"

                if query:
                    await query.edit_message_text(
                        text, parse_mode="Markdown", reply_markup=reply_markup
                    )
                elif message:
                    await message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

                # Очищаем данные
                context.user_data.pop("dictionary_state", None)
                context.user_data.pop("new_word_english", None)
                context.user_data.pop("new_word_russian", None)
                return

            # Получаем категорию "Разработка ПО" по умолчанию (или первую доступную)
            result = await session.execute(
                select(Category).where(Category.category_name.like("%Разработка ПО%"))
            )
            category = result.scalar_one_or_none()

            if not category:
                result = await session.execute(select(Category).limit(1))
                category = result.scalar_one_or_none()

            if not category:
                keyboard = [
                    [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                if message:
                    await message.reply_text(
                        "Ошибка: категории не найдены. Проверьте инициализацию БД.",
                        reply_markup=reply_markup,
                    )
                return

            # Создаем новое слово
            new_word = Word(
                english_word=english_word,
                russian_translation=russian_translation,
                category_id=category.id,
                example_sentence=example,
                user_id=user.id,  # Личное слово пользователя
                is_public=False,  # Не видно другим пользователям
            )
            session.add(new_word)
            await session.commit()

            # Подсчитываем общее количество слов пользователя
            result = await session.execute(
                select(func.count(Word.id)).where(
                    or_(Word.user_id.is_(None), Word.user_id == user.id), Word.is_public
                )
            )
            total_words = result.scalar_one()
        except IntegrityError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Integrity error in save_new_word: {error_msg}", exc_info=True)
            keyboard = [
                [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Проверяем тип ошибки целостности
            if "unique_user_word" in error_msg.lower():
                error_text = "❌ Это слово уже существует в вашем словаре."
            else:
                error_text = "❌ Ошибка целостности данных. Попробуйте еще раз."
            if query:
                await query.edit_message_text(error_text, reply_markup=reply_markup)
            elif message:
                await message.reply_text(error_text, reply_markup=reply_markup)
            return
        except DatabaseError as e:
            # FIX: Добавлен rollback для обработки ошибок транзакций (P0.1)
            await session.rollback()
            logger.error(f"Database error in save_new_word: {e}", exc_info=True)
            keyboard = [
                [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            error_text = "❌ Произошла ошибка при сохранении слова. Попробуйте еще раз."
            if query:
                await query.edit_message_text(error_text, reply_markup=reply_markup)
            elif message:
                await message.reply_text(error_text, reply_markup=reply_markup)
            return
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in save_new_word: {e}", exc_info=True)
            keyboard = [
                [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            error_text = "❌ Произошла неожиданная ошибка. Попробуйте еще раз."
            if query:
                await query.edit_message_text(error_text, reply_markup=reply_markup)
            elif message:
                await message.reply_text(error_text, reply_markup=reply_markup)
            return

    # Очищаем данные
    context.user_data.pop("dictionary_state", None)
    context.user_data.pop("new_word_english", None)
    context.user_data.pop("new_word_russian", None)

    keyboard = [
        [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"✅ *Слово добавлено!*\n\n"
        f"*{english_word}* = {russian_translation}\n\n"
        f"📊 Всего слов в словаре: {total_words}"
    )

    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif message:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def dictionary_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск по словарю"""
    query = update.callback_query
    await query.answer()

    context.user_data["dictionary_state"] = "searching"

    await query.edit_message_text(
        "🔍 *Поиск по словарю*\n\nВведите слово для поиска (английское или русское):",
        parse_mode="Markdown",
    )


async def dictionary_search_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка результата поиска"""
    search_term = update.message.text.strip().lower()
    telegram_id = update.effective_user.id

    async with async_session_maker() as session:
        # FIX: Использование репозитория вместо дублированного кода (P1.1)
        user = await get_user_by_telegram_id(session, telegram_id)

        if not user:
            keyboard = [
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Ошибка: пользователь не найден.", reply_markup=reply_markup
            )
            return

        # Ищем слова
        result = await session.execute(
            select(Word)
            .where(
                or_(Word.user_id.is_(None), Word.user_id == user.id),
                or_(
                    Word.english_word.ilike(f"%{search_term}%"),
                    Word.russian_translation.ilike(f"%{search_term}%"),
                ),
            )
            .limit(10)
        )
        words = result.scalars().all()

        if not words:
            keyboard = [
                [InlineKeyboardButton("🔍 Поиск еще", callback_data="dictionary_search")],
                [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"❌ Слова, содержащие '{search_term}', не найдены.", reply_markup=reply_markup
            )
            return

        # Формируем список найденных слов
        words_list = []
        for word in words:
            words_list.append(f"• *{word.english_word}* = {word.russian_translation}")

        text = f"🔍 *Найдено слов: {len(words)}*\n\n" + "\n".join(words_list)

        keyboard = [
            [InlineKeyboardButton("🔍 Поиск еще", callback_data="dictionary_search")],
            [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    context.user_data.pop("dictionary_state", None)


async def dictionary_my_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать личные слова пользователя"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    async with async_session_maker() as session:
        # FIX: Использование репозитория вместо дублированного кода (P1.1)
        user = await get_user_by_telegram_id(session, user_id)

        if not user:
            await query.edit_message_text("Ошибка: пользователь не найден.")
            return

        # Получаем личные слова пользователя
        result = await session.execute(
            select(Word).where(Word.user_id == user.id).order_by(Word.english_word).limit(20)
        )
        words = result.scalars().all()

        if not words:
            await query.edit_message_text(
                "📚 *Мои слова*\n\nУ вас пока нет личных слов. Добавьте их через меню словаря!",
                parse_mode="Markdown",
            )
            return

        # Формируем список
        words_list = []
        for word in words:
            words_list.append(f"• *{word.english_word}* = {word.russian_translation}")

        text = f"📚 *Мои слова* ({len(words)})\n\n" + "\n".join(words_list)

        keyboard = [
            [InlineKeyboardButton("🗑️ Удалить слово", callback_data="dictionary_delete")],
            [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def dictionary_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления слова"""
    query = update.callback_query
    await query.answer()

    context.user_data["dictionary_state"] = "deleting"

    await query.edit_message_text(
        "🗑️ *Удаление слова*\n\nВведите английское слово, которое хотите удалить:",
        parse_mode="Markdown",
    )


async def dictionary_delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление слова"""
    english_word = update.message.text.strip()
    user_id = update.effective_user.id

    async with async_session_maker() as session:
        try:
            # FIX: Использование репозитория вместо дублированного кода (P1.1)
            user = await get_user_by_telegram_id(session, user_id)

            if not user:
                keyboard = [
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "Ошибка: пользователь не найден.", reply_markup=reply_markup
                )
                return

            # Ищем слово пользователя
            result = await session.execute(
                select(Word).where(Word.english_word == english_word, Word.user_id == user.id)
            )
            word = result.scalar_one_or_none()

            if not word:
                keyboard = [
                    [InlineKeyboardButton("🗑️ Удалить другое слово", callback_data="dictionary_delete")],
                    [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                f"❌ Слово *{english_word}* не найдено в вашем словаре.",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            return

            # Удаляем слово
            await session.delete(word)
            await session.commit()
        except DatabaseError as e:
            # FIX: Улучшена обработка специфичных исключений БД (P1.2)
            await session.rollback()
            logger.error(f"Database error in dictionary_delete_word: {e}", exc_info=True)
            keyboard = [
                [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ Произошла ошибка при удалении слова. Попробуйте еще раз.",
                reply_markup=reply_markup,
            )
            return
        except Exception as e:
            # Общая обработка остальных исключений
            await session.rollback()
            logger.error(f"Unexpected error in dictionary_delete_word: {e}", exc_info=True)
            keyboard = [
                [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ Произошла неожиданная ошибка. Попробуйте еще раз.",
                reply_markup=reply_markup,
            )
            return

    context.user_data.pop("dictionary_state", None)

    keyboard = [
        [InlineKeyboardButton("📚 Мой словарь", callback_data="dictionary_menu")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Слово *{english_word}* удалено из вашего словаря.",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
