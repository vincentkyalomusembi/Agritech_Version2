"""Add staff users, size quotes, pricing rules, and audit logs.

Revision ID: b7c3d91e4a10
Revises: 4351f7d11d0d
Create Date: 2026-09-29 04:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7c3d91e4a10"
down_revision: Union[str, Sequence[str], None] = "4351f7d11d0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    staffrole = postgresql.ENUM(
        "platform_admin", "officer", name="staffrole", create_type=False
    )
    quotestatus = postgresql.ENUM(
        "pending", "paid", "expired", "cancelled", name="quotestatus", create_type=False
    )
    staffrole.create(op.get_bind(), checkfirst=True)
    quotestatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "pricing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tlu_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bands", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("entitlements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_pricing_rules_version", "pricing_rules", ["version"], unique=True)

    op.create_table(
        "subscription_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("farmer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("acres_used", sa.Float(), nullable=False),
        sa.Column("tlu_used", sa.Float(), nullable=False),
        sa.Column("herd_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("size_class", sa.String(length=20), nullable=False),
        sa.Column("amount_kes", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_rules.id"), nullable=True),
        sa.Column("status", quotestatus, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_subscription_quotes_farmer_id", "subscription_quotes", ["farmer_id"])
    op.create_index("ix_subscription_quotes_size_class", "subscription_quotes", ["size_class"])
    op.create_index("ix_subscription_quotes_status", "subscription_quotes", ["status"])

    op.add_column("subscriptions", sa.Column("size_class", sa.String(length=20), nullable=True))
    op.add_column("subscriptions", sa.Column("amount_kes", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("subscriptions", sa.Column("rule_version", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_subscriptions_quote_id",
        "subscriptions",
        "subscription_quotes",
        ["quote_id"],
        ["id"],
    )
    op.create_index("ix_subscriptions_size_class", "subscriptions", ["size_class"])

    op.execute(
        """
        UPDATE subscriptions
        SET size_class = CASE plan_name
            WHEN 'Basic' THEN 'Micro'
            WHEN 'Standard' THEN 'Small'
            WHEN 'Premium' THEN 'Medium'
            ELSE plan_name
        END,
        amount_kes = CASE plan_name
            WHEN 'Basic' THEN 0
            WHEN 'Standard' THEN 50
            WHEN 'Premium' THEN 150
            ELSE amount_kes
        END,
        plan_name = CASE plan_name
            WHEN 'Basic' THEN 'Micro'
            WHEN 'Standard' THEN 'Small'
            WHEN 'Premium' THEN 'Medium'
            ELSE plan_name
        END
        """
    )

    op.create_table(
        "staff_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", staffrole, nullable=False),
        sa.Column("county_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counties.id"), nullable=True),
        sa.Column("expert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("experts.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_staff_users_phone_number", "staff_users", ["phone_number"], unique=True)
    op.create_index("ix_staff_users_email", "staff_users", ["email"], unique=True)
    op.create_index("ix_staff_users_role", "staff_users", ["role"])
    op.create_index("ix_staff_users_county_id", "staff_users", ["county_id"])
    op.create_index("ix_staff_users_expert_id", "staff_users", ["expert_id"], unique=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_kind", sa.String(length=20), nullable=False, server_default="staff"),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.execute(
        sa.text(
            """
            INSERT INTO pricing_rules (id, version, tlu_weights, bands, entitlements, is_active)
            VALUES (
                gen_random_uuid(),
                1,
                '{"cattle": 1.0, "goats": 0.15, "sheep": 0.15, "chicken": 0.01, "ducks": 0.01, "turkeys": 0.01, "poultry": 0.01, "other": 0.2}'::jsonb,
                '[
                    {"name": "Micro", "min_acres": 0, "max_acres": 1, "min_tlu": 0, "max_tlu": 1, "kes": 0},
                    {"name": "Small", "min_acres": 1, "max_acres": 3, "min_tlu": 1, "max_tlu": 5, "kes": 20},
                    {"name": "Medium", "min_acres": 3, "max_acres": 10, "min_tlu": 5, "max_tlu": 20, "kes": 40},
                    {"name": "Large", "min_acres": 10, "max_acres": null, "min_tlu": 20, "max_tlu": null, "kes": 70}
                ]'::jsonb,
                '{
                    "Micro": ["weather_alerts", "market_prices", "profile_update", "subscription"],
                    "Small": ["weather_alerts", "market_prices", "profile_update", "subscription", "crop_recommendation", "livestock_recommendation", "disease_alerts", "expert_request"],
                    "Medium": ["weather_alerts", "market_prices", "profile_update", "subscription", "crop_recommendation", "livestock_recommendation", "disease_alerts", "expert_request"],
                    "Large": ["weather_alerts", "market_prices", "profile_update", "subscription", "crop_recommendation", "livestock_recommendation", "disease_alerts", "expert_request"]
                }'::jsonb,
                true
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_staff_users_expert_id", table_name="staff_users")
    op.drop_table("staff_users")
    op.drop_constraint("fk_subscriptions_quote_id", "subscriptions", type_="foreignkey")
    op.drop_index("ix_subscriptions_size_class", table_name="subscriptions")
    op.drop_column("subscriptions", "rule_version")
    op.drop_column("subscriptions", "quote_id")
    op.drop_column("subscriptions", "amount_kes")
    op.drop_column("subscriptions", "size_class")
    op.drop_table("subscription_quotes")
    op.drop_table("pricing_rules")
    postgresql.ENUM(name="staffrole").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="quotestatus").drop(op.get_bind(), checkfirst=True)
