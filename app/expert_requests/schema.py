from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.expert_requests.model import RequestStatus


class ExpertRequestCreate(BaseModel):
    """Data required to submit an expert request."""

    farmer_id: UUID
    expert_id: UUID
    issue_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    preferred_visit_date: datetime | None = None


class ExpertRequestStatusUpdate(BaseModel):
    """Data required to update an expert request status."""

    request_id: UUID
    status: RequestStatus


class ExpertRequestResponse(BaseModel):
    """Expert request data returned to clients."""

    id: UUID
    farmer_id: UUID
    expert_id: UUID
    issue_type: str
    description: str
    status: RequestStatus
    preferred_visit_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }
