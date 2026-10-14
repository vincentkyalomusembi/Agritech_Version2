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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RequestStatus(enum.Enum):
    PENDING = "Pending"
    OFFERED = "Offered"
    ACCEPTED = "Accepted"
    UNASSIGNED = "Unassigned"
    ESCALATED = "Escalated"
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

    expert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id"),
        nullable=True,
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

    request_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, default=lambda: f"ER-{uuid.uuid4().hex[:8].upper()}")
    farmer_resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True, nullable=True)


class ExpertOffer(Base):
    __tablename__ = "expert_offers"
    __table_args__ = (UniqueConstraint("request_id", "expert_id", name="uq_expert_offer_request_expert"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("expert_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    expert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("experts.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offered")
    score: Mapped[float] = mapped_column(nullable=False)
    offered_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    responded_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    response_seconds: Mapped[int | None] = mapped_column()
    response_note: Mapped[str | None] = mapped_column(String(240))

    request = relationship("ExpertRequest")
    expert = relationship("Expert")
