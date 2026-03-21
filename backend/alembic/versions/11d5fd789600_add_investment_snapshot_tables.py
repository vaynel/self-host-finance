"""add investment snapshot tables

Revision ID: 11d5fd789600
Revises: b9d40aa1b795
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.investment_snapshot import InvestmentHoldingSnapshot, InvestmentCashSnapshot  # noqa: F401


revision: str = "11d5fd789600"
down_revision: Union[str, None] = "b9d40aa1b795"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investment_holding_snapshot",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("average_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("current_price", sa.Numeric(15, 4), nullable=False),
        sa.Column("valuation", sa.Numeric(18, 2), nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_investment_holding_snapshot_user_account", "investment_holding_snapshot", ["user_id", "account_id"])
    op.create_index("ix_investment_holding_snapshot_user_ticker", "investment_holding_snapshot", ["user_id", "ticker"])

    op.create_table(
        "investment_cash_snapshot",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("orderable_cash", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="KRW"),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_investment_cash_snapshot_user_account", "investment_cash_snapshot", ["user_id", "account_id"])


def downgrade() -> None:
    op.drop_index("ix_investment_cash_snapshot_user_account", table_name="investment_cash_snapshot")
    op.drop_table("investment_cash_snapshot")

    op.drop_index("ix_investment_holding_snapshot_user_ticker", table_name="investment_holding_snapshot")
    op.drop_index("ix_investment_holding_snapshot_user_account", table_name="investment_holding_snapshot")
    op.drop_table("investment_holding_snapshot")
