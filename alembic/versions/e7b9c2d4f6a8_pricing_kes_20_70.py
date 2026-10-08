"""Retune paid size bands to KES 20–70 (Large cap 70).

Revision ID: e7b9c2d4f6a8
Revises: a1b2c3d4e5f6
Create Date: 2026-09-30 18:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e7b9c2d4f6a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_BANDS = """
[
    {"name": "Micro", "min_acres": 0, "max_acres": 1, "min_tlu": 0, "max_tlu": 1, "kes": 0},
    {"name": "Small", "min_acres": 1, "max_acres": 3, "min_tlu": 1, "max_tlu": 5, "kes": 20},
    {"name": "Medium", "min_acres": 3, "max_acres": 10, "min_tlu": 5, "max_tlu": 20, "kes": 40},
    {"name": "Large", "min_acres": 10, "max_acres": null, "min_tlu": 20, "max_tlu": null, "kes": 70}
]
"""

OLD_BANDS = """
[
    {"name": "Micro", "min_acres": 0, "max_acres": 1, "min_tlu": 0, "max_tlu": 1, "kes": 0},
    {"name": "Small", "min_acres": 1, "max_acres": 3, "min_tlu": 1, "max_tlu": 5, "kes": 50},
    {"name": "Medium", "min_acres": 3, "max_acres": 10, "min_tlu": 5, "max_tlu": 20, "kes": 150},
    {"name": "Large", "min_acres": 10, "max_acres": null, "min_tlu": 20, "max_tlu": null, "kes": 400}
]
"""


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE pricing_rules SET bands = CAST(:bands AS jsonb) WHERE is_active = true").bindparams(
            bands=NEW_BANDS.strip()
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE pricing_rules SET bands = CAST(:bands AS jsonb) WHERE is_active = true").bindparams(
            bands=OLD_BANDS.strip()
        )
    )
