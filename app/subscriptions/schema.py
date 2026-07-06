from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionResponse(BaseModel):
    """Subscription data returned to clients or internal callers."""

    id: UUID
    farmer_id: UUID
    is_active: bool
    plan_name: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class SubscriptionActivateRequest(BaseModel):
    """Data required to activate or renew a subscription."""

    farmer_id: UUID
    plan_name: str = Field(default="Premium", min_length=1, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
