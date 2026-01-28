"""Главный файл запуска бота"""

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import BOT_TOKEN
from bot.handlers import achievements, dictionary, start, statistics, training
from bot.utils.logger import setup_logger

# Настройка логирования
logger = setup_logger()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте еще раз или используйте /start"
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")


def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Проверьте файл .env")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start.start_command))

    # Регистрируем обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(start.main_menu_callback, pattern="^main_menu$"))

    # Обработчики тренировок
    application.add_handler(
        CallbackQueryHandler(training.training_start, pattern="^training_start$")
    )
    application.add_handler(
        CallbackQueryHandler(training.training_direction, pattern="^training_direction_")
    )
    application.add_handler(CallbackQueryHandler(training.handle_answer, pattern="^answer_"))
    application.add_handler(CallbackQueryHandler(training.next_question, pattern="^next_question$"))
    application.add_handler(CallbackQueryHandler(training.training_end, pattern="^training_end$"))

    # Обработчики словаря
    application.add_handler(
        CallbackQueryHandler(dictionary.dictionary_menu, pattern="^dictionary_menu$")
    )
    application.add_handler(
        CallbackQueryHandler(dictionary.dictionary_add_start, pattern="^dictionary_add$")
    )
    application.add_handler(
        CallbackQueryHandler(
            dictionary.dictionary_add_skip_example, pattern="^dictionary_add_skip_example$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(dictionary.dictionary_search, pattern="^dictionary_search$")
    )
    application.add_handler(
        CallbackQueryHandler(dictionary.dictionary_my_words, pattern="^dictionary_my_words$")
    )
    application.add_handler(
        CallbackQueryHandler(dictionary.dictionary_delete_start, pattern="^dictionary_delete$")
    )

    # Обработчики статистики
    application.add_handler(
        CallbackQueryHandler(statistics.statistics_menu, pattern="^statistics_menu$")
    )
    application.add_handler(
        CallbackQueryHandler(statistics.statistics_detailed, pattern="^statistics_detailed$")
    )

    # Обработчики достижений
    application.add_handler(
        CallbackQueryHandler(achievements.achievements_menu, pattern="^achievements_menu$")
    )

    # Обработчики текстовых сообщений (для словаря)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_state = context.user_data.get("dictionary_state")

    if user_state == "waiting_english":
        await dictionary.dictionary_add_english(update, context)
    elif user_state == "waiting_russian":
        await dictionary.dictionary_add_russian(update, context)
    elif user_state == "waiting_example":
        await dictionary.dictionary_add_example(update, context)
    elif user_state == "searching":
        await dictionary.dictionary_search_result(update, context)
    elif user_state == "deleting":
        await dictionary.dictionary_delete_word(update, context)
    else:
        # Если состояние не определено, предлагаем начать с /start
        if update.message:
            await update.message.reply_text(
                "Не понимаю команду. Используйте /start для начала работы."
            )


if __name__ == "__main__":
    main()
