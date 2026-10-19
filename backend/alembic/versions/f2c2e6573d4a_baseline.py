"""baseline

Revision ID: f2c2e6573d4a
Revises: 
Create Date: 2026-10-19 02:47:20.509237

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'f2c2e6573d4a'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
