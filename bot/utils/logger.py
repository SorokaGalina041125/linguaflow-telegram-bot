"""Настройка логирования"""

import logging
from pathlib import Path

from bot.config import LOG_FILE, LOG_LEVEL


def setup_logger():
    """Настройка логирования в файл и консоль"""
    # Создаем директорию для логов, если её нет
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Настройка формата логирования
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Получаем уровень логирования
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Настройка root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Очистка существующих обработчиков
    logger.handlers.clear()

    # Обработчик для файла
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
