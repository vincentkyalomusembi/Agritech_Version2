from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.pricing.model import QuoteStatus


class SizeComputation(BaseModel):
    acres: float
    tlu_by_species: dict[str, float]
    tlu_total: float
    crop_class: str
    livestock_class: str
    size_class: str
    monthly_kes: int
    has_size_input: bool
    rule_version: int


class QuoteResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    acres_used: float
    tlu_used: float
    herd_snapshot: dict
    size_class: str
    amount_kes: int
    rule_version: int
    status: QuoteStatus
    created_at: datetime
    sms_text: str | None = None

    model_config = {"from_attributes": True}


class QuotePreviewQuery(BaseModel):
    acres: float = 0
    cattle: int = Field(default=0, ge=0)
    goats: int = Field(default=0, ge=0)
    sheep: int = Field(default=0, ge=0)
    poultry: int = Field(default=0, ge=0)


class PricingRuleResponse(BaseModel):
    id: UUID
    version: int
    tlu_weights: dict
    bands: list
    entitlements: dict
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PricingRuleCreate(BaseModel):
    tlu_weights: dict
    bands: list
    entitlements: dict
    is_active: bool = True
