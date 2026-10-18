import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Index,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CropVariety(Base):
    __tablename__ = "crop_varieties"
    __table_args__ = (UniqueConstraint("crop_id", "name", name="uq_crop_variety_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    maintainer: Mapped[str | None] = mapped_column(String(150))
    altitude_min_m: Mapped[int | None] = mapped_column(Integer)
    altitude_max_m: Mapped[int | None] = mapped_column(Integer)
    rainfall_min_mm: Mapped[int | None] = mapped_column(Integer)
    rainfall_max_mm: Mapped[int | None] = mapped_column(Integer)
    maturity_days_min: Mapped[int | None] = mapped_column(Integer)
    maturity_days_max: Mapped[int | None] = mapped_column(Integer)
    risk_attributes: Mapped[str | None] = mapped_column(Text)
    adapted_regions: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_checked_on: Mapped[Date | None] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    crop = relationship("Crop")


class LivestockBreed(Base):
    __tablename__ = "livestock_breeds"
    __table_args__ = (UniqueConstraint("livestock_id", "name", name="uq_livestock_breed_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    livestock_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("livestock.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    altitude_min_m: Mapped[int | None] = mapped_column(Integer)
    altitude_max_m: Mapped[int | None] = mapped_column(Integer)
    rainfall_min_mm: Mapped[int | None] = mapped_column(Integer)
    rainfall_max_mm: Mapped[int | None] = mapped_column(Integer)
    maturity_days_min: Mapped[int | None] = mapped_column(Integer)
    maturity_days_max: Mapped[int | None] = mapped_column(Integer)
    risk_attributes: Mapped[str | None] = mapped_column(Text)
    adapted_regions: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_checked_on: Mapped[Date | None] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    livestock = relationship("Livestock")


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("name", "address", name="uq_vendor_name_address"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    county_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("counties.id"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    sub_county: Mapped[str | None] = mapped_column(String(120))
    ward: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    contact_email: Mapped[str | None] = mapped_column(String(254))
    opening_hours: Mapped[str | None] = mapped_column(Text)
    whatsapp_phone: Mapped[str | None] = mapped_column(String(20))
    certified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Paid placement: listed first and always labelled as sponsored to farmers.
    sponsored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    categories: Mapped[list | None] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_checked_on: Mapped[Date | None] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    county = relationship("County")
    products = relationship("VendorProduct", back_populates="vendor", cascade="all, delete-orphan")


class VendorProduct(Base):
    __tablename__ = "vendor_products"
    __table_args__ = (
        CheckConstraint("(crop_variety_id IS NOT NULL)::int + (livestock_breed_id IS NOT NULL)::int <= 1", name="ck_vendor_product_one_catalogue_item"),
        UniqueConstraint("vendor_id", "product_name", name="uq_vendor_product_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_variety_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("crop_varieties.id", ondelete="SET NULL"), index=True)
    livestock_breed_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("livestock_breeds.id", ondelete="SET NULL"), index=True)
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str | None] = mapped_column(String(30))
    price_kes: Mapped[float | None] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(60), nullable=False)
    stock_quantity: Mapped[float | None] = mapped_column(Float)
    price_checked_on: Mapped[Date | None] = mapped_column(Date)
    stock_checked_on: Mapped[Date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor = relationship("Vendor", back_populates="products")
    crop_variety = relationship("CropVariety")
    livestock_breed = relationship("LivestockBreed")


class VendorEvent(Base):
    """A farmer viewing or contacting a vendor; the basis for listing reports."""

    __tablename__ = "vendor_events"
    __table_args__ = (Index("ix_vendor_events_vendor_type", "vendor_id", "event_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    farmer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("farmers.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Market(Base):
    __tablename__ = "markets"
    __table_args__ = (UniqueConstraint("county_id", "name", name="uq_market_county_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    county_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("counties.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    sub_county: Mapped[str | None] = mapped_column(String(120))
    ward: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    market_days: Mapped[str | None] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_checked_on: Mapped[Date | None] = mapped_column(Date)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    county = relationship("County")
