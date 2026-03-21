"""add investment order and execution tables

Revision ID: f5967abe8824
Revises: 11d5fd789600
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.investment_order import InvestmentOrder, InvestmentExecution  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "f5967abe8824"
down_revision: Union[str, None] = "11d5fd789600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # investment_orders 테이블
    op.create_table(
        "investment_orders",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("broker_account_id", sa.String(length=50), sa.ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("price", sa.Numeric(15, 2), nullable=True),
        sa.Column("order_type", sa.String(length=20), nullable=False, server_default="limit"),
        sa.Column("broker_order_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("filled_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_investment_orders_user_id", "investment_orders", ["user_id"])
    op.create_index("ix_investment_orders_account_id", "investment_orders", ["account_id"])
    op.create_index("ix_investment_orders_broker_account_id", "investment_orders", ["broker_account_id"])
    op.create_index("ix_investment_orders_ticker", "investment_orders", ["ticker"])
    op.create_index("ix_investment_orders_broker_order_id", "investment_orders", ["broker_order_id"])
    op.create_index("ix_investment_orders_status", "investment_orders", ["status"])
    op.create_index("ix_investment_orders_user_account", "investment_orders", ["user_id", "account_id"])

    # investment_executions 테이블
    op.create_table(
        "investment_executions",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("order_id", sa.String(50), sa.ForeignKey("investment_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("broker_execution_id", sa.String(100), nullable=True),
        sa.Column("executed_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("executed_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("fee", sa.Numeric(15, 2), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("settled", sa.String(10), nullable=False, server_default="no"),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_investment_executions_order_id", "investment_executions", ["order_id"])
    op.create_index("ix_investment_executions_user_id", "investment_executions", ["user_id"])
    op.create_index("ix_investment_executions_broker_execution_id", "investment_executions", ["broker_execution_id"], unique=True)
    op.create_index("ix_investment_executions_settled", "investment_executions", ["settled"])


def downgrade() -> None:
    op.drop_index("ix_investment_executions_settled", table_name="investment_executions")
    op.drop_index("ix_investment_executions_broker_execution_id", table_name="investment_executions")
    op.drop_index("ix_investment_executions_user_id", table_name="investment_executions")
    op.drop_index("ix_investment_executions_order_id", table_name="investment_executions")
    op.drop_table("investment_executions")

    op.drop_index("ix_investment_orders_user_account", table_name="investment_orders")
    op.drop_index("ix_investment_orders_status", table_name="investment_orders")
    op.drop_index("ix_investment_orders_broker_order_id", table_name="investment_orders")
    op.drop_index("ix_investment_orders_ticker", table_name="investment_orders")
    op.drop_index("ix_investment_orders_broker_account_id", table_name="investment_orders")
    op.drop_index("ix_investment_orders_account_id", table_name="investment_orders")
    op.drop_index("ix_investment_orders_user_id", table_name="investment_orders")
    op.drop_table("investment_orders")
