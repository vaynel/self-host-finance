"""placeholder for missing revision referenced by DB

Revision ID: i9j0k1l2m3n4
Revises: g7h8i9j0k1l2
Create Date: 2026-03-26

This repository previously had a migration with revision id `i9j0k1l2m3n4`.
Some databases were stamped to that revision, but the file went missing.

The schema changes from that revision are already present in those databases,
so this migration is intentionally a no-op to restore Alembic continuity.
"""

from typing import Sequence, Union

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, tuple[str, ...], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # no-op (placeholder)
    pass


def downgrade() -> None:
    # no-op (placeholder)
    pass

