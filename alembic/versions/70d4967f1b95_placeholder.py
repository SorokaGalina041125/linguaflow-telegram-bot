"""Placeholder revision (пустая миграция восстановлена для совместимости с БД)

Revision ID: 70d4967f1b95
Revises: 0b885dcfc8f0
Create Date: 2026-01-28

Если в БД уже записана эта ревизия — файл нужен, чтобы Alembic мог её найти.
Никаких изменений схемы не вносит.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "70d4967f1b95"
down_revision: Union[str, None] = "0b885dcfc8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
