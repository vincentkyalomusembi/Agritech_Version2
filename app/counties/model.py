import uuid

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Float

from app.database.base import Base

class County(Base):
    __tablename__ = "counties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    farmers = relationship(
        "Farmer",
        back_populates="county",
    )

    experts= relationship(
        "Expert", 
        back_populates="county")

    constituencies = relationship("Constituency", back_populates="county", cascade="all, delete-orphan")


class Constituency(Base):
    """Electoral constituency, commonly used as the sub-county choice in forms."""

    __tablename__ = "constituencies"
    __table_args__ = (UniqueConstraint("county_id", "name", name="uq_constituency_county_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    county_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("counties.id", ondelete="CASCADE"), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    county = relationship("County", back_populates="constituencies")
    wards = relationship("Ward", back_populates="constituency", cascade="all, delete-orphan")


class Ward(Base):
    """County assembly ward linked through its constituency."""

    __tablename__ = "wards"
    __table_args__ = (UniqueConstraint("constituency_id", "name", name="uq_ward_constituency_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    constituency_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=False, index=True)

    constituency = relationship("Constituency", back_populates="wards")
