"""add broker tokens table

Revision ID: b9d40aa1b795
Revises: beca3f5b9b0d
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.broker_token import BrokerToken  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "b9d40aa1b795"
down_revision: Union[str, None] = "beca3f5b9b0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_tokens",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column(
            "broker_account_id",
            sa.String(length=50),
            sa.ForeignKey("broker_accounts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encrypted_access_token", sa.String(length=512), nullable=False),
        sa.Column("encrypted_refresh_token", sa.String(length=512), nullable=True),
        sa.Column("token_type", sa.String(length=20), nullable=False, server_default="Bearer"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("refresh_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_broker_tokens_broker_account_id", "broker_tokens", ["broker_account_id"])


def downgrade() -> None:
    op.drop_index("ix_broker_tokens_broker_account_id", table_name="broker_tokens")
    op.drop_table("broker_tokens")
