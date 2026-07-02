import uuid
import enum

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ExpertType(enum.Enum):
    AGRICULTURE = "Agriculture"
    VETERINARY = "Veterinary"


class Expert(Base):
    __tablename__ = "experts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    expert_type: Mapped[ExpertType] = mapped_column(
        Enum(ExpertType),
        nullable=False,
        index=True,
    )

    county_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("counties.id"),
        nullable=False,
        index=True,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
        back_populates="experts",
    )

    expert_requests = relationship(
        "ExpertRequest",
        back_populates="expert",
    )

    organization: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )