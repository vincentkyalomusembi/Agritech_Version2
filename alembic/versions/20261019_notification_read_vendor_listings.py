"""Notification read state, vendor listing fields and vendor engagement events.

Revision ID: 20261019vend
Revises: 20261016geo
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261019vend"
down_revision: Union[str, Sequence[str], None] = "20261016geo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_notifications_farmer_unread", "notifications", ["farmer_id", "read_at"])

    op.add_column("vendors", sa.Column("whatsapp_phone", sa.String(20), nullable=True))
    op.add_column("vendors", sa.Column("certified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("vendors", sa.Column("sponsored", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("vendors", sa.Column("categories", sa.JSON(), nullable=True))
    op.add_column("vendor_products", sa.Column("category", sa.String(30), nullable=True))

    op.create_table(
        "vendor_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("farmer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("farmers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vendor_events_vendor_type", "vendor_events", ["vendor_id", "event_type"])


def downgrade() -> None:
    op.drop_index("ix_vendor_events_vendor_type", table_name="vendor_events")
    op.drop_table("vendor_events")
    op.drop_column("vendor_products", "category")
    for column in ("categories", "sponsored", "certified", "whatsapp_phone"):
        op.drop_column("vendors", column)
    op.drop_index("ix_notifications_farmer_unread", table_name="notifications")
    op.drop_column("notifications", "read_at")
