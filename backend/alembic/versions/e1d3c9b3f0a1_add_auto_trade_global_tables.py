"""add auto_trade_global_rules and logs tables.

Revision ID: e1d3c9b3f0a1
Revises: d78a1a2f3c44
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e1d3c9b3f0a1"
down_revision: Union[str, None] = "d78a1a2f3c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auto_trade_global_rules",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trigger_kind", sa.String(length=20), nullable=False, server_default="cost_drop"),
        sa.Column("trigger_percent", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("action_mode", sa.String(length=20), nullable=False, server_default="alert_only"),
        sa.Column("order_type", sa.String(length=20), nullable=False, server_default="limit"),
        sa.Column("sell_quantity_ratio", sa.Numeric(10, 4), nullable=False, server_default="1"),
        sa.Column("limit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("cooldown_seconds", sa.String(length=20), nullable=False, server_default="300"),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auto_trade_global_rules_user_account_enabled", "auto_trade_global_rules", ["user_id", "account_id", "enabled"])

    op.create_table(
        "auto_trade_global_run_logs",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("user_id", sa.String(length=50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rule_id", sa.String(length=50), sa.ForeignKey("auto_trade_global_rules.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("account_id", sa.String(length=50), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticker", sa.String(length=20), nullable=False, index=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("order_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auto_trade_global_run_logs_rule_created", "auto_trade_global_run_logs", ["rule_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_auto_trade_global_run_logs_rule_created", table_name="auto_trade_global_run_logs")
    op.drop_table("auto_trade_global_run_logs")
    op.drop_index("ix_auto_trade_global_rules_user_account_enabled", table_name="auto_trade_global_rules")
    op.drop_table("auto_trade_global_rules")

