"""Add structured recommendation cards and managed expert offers.

Revision ID: c4d6e8f0a2b4
Revises: 91c2e4a6b8d0
Create Date: 2026-10-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4d6e8f0a2b4"
down_revision: Union[str, Sequence[str], None] = "91c2e4a6b8d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recommendations", sa.Column("recommendation_data", postgresql.JSONB(), nullable=True))
    op.add_column("recommendations", sa.Column("crop_variety_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crop_varieties.id", ondelete="SET NULL"), nullable=True))
    op.add_column("recommendations", sa.Column("livestock_breed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("livestock_breeds.id", ondelete="SET NULL"), nullable=True))
    op.add_column("recommendations", sa.Column("vendor_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendor_products.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_recommendations_crop_variety_id", "recommendations", ["crop_variety_id"])
    op.create_index("ix_recommendations_livestock_breed_id", "recommendations", ["livestock_breed_id"])
    op.create_index("ix_recommendations_vendor_product_id", "recommendations", ["vendor_product_id"])
    op.add_column("experts", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("experts", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("experts", sa.Column("contact_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("expert_requests", "expert_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column("expert_requests", sa.Column("request_code", sa.String(12), nullable=True))
    op.add_column("expert_requests", sa.Column("farmer_resolution", sa.String(20), nullable=True))
    op.add_column("expert_requests", sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_expert_requests_source_session_id", "expert_requests", ["source_session_id"], unique=True)
    op.execute("UPDATE expert_requests SET request_code = 'ER-' || upper(substr(replace(id::text, '-', ''), 1, 8)) WHERE request_code IS NULL")
    op.alter_column("expert_requests", "request_code", nullable=False)
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'OFFERED'")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'UNASSIGNED'")
    op.execute("ALTER TYPE requeststatus ADD VALUE IF NOT EXISTS 'ESCALATED'")
    op.create_index("ix_expert_requests_request_code", "expert_requests", ["request_code"], unique=True)
    op.create_table(
        "expert_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("expert_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="offered"),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("response_seconds", sa.Integer()),
        sa.Column("response_note", sa.String(240)),
        sa.UniqueConstraint("request_id", "expert_id", name="uq_expert_offer_request_expert"),
    )
    op.create_index("ix_expert_offers_request_id", "expert_offers", ["request_id"])
    op.create_index("ix_expert_offers_expert_id", "expert_offers", ["expert_id"])
    op.create_index("ix_expert_offers_status_expires", "expert_offers", ["status", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_expert_offers_status_expires", table_name="expert_offers")
    op.drop_index("ix_expert_offers_expert_id", table_name="expert_offers")
    op.drop_index("ix_expert_offers_request_id", table_name="expert_offers")
    op.drop_table("expert_offers")
    op.drop_index("ix_expert_requests_request_code", table_name="expert_requests")
    op.drop_index("ix_expert_requests_source_session_id", table_name="expert_requests")
    op.drop_column("expert_requests", "source_session_id")
    op.drop_column("expert_requests", "farmer_resolution")
    op.drop_column("expert_requests", "request_code")
    op.alter_column("expert_requests", "expert_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_column("experts", "longitude")
    op.drop_column("experts", "latitude")
    op.drop_column("experts", "contact_verified")
    op.drop_column("recommendations", "recommendation_data")
    op.drop_index("ix_recommendations_vendor_product_id", table_name="recommendations")
    op.drop_index("ix_recommendations_livestock_breed_id", table_name="recommendations")
    op.drop_index("ix_recommendations_crop_variety_id", table_name="recommendations")
    op.drop_column("recommendations", "vendor_product_id")
    op.drop_column("recommendations", "livestock_breed_id")
    op.drop_column("recommendations", "crop_variety_id")
