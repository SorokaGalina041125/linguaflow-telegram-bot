"""Репозиторий для общих операций с базой данных

FIX: Создан репозиторий для устранения дублирования кода получения пользователя (P1.1)
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    """Получить пользователя по telegram_id
    
    Args:
        session: Сессия БД
        telegram_id: ID пользователя в Telegram
        
    Returns:
        User объект или None, если пользователь не найден
    """
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()
