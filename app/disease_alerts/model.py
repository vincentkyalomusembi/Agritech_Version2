import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OutbreakAlert(Base):
    """An admin-issued area alert; recipients get an SMS and an inbox notification."""

    __tablename__ = "outbreak_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symptom_code: Mapped[str] = mapped_column(String(60), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_key: Mapped[str | None] = mapped_column(String(60))
    center_lat: Mapped[float] = mapped_column(Float, nullable=False)
    center_lng: Mapped[float] = mapped_column(Float, nullable=False)
    radius_km: Mapped[float] = mapped_column(Float, nullable=False)
    message_en: Mapped[str] = mapped_column(Text, nullable=False)
    message_sw: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="sent", server_default="sent")
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutbreakSettings(Base):
    """Single row (id=1) holding the signal flagging policy."""

    __tablename__ = "outbreak_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    minimum_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cell_size_deg: Mapped[float] = mapped_column(Float, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff_users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
