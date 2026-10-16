"""Add county, constituency, ward reference hierarchy.

Revision ID: 20261016geo
Revises: 20261015env
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261016geo"
down_revision: Union[str, Sequence[str], None] = "20261015env"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "constituencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("county_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.UniqueConstraint("county_id", "name", name="uq_constituency_county_name"),
    )
    op.create_index("ix_constituencies_code", "constituencies", ["code"])
    op.create_index("ix_constituencies_name", "constituencies", ["name"])
    op.create_index("ix_constituencies_county_id", "constituencies", ["county_id"])
    op.create_table(
        "wards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("constituency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("constituency_id", "name", name="uq_ward_constituency_name"),
    )
    op.create_index("ix_wards_code", "wards", ["code"])
    op.create_index("ix_wards_name", "wards", ["name"])
    op.create_index("ix_wards_constituency_id", "wards", ["constituency_id"])
    op.add_column("farmers", sa.Column("constituency_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("farmers", sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_farmers_constituency_id", "farmers", "constituencies", ["constituency_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_farmers_ward_id", "farmers", "wards", ["ward_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_farmers_constituency_id", "farmers", ["constituency_id"])
    op.create_index("ix_farmers_ward_id", "farmers", ["ward_id"])


def downgrade() -> None:
    op.drop_index("ix_farmers_ward_id", table_name="farmers")
    op.drop_index("ix_farmers_constituency_id", table_name="farmers")
    op.drop_constraint("fk_farmers_ward_id", "farmers", type_="foreignkey")
    op.drop_constraint("fk_farmers_constituency_id", "farmers", type_="foreignkey")
    op.drop_column("farmers", "ward_id")
    op.drop_column("farmers", "constituency_id")
    op.drop_index("ix_wards_constituency_id", table_name="wards")
    op.drop_index("ix_wards_name", table_name="wards")
    op.drop_index("ix_wards_code", table_name="wards")
    op.drop_table("wards")
    op.drop_index("ix_constituencies_county_id", table_name="constituencies")
    op.drop_index("ix_constituencies_name", table_name="constituencies")
    op.drop_index("ix_constituencies_code", table_name="constituencies")
    op.drop_table("constituencies")
