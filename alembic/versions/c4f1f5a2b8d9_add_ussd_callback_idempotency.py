"""Add durable USSD callback replay protection.

Revision ID: c4f1f5a2b8d9
Revises: 9ea603b718c4
Create Date: 2026-07-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f1f5a2b8d9"
down_revision: Union[str, Sequence[str], None] = "9ea603b718c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the provider session key and cached callback response."""

    # ---- Copilot Improvement ----
    # Persisting these values makes USSD retry handling safe in multi-worker
    # deployments; a unique provider session ID also prevents duplicate work.
    # ---- End Improvement ----
    op.add_column(
        "sms_sessions",
        sa.Column("callback_session_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "sms_sessions",
        sa.Column("callback_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "sms_sessions",
        sa.Column("response_text", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_sms_sessions_callback_session_id"),
        "sms_sessions",
        ["callback_session_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove USSD replay protection fields."""

    op.drop_index(op.f("ix_sms_sessions_callback_session_id"), table_name="sms_sessions")
    op.drop_column("sms_sessions", "response_text")
    op.drop_column("sms_sessions", "callback_text")
    op.drop_column("sms_sessions", "callback_session_id")
