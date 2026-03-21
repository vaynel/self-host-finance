"""Expand broker_tokens token column sizes to avoid truncation errors."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c8b0d2f8e8aa"
down_revision: Union[str, None] = "b9d40aa1b795"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "broker_tokens",
        "encrypted_access_token",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "broker_tokens",
        "encrypted_refresh_token",
        existing_type=sa.String(length=512),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "broker_tokens",
        "encrypted_access_token",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    op.alter_column(
        "broker_tokens",
        "encrypted_refresh_token",
        existing_type=sa.Text(),
        type_=sa.String(length=512),
        existing_nullable=True,
    )

