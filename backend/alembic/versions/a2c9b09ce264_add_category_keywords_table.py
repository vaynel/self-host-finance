"""add_category_keywords_table

Revision ID: a2c9b09ce264
Revises: 001
Create Date: 2026-03-17 08:29:36.179482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2c9b09ce264'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category_keywords",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("user_id", sa.String(50), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_category_keywords_user_id", "category_keywords", ["user_id"])
    op.create_index("ix_category_keywords_category", "category_keywords", ["category"])
    op.create_index("ix_category_keywords_keyword", "category_keywords", ["keyword"])
    op.create_index("ix_category_keywords_user_category", "category_keywords", ["user_id", "category"])


def downgrade() -> None:
    op.drop_index("ix_category_keywords_user_category", table_name="category_keywords")
    op.drop_index("ix_category_keywords_keyword", table_name="category_keywords")
    op.drop_index("ix_category_keywords_category", table_name="category_keywords")
    op.drop_index("ix_category_keywords_user_id", table_name="category_keywords")
    op.drop_table("category_keywords")
