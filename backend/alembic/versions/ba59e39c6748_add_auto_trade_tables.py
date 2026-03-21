"""add auto trade tables

Revision ID: ba59e39c6748
Revises: f5967abe8824
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.auto_trade import AutoTradeRule, AutoTradeRunLog  # noqa: F401


revision: str = "ba59e39c6748"
down_revision: Union[str, None] = "f5967abe8824"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auto_trade_rules",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("target_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("stop_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("order_type", sa.String(length=20), nullable=False, server_default="limit"),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("limit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("cooldown_seconds", sa.String(length=20), nullable=False, server_default="300"),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auto_trade_rules_user_id", "auto_trade_rules", ["user_id"])
    op.create_index("ix_auto_trade_rules_account_id", "auto_trade_rules", ["account_id"])
    op.create_index("ix_auto_trade_rules_ticker", "auto_trade_rules", ["ticker"])
    op.create_index(
        "ix_auto_trade_rules_user_account_enabled",
        "auto_trade_rules",
        ["user_id", "account_id", "enabled"],
    )

    op.create_table(
        "auto_trade_run_logs",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(length=50), sa.ForeignKey("auto_trade_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("order_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auto_trade_run_logs_user_id", "auto_trade_run_logs", ["user_id"])
    op.create_index("ix_auto_trade_run_logs_rule_id", "auto_trade_run_logs", ["rule_id"])
    op.create_index("ix_auto_trade_run_logs_account_id", "auto_trade_run_logs", ["account_id"])
    op.create_index("ix_auto_trade_run_logs_ticker", "auto_trade_run_logs", ["ticker"])
    op.create_index("ix_auto_trade_run_logs_rule_created", "auto_trade_run_logs", ["rule_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_auto_trade_run_logs_rule_created", table_name="auto_trade_run_logs")
    op.drop_index("ix_auto_trade_run_logs_ticker", table_name="auto_trade_run_logs")
    op.drop_index("ix_auto_trade_run_logs_account_id", table_name="auto_trade_run_logs")
    op.drop_index("ix_auto_trade_run_logs_rule_id", table_name="auto_trade_run_logs")
    op.drop_index("ix_auto_trade_run_logs_user_id", table_name="auto_trade_run_logs")
    op.drop_table("auto_trade_run_logs")

    op.drop_index("ix_auto_trade_rules_user_account_enabled", table_name="auto_trade_rules")
    op.drop_index("ix_auto_trade_rules_ticker", table_name="auto_trade_rules")
    op.drop_index("ix_auto_trade_rules_account_id", table_name="auto_trade_rules")
    op.drop_index("ix_auto_trade_rules_user_id", table_name="auto_trade_rules")
    op.drop_table("auto_trade_rules")
