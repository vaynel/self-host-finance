"""add discord webhook (encrypted) to user_settings

Revision ID: g7h8i9j0k1l2
Revises: ba59e39c6748, e1d3c9b3f0a1
Create Date: 2026-03-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, tuple[str, ...], None] = ("ba59e39c6748", "e1d3c9b3f0a1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("discord_webhook_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_settings", "discord_webhook_encrypted")
