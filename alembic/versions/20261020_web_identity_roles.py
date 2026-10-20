"""Add shared role-based web identities.

Revision ID: 20261020roles
Revises: 20261019outb
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261020roles"
down_revision: Union[str, Sequence[str], None] = "20261019outb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    webrole = postgresql.ENUM("farmer", "expert", "admin", name="webrole", create_type=False)
    webrole.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "web_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", webrole, nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("pin_hash", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("farmer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("expert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_web_users_role", "web_users", ["role"])
    op.create_index("ix_web_users_phone_number", "web_users", ["phone_number"], unique=True)
    op.create_index("uq_web_users_farmer_id", "web_users", ["farmer_id"], unique=True)
    op.create_index("uq_web_users_expert_id", "web_users", ["expert_id"], unique=True)

    bind = op.get_bind()
    bind.execute(sa.text("""
        INSERT INTO web_users (id, role, full_name, phone_number, pin_hash, farmer_id, is_active)
        SELECT id, 'farmer', full_name, phone_number, pin_hash, id, is_active
        FROM farmers
    """))
    bind.execute(sa.text("""
        INSERT INTO web_users (id, role, full_name, phone_number, email, password_hash, expert_id, is_active)
        SELECT s.id,
               (CASE WHEN s.role::text = 'platform_admin' THEN 'admin' ELSE 'expert' END)::webrole,
               s.full_name, s.phone_number, s.email, s.password_hash, s.expert_id, s.is_active
        FROM staff_users s
        WHERE NOT EXISTS (SELECT 1 FROM web_users u WHERE u.phone_number = s.phone_number)
    """))
    bind.execute(sa.text("""
        INSERT INTO web_users (id, role, full_name, phone_number, expert_id, is_active)
        SELECT e.id, 'expert', e.full_name, e.phone_number, e.id, true
        FROM experts e
        WHERE NOT EXISTS (SELECT 1 FROM web_users u WHERE u.phone_number = e.phone_number)
    """))


def downgrade() -> None:
    op.drop_index("uq_web_users_expert_id", table_name="web_users")
    op.drop_index("uq_web_users_farmer_id", table_name="web_users")
    op.drop_index("ix_web_users_phone_number", table_name="web_users")
    op.drop_index("ix_web_users_role", table_name="web_users")
    op.drop_table("web_users")
    sa.Enum(name="webrole").drop(op.get_bind(), checkfirst=True)
