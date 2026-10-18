from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.expert_requests.model import RequestStatus


class ExpertRequestCreate(BaseModel):
    """Data required to submit an expert request."""

    farmer_id: UUID | None = None
    expert_id: UUID | None = None
    issue_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    preferred_visit_date: datetime | None = None
    symptom_codes: list[Annotated[str, Field(pattern=r"^[a-z0-9-]{2,40}$")]] = Field(default_factory=list, max_length=10)
    urgency: str | None = Field(default=None, pattern=r"^(emergency|soon|general_advice)$")


class ExpertRequestStatusUpdate(BaseModel):
    """Data required to update an expert request status."""

    request_id: UUID
    status: RequestStatus


class ExpertRequestResponse(BaseModel):
    """Expert request data returned to clients."""

    id: UUID
    farmer_id: UUID
    expert_id: UUID | None
    issue_type: str
    description: str
    status: RequestStatus
    preferred_visit_date: datetime | None
    created_at: datetime
    updated_at: datetime
    request_code: str
    farmer_resolution: str | None = None
    symptom_codes: list[str] | None = None
    urgency: str | None = None

    model_config = {
        "from_attributes": True,
    }


class FarmerRequestExpert(BaseModel):
    """Assigned expert as shown to the farmer; phone only once accepted."""

    id: UUID
    full_name: str
    expert_type: str
    organization: str | None = None
    phone_number: str | None = None


class FarmerExpertRequestResponse(ExpertRequestResponse):
    """Farmer-owned request with the assigned expert, if any."""

    expert: FarmerRequestExpert | None = None


class FarmerExpertRequestPage(BaseModel):
    items: list[FarmerExpertRequestResponse]
    total: int
    limit: int
    offset: int


class ExpertRequestFeedback(BaseModel):
    """Farmer's outcome for a completed request."""

    solved: bool
