from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.expert_requests.model import RequestStatus
from app.experts.model import ExpertType
from app.experts.schema import ExpertResponse
from app.pricing.schema import PricingRuleResponse, QuoteResponse, SizeComputation
from app.staff.schema import StaffResponse


class Page(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class AdminOverview(BaseModel):
    farmers_total: int
    farmers_7d: int
    by_size_class: dict[str, int]
    active_paid_subscriptions: int
    failed_payments_7d: int
    requests_by_status: dict[str, int]
    requests_aging_48h: int
    advisories_active: int
    market_prices_last_scraped_at: datetime | None
    sms_sessions_open: int
    health: dict[str, Any]


class AdminFarmerListItem(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    national_id_masked: str
    county_id: UUID
    county_name: str | None = None
    is_active: bool
    acres: float
    size_class: str | None
    amount_kes: int | None
    created_at: datetime


class AdminFarmerDetail(AdminFarmerListItem):
    national_id: str | None = None
    crops: list[dict]
    livestock: list[dict]
    tlu_total: float
    current_quote: QuoteResponse | None = None
    requests: list[dict]


class AdminFarmerActiveUpdate(BaseModel):
    is_active: bool


class AdminExpertCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    phone_number: str = Field(..., min_length=10, max_length=20)
    expert_type: ExpertType
    county_id: UUID
    organization: str = Field(..., min_length=2, max_length=150)
    is_available: bool = True


class AdminExpertUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    expert_type: ExpertType | None = None
    county_id: UUID | None = None
    organization: str | None = None
    is_available: bool | None = None


class AdminCountyItem(BaseModel):
    id: UUID
    name: str


class AdminFieldOfficerCreate(BaseModel):
    """Creates an Expert (USSD directory) and linked officer StaffUser in one request."""

    full_name: str = Field(..., min_length=3, max_length=150)
    phone_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    expert_type: ExpertType
    county_id: UUID
    organization: str = Field(..., min_length=2, max_length=150)
    email: str | None = None
    is_available: bool = False


class AdminFieldOfficerResponse(BaseModel):
    expert: ExpertResponse
    staff: StaffResponse


class AdminRequestItem(BaseModel):
    id: UUID
    farmer_id: UUID
    farmer_name: str | None = None
    farmer_phone: str | None = None
    county_id: UUID | None = None
    county_name: str | None = None
    expert_id: UUID
    expert_name: str | None = None
    issue_type: str
    description: str
    status: RequestStatus
    preferred_visit_date: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminRequestPatch(BaseModel):
    status: RequestStatus | None = None
    expert_id: UUID | None = None


class AvailabilityUpdate(BaseModel):
    is_available: bool


class RequoteRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=300)


class PageFarmers(BaseModel):
    items: list[AdminFarmerListItem]
    total: int
    limit: int
    offset: int


class PageRequests(BaseModel):
    items: list[AdminRequestItem]
    total: int
    limit: int
    offset: int


class PageQuotes(BaseModel):
    items: list[QuoteResponse]
    total: int
    limit: int
    offset: int


class PageGeneric(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


class PageStaff(BaseModel):
    items: list[StaffResponse]
    total: int
    limit: int
    offset: int


class PageExperts(BaseModel):
    items: list[ExpertResponse]
    total: int
    limit: int
    offset: int


class PagePricing(BaseModel):
    items: list[PricingRuleResponse]
    total: int
    limit: int
    offset: int


class QuotePreviewResponse(SizeComputation):
    sms_text: str
