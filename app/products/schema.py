from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.products.model import ProductCategory


class ProductCreate(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=150)
    category: ProductCategory
    description: str | None = None
    manufacturer: str | None = None
    is_active: bool = True
    target_type: str = Field(..., max_length=20)  # "crop" or "livestock"


class ProductUpdate(BaseModel):
    product_name: str | None = Field(default=None, min_length=2, max_length=150)
    category: ProductCategory | None = None
    description: str | None = None
    manufacturer: str | None = None
    is_active: bool | None = None
    target_type: str | None = None


class ProductResponse(BaseModel):
    id: UUID
    product_name: str
    category: ProductCategory
    description: str | None
    manufacturer: str | None
    is_active: bool
    target_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
