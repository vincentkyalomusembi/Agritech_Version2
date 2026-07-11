from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class MarketPriceCreate(BaseModel):
    county_id: UUID
    crop_id: UUID
    market_name: str = Field(..., min_length=2, max_length=150)
    minimum_price: float = Field(..., gt=0)
    maximum_price: float = Field(..., gt=0)
    average_price: float = Field(..., gt=0)
    unit: str = Field(..., max_length=50)
    price_date: date
    source: str = Field(default="MANUAL", max_length=100)


class MarketPriceResponse(BaseModel):
    id: UUID
    county_id: UUID
    crop_id: UUID
    market_name: str
    minimum_price: float
    maximum_price: float
    average_price: float
    unit: str
    price_date: date
    source: str

    model_config = {"from_attributes": True}
