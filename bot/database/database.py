"""Настройка подключения к базе данных"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from bot.config import DATABASE_URL

# FIX: Настроен пул соединений для предотвращения исчерпания соединений при высокой нагрузке (P0.4)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,           # Размер пула соединений
    max_overflow=20,       # Максимальное переполнение пула
    pool_pre_ping=True,     # Проверка соединений перед использованием
    pool_recycle=3600,      # Переиспользование соединений (1 час)
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Базовый класс для моделей
Base = declarative_base()

# FIX: Удалена неиспользуемая функция get_session() (P0.5)
# Все обработчики используют async_session_maker() напрямую через async with
