import uuid

from sqlalchemy import (
    String,
    Float,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FarmerCrop(Base):
    __tablename__ = "farmer_crops"

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

    crop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crops.id"),
        nullable=False,
        index=True,
    )

    farm_size: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    soil_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    experience_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    farmer = relationship(
        "Farmer",
        back_populates="crops",
    )

    crop = relationship(
        "Crop",
        back_populates="farmer_crops",
    )