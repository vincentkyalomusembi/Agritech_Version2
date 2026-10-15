import uuid
import enum

from sqlalchemy import (
    Boolean,
    String,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RecommendationType(enum.Enum):
    CROP = "Crop"
    LIVESTOCK = "Livestock"


class Recommendation(Base):
    __tablename__ = "recommendations"

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

    crop_variety_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crop_varieties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    livestock_breed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("livestock_breeds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendor_products.id", ondelete="SET NULL"), nullable=True, index=True
    )

    recommendation_type: Mapped[RecommendationType] = mapped_column(
        Enum(RecommendationType),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    recommendation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommendation_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ai_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    farmer = relationship(
        "Farmer",
        back_populates="recommendations",
    )

    is_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    sms_deliveries = relationship(
        "RecommendationSMSDelivery", back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationSMSDelivery(Base):
    """One provider submission and its eventual delivery report."""
    __tablename__ = "recommendation_sms_deliveries"
    __table_args__ = (Index("ix_recommendation_sms_deliveries_provider_id", "provider_message_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommendation = relationship("Recommendation", back_populates="sms_deliveries")
