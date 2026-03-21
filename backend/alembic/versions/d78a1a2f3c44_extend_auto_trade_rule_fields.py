"""extend auto_trade_rules with trigger/action fields

Revision ID: d78a1a2f3c44
Revises: cc3f4f1a2d10
Create Date: 2026-03-20
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d78a1a2f3c44"
down_revision: Union[str, None] = "cc3f4f1a2d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("auto_trade_rules", sa.Column("trigger_kind", sa.String(length=20), nullable=False, server_default="cost_drop"))
    op.add_column("auto_trade_rules", sa.Column("trigger_percent", sa.Numeric(6, 2), nullable=False, server_default="0"))
    op.add_column("auto_trade_rules", sa.Column("action_mode", sa.String(length=20), nullable=False, server_default="alert_only"))
    # remove server_default to clean schema
    with op.batch_alter_table("auto_trade_rules") as batch_op:
        batch_op.alter_column("trigger_kind", server_default=None)
        batch_op.alter_column("trigger_percent", server_default=None)
        batch_op.alter_column("action_mode", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("auto_trade_rules") as batch_op:
        batch_op.drop_column("action_mode")
        batch_op.drop_column("trigger_percent")
        batch_op.drop_column("trigger_kind")

