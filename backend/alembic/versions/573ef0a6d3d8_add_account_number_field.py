"""add_account_number_field

Revision ID: 573ef0a6d3d8
Revises: a2c9b09ce264
Create Date: 2026-03-17 08:36:35.160917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '573ef0a6d3d8'
down_revision: Union[str, None] = 'a2c9b09ce264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("account_number", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "account_number")
