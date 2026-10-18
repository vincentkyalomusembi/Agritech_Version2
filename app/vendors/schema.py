from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class OpeningInterval(BaseModel):
    open: str
    close: str


class VendorSummary(BaseModel):
    id: UUID
    name: str
    county: str | None
    sub_county: str | None
    ward: str | None
    address: str
    latitude: float | None
    longitude: float | None
    phone: str | None
    whatsapp: str | None
    email: str | None
    certified: bool
    sponsored: bool
    categories: list[str]
    opening_hours_text: str | None
    # Weekday (0 = Sunday) to interval or null when closed; null if hours are unknown.
    opening_hours: dict[int, OpeningInterval | None] | None
    distance_km: float | None = None
    product_count: int = 0


class VendorPage(BaseModel):
    items: list[VendorSummary]
    total: int
    limit: int
    offset: int


class VendorProductResponse(BaseModel):
    id: UUID
    vendor_id: UUID
    name: str
    category: str
    price_kes: float | None
    unit: str
    stock_status: Literal["in_stock", "low_stock", "out_of_stock", "unknown"]
    price_checked_on: str | None
    crop_variety_id: UUID | None
    livestock_breed_id: UUID | None


class VendorEventCreate(BaseModel):
    event: Literal["view", "call", "whatsapp", "directions", "contact"]


class VendorEventCounts(BaseModel):
    views: int
    contacts: int
