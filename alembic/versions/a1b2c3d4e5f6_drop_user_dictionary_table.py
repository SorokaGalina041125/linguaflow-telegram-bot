"""Drop user_dictionary table

Revision ID: a1b2c3d4e5f6
Revises: 70d4967f1b95
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "70d4967f1b95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем таблицу user_dictionary (не используется в проекте)
    op.drop_table("user_dictionary")


def downgrade() -> None:
    # Восстанавливаем таблицу user_dictionary при откате
    op.create_table(
        "user_dictionary",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("custom_translation", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"]),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word_id", name="unique_user_word_dict"),
    )
