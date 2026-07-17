import uuid

from sqlalchemy import (
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FarmerLivestock(Base):
    __tablename__ = "farmer_livestock"

    # Prevent a farmer from registering the same livestock more than once.
    __table_args__= (
        UniqueConstraint(
            "farmer_id",
            "livestock_id",
            name="uq_farmer_livestock",
        ),
    )

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

    livestock_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("livestock.id"),
        nullable=False,
        index=True,
    )

    herd_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    farmer = relationship(
        "Farmer",
        back_populates="livestock",
    )

    livestock = relationship(
        "Livestock",
        back_populates="farmer_livestock",
    )