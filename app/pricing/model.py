import enum
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class QuoteStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    tlu_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    bands: Mapped[list] = mapped_column(JSONB, nullable=False)
    entitlements: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    quotes = relationship("SubscriptionQuote", back_populates="rule")


class SubscriptionQuote(Base):
    __tablename__ = "subscription_quotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    acres_used: Mapped[float] = mapped_column(Float, nullable=False)
    tlu_used: Mapped[float] = mapped_column(Float, nullable=False)
    herd_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    size_class: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount_kes: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_rules.id"),
        nullable=True,
    )
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(
            QuoteStatus,
            name="quotestatus",
            create_type=False,
            values_callable=lambda members: [item.value for item in members],
        ),
        default=QuoteStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    farmer = relationship("Farmer")
    rule = relationship("PricingRule", back_populates="quotes")
