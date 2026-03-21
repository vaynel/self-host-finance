"""add broker accounts table

Revision ID: beca3f5b9b0d
Revises: c7d9c2f1e3ab
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.broker_account import BrokerAccount  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "beca3f5b9b0d"
down_revision: Union[str, None] = "c7d9c2f1e3ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_accounts",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(length=50),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("broker_type", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("broker_account_no_masked", sa.String(length=100), nullable=True),
        sa.Column("product_code", sa.String(length=50), nullable=True),
        sa.Column("is_mock", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("api_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("auto_trade_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_balance_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_price_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_broker_accounts_account_id", "broker_accounts", ["account_id"])
    op.create_index("ix_broker_accounts_broker_type", "broker_accounts", ["broker_type"])


def downgrade() -> None:
    op.drop_index("ix_broker_accounts_broker_type", table_name="broker_accounts")
    op.drop_index("ix_broker_accounts_account_id", table_name="broker_accounts")
    op.drop_table("broker_accounts")
