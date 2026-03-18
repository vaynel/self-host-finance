"""add investment price tables

Revision ID: c7d9c2f1e3ab
Revises: 9c1b2f5b7a12
Create Date: 2026-03-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.investment_price import InvestmentPriceLatest, InvestmentPriceDaily  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "c7d9c2f1e3ab"
down_revision: Union[str, None] = "9c1b2f5b7a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investment_price_latest",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticker", sa.String(length=20), nullable=False, index=True),
        sa.Column("price", sa.Numeric(15, 4), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_investment_price_latest_user_ticker", "investment_price_latest", ["user_id", "ticker"])

    op.create_table(
        "investment_price_daily",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticker", sa.String(length=20), nullable=False, index=True),
        sa.Column("trade_date", sa.Date(), nullable=False, index=True),
        sa.Column("close", sa.Numeric(15, 4), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_investment_price_daily_user_ticker_date",
        "investment_price_daily",
        ["user_id", "ticker", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_investment_price_daily_user_ticker_date", table_name="investment_price_daily")
    op.drop_table("investment_price_daily")

    op.drop_index("ix_investment_price_latest_user_ticker", table_name="investment_price_latest")
    op.drop_table("investment_price_latest")

