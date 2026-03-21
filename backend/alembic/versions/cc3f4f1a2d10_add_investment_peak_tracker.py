"""add investment_peak_tracker table

Revision ID: cc3f4f1a2d10
Revises: c8b0d2f8e8aa
Create Date: 2026-03-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "cc3f4f1a2d10"
down_revision: Union[str, None] = "c8b0d2f8e8aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investment_peak_tracker",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=50), nullable=False),
        sa.Column("peak_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_peak_user_account_ticker", "investment_peak_tracker", ["user_id", "account_id", "ticker"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_peak_user_account_ticker", table_name="investment_peak_tracker")
    op.drop_table("investment_peak_tracker")

