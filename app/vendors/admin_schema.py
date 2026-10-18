from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

CATEGORY_PATTERN = r"^(seeds|feed|fertiliser|vaccines|tools|livestock|inputs|agrochemicals|vet_drugs)$"


class VendorWrite(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    county_id: UUID | None = None
    address: str | None = Field(default=None, min_length=2)
    sub_county: str | None = Field(default=None, max_length=120)
    ward: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-4.7, le=5.1)
    longitude: float | None = Field(default=None, ge=33.9, le=41.9)
    contact_phone: str | None = Field(default=None, max_length=40)
    whatsapp_phone: str | None = Field(default=None, max_length=20)
    contact_email: str | None = Field(default=None, max_length=254)
    opening_hours: str | None = None
    certified: bool | None = None
    sponsored: bool | None = None
    categories: list[str] | None = None
    source_url: str | None = None


class VendorCreate(VendorWrite):
    name: str = Field(min_length=2, max_length=180)
    county_id: UUID
    address: str = Field(min_length=2)


class VendorProductWrite(BaseModel):
    product_name: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, pattern=CATEGORY_PATTERN)
    price_kes: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=60)
    stock_quantity: float | None = Field(default=None, ge=0)
    crop_variety_id: UUID | None = None
    livestock_breed_id: UUID | None = None


class VendorProductCreate(VendorProductWrite):
    product_name: str = Field(min_length=2, max_length=180)
    unit: str = Field(min_length=1, max_length=60)


class DailyEngagement(BaseModel):
    date: date
    views: int
    contacts: int


class VendorReport(BaseModel):
    vendor_id: UUID
    name: str
    sponsored: bool
    days: int
    views: int
    contacts: int
    calls: int
    whatsapp: int
    directions: int
    unique_farmers: int
    contact_rate: float | None
    daily: list[DailyEngagement]


class VendorRanking(BaseModel):
    vendor_id: UUID
    name: str
    county: str | None
    sponsored: bool
    views: int
    contacts: int
