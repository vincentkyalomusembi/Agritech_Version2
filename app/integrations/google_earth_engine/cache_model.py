import uuid
from datetime import date

from sqlalchemy import Date as SQLDate, DateTime, Float, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class EnvironmentalCache(Base):
    __tablename__ = "environmental_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)
    region_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    region_name: Mapped[str] = mapped_column(String(150), nullable=False)
    county_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ndvi: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ndvi_trend: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    observed_on: Mapped[date] = mapped_column(SQLDate, nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    county = relationship("County")