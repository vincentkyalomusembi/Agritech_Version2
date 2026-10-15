"""Track recommendation SMS submissions and delivery callbacks.

Revision ID: 8d2f4a6c1b90
Revises: c4d6e8f0a2b4
Create Date: 2026-10-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8d2f4a6c1b90"
down_revision: Union[str, Sequence[str], None] = "c4d6e8f0a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_sms_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_phone", sa.String(length=30), nullable=False),
        sa.Column("provider_message_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="submitted"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_recommendation_sms_deliveries_recommendation_id", "recommendation_sms_deliveries", ["recommendation_id"])
    op.create_index("ix_recommendation_sms_deliveries_provider_id", "recommendation_sms_deliveries", ["provider_message_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_recommendation_sms_deliveries_provider_id", table_name="recommendation_sms_deliveries")
    op.drop_index("ix_recommendation_sms_deliveries_recommendation_id", table_name="recommendation_sms_deliveries")
    op.drop_table("recommendation_sms_deliveries")
