"""Outbreak alerts and thresholds, structured request symptoms, rainfall normals.

Revision ID: 20261019outb
Revises: 20261019vend
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261019outb"
down_revision: Union[str, Sequence[str], None] = "20261019vend"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("expert_requests", sa.Column("symptom_codes", sa.JSON(), nullable=True))
    op.add_column("expert_requests", sa.Column("urgency", sa.String(20), nullable=True))
    op.add_column("environmental_cache", sa.Column("rainfall_normal_mm", sa.Float(), nullable=True))

    op.create_table(
        "outbreak_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symptom_code", sa.String(60), nullable=False),
        sa.Column("issue_type", sa.String(20), nullable=False),
        sa.Column("subject_key", sa.String(60), nullable=True),
        sa.Column("center_lat", sa.Float(), nullable=False),
        sa.Column("center_lng", sa.Float(), nullable=False),
        sa.Column("radius_km", sa.Float(), nullable=False),
        sa.Column("message_en", sa.Text(), nullable=False),
        sa.Column("message_sw", sa.Text(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="sent"),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outbreak_alerts_status_expires", "outbreak_alerts", ["status", "expires_at"])

    op.create_table(
        "outbreak_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("minimum_count", sa.Integer(), nullable=False),
        sa.Column("cell_size_deg", sa.Float(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("outbreak_settings")
    op.drop_index("ix_outbreak_alerts_status_expires", table_name="outbreak_alerts")
    op.drop_table("outbreak_alerts")
    op.drop_column("environmental_cache", "rainfall_normal_mm")
    op.drop_column("expert_requests", "urgency")
    op.drop_column("expert_requests", "symptom_codes")
