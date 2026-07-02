import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RequestStatus(enum.Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ExpertRequest(Base):
    __tablename__ = "expert_requests"

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

    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id"),
        nullable=False,
        index=True,
    )

    issue_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus),
        default=RequestStatus.PENDING,
        nullable=False,
        index=True,
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

    farmer = relationship(
        "Farmer",
        back_populates="expert_requests",
    )

    expert = relationship(
        "Expert",
        back_populates="expert_requests",
    )

    preferred_visit_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )