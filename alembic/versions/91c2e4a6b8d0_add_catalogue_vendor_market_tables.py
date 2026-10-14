"""Add agricultural catalogue, vendors, vendor products, and markets.

Revision ID: 91c2e4a6b8d0
Revises: f2a6c8d0e4b1
Create Date: 2026-10-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "91c2e4a6b8d0"
down_revision: Union[str, Sequence[str], None] = "f2a6c8d0e4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crop_varieties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("crop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("maintainer", sa.String(150)),
        sa.Column("altitude_min_m", sa.Integer()), sa.Column("altitude_max_m", sa.Integer()),
        sa.Column("rainfall_min_mm", sa.Integer()), sa.Column("rainfall_max_mm", sa.Integer()),
        sa.Column("maturity_days_min", sa.Integer()), sa.Column("maturity_days_max", sa.Integer()),
        sa.Column("risk_attributes", sa.Text()), sa.Column("adapted_regions", sa.Text()),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("source_checked_on", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("crop_id", "name", name="uq_crop_variety_name"),
    )
    op.create_index("ix_crop_varieties_crop_id", "crop_varieties", ["crop_id"])

    op.create_table(
        "livestock_breeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("livestock_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("livestock.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("altitude_min_m", sa.Integer()), sa.Column("altitude_max_m", sa.Integer()),
        sa.Column("rainfall_min_mm", sa.Integer()), sa.Column("rainfall_max_mm", sa.Integer()),
        sa.Column("maturity_days_min", sa.Integer()), sa.Column("maturity_days_max", sa.Integer()),
        sa.Column("risk_attributes", sa.Text()), sa.Column("adapted_regions", sa.Text()),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("source_checked_on", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("livestock_id", "name", name="uq_livestock_breed_name"),
    )
    op.create_index("ix_livestock_breeds_livestock_id", "livestock_breeds", ["livestock_id"])

    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("county_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counties.id"), nullable=False),
        sa.Column("address", sa.Text(), nullable=False), sa.Column("sub_county", sa.String(120)), sa.Column("ward", sa.String(120)),
        sa.Column("latitude", sa.Float()), sa.Column("longitude", sa.Float()),
        sa.Column("contact_phone", sa.String(40)), sa.Column("contact_email", sa.String(254)), sa.Column("opening_hours", sa.Text()),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("source_checked_on", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("name", "address", name="uq_vendor_name_address"),
    )
    op.create_index("ix_vendors_name", "vendors", ["name"])
    op.create_index("ix_vendors_county_id", "vendors", ["county_id"])

    op.create_table(
        "vendor_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crop_variety_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crop_varieties.id", ondelete="SET NULL")),
        sa.Column("livestock_breed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("livestock_breeds.id", ondelete="SET NULL")),
        sa.Column("product_name", sa.String(180), nullable=False), sa.Column("price_kes", sa.Numeric(12, 2)),
        sa.Column("unit", sa.String(60), nullable=False), sa.Column("stock_quantity", sa.Float()),
        sa.Column("price_checked_on", sa.Date()), sa.Column("stock_checked_on", sa.Date()), sa.Column("source_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("(crop_variety_id IS NOT NULL)::int + (livestock_breed_id IS NOT NULL)::int <= 1", name="ck_vendor_product_one_catalogue_item"),
        sa.UniqueConstraint("vendor_id", "product_name", name="uq_vendor_product_name"),
    )
    for column in ("vendor_id", "crop_variety_id", "livestock_breed_id"):
        op.create_index(f"ix_vendor_products_{column}", "vendor_products", [column])

    op.create_table(
        "markets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("county_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counties.id"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False), sa.Column("sub_county", sa.String(120)), sa.Column("ward", sa.String(120)),
        sa.Column("latitude", sa.Float(), nullable=False), sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("market_days", sa.String(120)), sa.Column("contact", sa.String(120)),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("source_checked_on", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("county_id", "name", name="uq_market_county_name"),
    )
    op.create_index("ix_markets_county_id", "markets", ["county_id"])


def downgrade() -> None:
    op.drop_index("ix_markets_county_id", table_name="markets")
    op.drop_table("markets")
    for column in ("livestock_breed_id", "crop_variety_id", "vendor_id"):
        op.drop_index(f"ix_vendor_products_{column}", table_name="vendor_products")
    op.drop_table("vendor_products")
    op.drop_index("ix_vendors_county_id", table_name="vendors")
    op.drop_index("ix_vendors_name", table_name="vendors")
    op.drop_table("vendors")
    op.drop_index("ix_livestock_breeds_livestock_id", table_name="livestock_breeds")
    op.drop_table("livestock_breeds")
    op.drop_index("ix_crop_varieties_crop_id", table_name="crop_varieties")
    op.drop_table("crop_varieties")
