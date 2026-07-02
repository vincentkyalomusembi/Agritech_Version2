import uuid
import enum

from sqlalchemy import (
    String,
    Text,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SessionType(enum.Enum):
    CROP_RECOMMENDATION = "Crop Recommendation"
    LIVESTOCK_RECOMMENDATION = "Livestock Recommendation"
    EXPERT_REQUEST = "Expert Request"


class SessionStatus(enum.Enum):
    ACTIVE = "Active"
    COMPLETED = "Completed"
    EXPIRED = "Expired"


class SMSSession(Base):
    __tablename__ = "sms_sessions"

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

    session_type: Mapped[SessionType] = mapped_column(
        Enum(SessionType),
        nullable=False,
        index=True,
    )

    session_status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus),
        default=SessionStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    current_step: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    session_data: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    expires_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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

    farmer = relationship(
        "Farmer",
        back_populates="sms_sessions",
    )