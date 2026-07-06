"""
Market Prices — Pydantic Schemas
=================================
Request and response schemas for the /market-prices endpoints.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
#  Response                                                            #
# ------------------------------------------------------------------ #

class MarketPriceResponse(BaseModel):
    """
    Serialised MarketPrice row returned to API clients.
    """
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


# ------------------------------------------------------------------ #
#  Request (manual admin entry, if needed)                             #
# ------------------------------------------------------------------ #

class MarketPriceCreate(BaseModel):
    """
    Payload for manually creating a market price entry.
    Normally prices come from KAMIS scraper, but admins can add too.
    """
    county_id: UUID
    crop_id: UUID
    market_name: str = Field(..., min_length=2, max_length=150)
    minimum_price: float = Field(..., gt=0)
    maximum_price: float = Field(..., gt=0)
    average_price: float = Field(..., gt=0)
    unit: str = Field(..., max_length=50)
    price_date: date
    source: str = Field(default="MANUAL", max_length=100)
