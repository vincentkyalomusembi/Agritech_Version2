from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.experts.model import ExpertType


class ExpertResponse(BaseModel):
    """Expert data returned to clients."""

    id: UUID
    full_name: str
    phone_number: str
    expert_type: ExpertType
    county_id: UUID
    organization: str
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ExpertListResponse(BaseModel):
    """Paginated-ready list wrapper for experts."""

    items: list[ExpertResponse]
    total: int
    limit: int | None = None
    offset: int = 0
