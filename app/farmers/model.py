import uuid

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    national_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    pin_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    county_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("counties.id"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    county = relationship(
        "County",
        back_populates="farmers",
    )

    crops = relationship(
        "FarmerCrop",
        back_populates="farmer",
        cascade="all, delete-orphan",
    )

    livestock = relationship(
        "FarmerLivestock",
        back_populates="farmer",
        cascade="all, delete-orphan",
    )

    subscriptions = relationship(
        "Subscription",
        back_populates="farmer",
    )

    recommendations = relationship(
        "Recommendation",
        back_populates="farmer",
    )

    notifications = relationship(
        "Notification",
        back_populates="farmer",
    )

    sms_sessions = relationship(
        "SMSSession",
        back_populates="farmer",
    )

    expert_requests = relationship(
        "ExpertRequest",
        back_populates="farmer",
    )