"""Add missing SMS session enum values used by admin overview.

Revision ID: a1b2c3d4e5f6
Revises: b7c3d91e4a10
Create Date: 2026-09-29 11:15:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b7c3d91e4a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'PROCESSING'")
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'FAILED'")
    op.execute("ALTER TYPE sessionstatus ADD VALUE IF NOT EXISTS 'CANCELLED'")
    op.execute("ALTER TYPE sessiontype ADD VALUE IF NOT EXISTS 'WEATHER_ALERTS'")
    op.execute("ALTER TYPE sessiontype ADD VALUE IF NOT EXISTS 'DISEASE_ALERTS'")
    op.execute("ALTER TYPE sessiontype ADD VALUE IF NOT EXISTS 'MARKET_PRICES'")
    op.execute("ALTER TYPE sessiontype ADD VALUE IF NOT EXISTS 'PROFILE_UPDATE'")
    op.execute("ALTER TYPE sessiontype ADD VALUE IF NOT EXISTS 'SUBSCRIPTION'")


def downgrade() -> None:
    # Postgres cannot drop individual enum values safely.
    pass
