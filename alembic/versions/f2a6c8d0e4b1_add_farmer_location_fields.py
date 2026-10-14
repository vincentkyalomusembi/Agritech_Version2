"""Add optional location details to farmer profiles.

Revision ID: f2a6c8d0e4b1
Revises: e7b9c2d4f6a8
Create Date: 2026-10-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a6c8d0e4b1"
down_revision: Union[str, Sequence[str], None] = "e7b9c2d4f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("farmers", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("farmers", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("farmers", sa.Column("sub_county", sa.String(length=100), nullable=True))
    op.add_column("farmers", sa.Column("ward", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("farmers", "ward")
    op.drop_column("farmers", "sub_county")
    op.drop_column("farmers", "longitude")
    op.drop_column("farmers", "latitude")
