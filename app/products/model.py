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


class ProductCategory(enum.Enum):
    FERTILIZER = "Fertilizer"
    PESTICIDE = "Pesticide"
    HERBICIDE = "Herbicide"
    FUNGICIDE = "Fungicide"
    SEED = "Seed"
    ANIMAL_FEED = "Animal Feed"
    VETERINARY = "Veterinary Medicine"


class AgriculturalProduct(Base):
    __tablename__ = "agricultural_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    product_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    manufacturer: Mapped[str] = mapped_column(
        String(150),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
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

    target_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        )