import uuid

from sqlalchemy import (
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    county_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("counties.id"),
        nullable=False,
        index=True,
    )

    crop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crops.id"),
        nullable=False,
        index=True,
    )

    market_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    minimum_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    average_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    price_date: Mapped[Date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    county = relationship(
        "County"
    )

    crop = relationship(
        "Crop"
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="KAMIS",
        )