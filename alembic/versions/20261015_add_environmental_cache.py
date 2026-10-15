"""Add daily environmental cache for regional GEE values.

Revision ID: 20261015env
Revises: 8d2f4a6c1b90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261015env"
down_revision: Union[str, Sequence[str], None] = "8d2f4a6c1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "environmental_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(length=300), nullable=False),
        sa.Column("region_type", sa.String(length=20), nullable=False),
        sa.Column("region_name", sa.String(length=150), nullable=False),
        sa.Column("county_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counties.id", ondelete="SET NULL")),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("rainfall_mm", sa.Float()),
        sa.Column("rainfall_status", sa.String(length=30)),
        sa.Column("ndvi", sa.JSON()),
        sa.Column("ndvi_trend", sa.JSON()),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cache_key", name="uq_environmental_cache_key"),
    )
    op.create_index("ix_environmental_cache_cache_key", "environmental_cache", ["cache_key"])
    op.create_index("ix_environmental_cache_region_type", "environmental_cache", ["region_type"])
    op.create_index("ix_environmental_cache_county_id", "environmental_cache", ["county_id"])
    op.create_index("ix_environmental_cache_observed_on", "environmental_cache", ["observed_on"])


def downgrade() -> None:
    op.drop_index("ix_environmental_cache_observed_on", table_name="environmental_cache")
    op.drop_index("ix_environmental_cache_county_id", table_name="environmental_cache")
    op.drop_index("ix_environmental_cache_region_type", table_name="environmental_cache")
    op.drop_index("ix_environmental_cache_cache_key", table_name="environmental_cache")
    op.drop_table("environmental_cache")