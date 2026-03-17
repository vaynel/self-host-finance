"""add_parsing_strategies_table

Revision ID: baf61206be36
Revises: 573ef0a6d3d8
Create Date: 2026-03-17 22:57:20.323579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import JSONB
except Exception:  # pragma: no cover
    JSONB = sa.JSON  # type: ignore

# revision identifiers, used by Alembic.
revision: str = 'baf61206be36'
down_revision: Union[str, None] = '573ef0a6d3d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parsing_strategies",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="groq"),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("mapping", JSONB(), nullable=False),
        sa.Column("rules", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb") if JSONB is not sa.JSON else sa.text("'{}'")),
        sa.Column("header", JSONB(), nullable=True),
        sa.Column("examples", JSONB(), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_parsing_strategies_user_id", "parsing_strategies", ["user_id"])
    op.create_index("ix_parsing_strategies_fingerprint", "parsing_strategies", ["fingerprint"])
    op.create_index(
        "ix_parsing_strategies_user_fingerprint",
        "parsing_strategies",
        ["user_id", "fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_parsing_strategies_user_fingerprint", table_name="parsing_strategies")
    op.drop_index("ix_parsing_strategies_fingerprint", table_name="parsing_strategies")
    op.drop_index("ix_parsing_strategies_user_id", table_name="parsing_strategies")
    op.drop_table("parsing_strategies")
