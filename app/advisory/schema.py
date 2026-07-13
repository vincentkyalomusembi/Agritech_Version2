from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.advisory.model import AdvisoryCategory


class AdvisoryCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    category: AdvisoryCategory
    county_id: UUID | None = None  # omit for national-level advisories
    message: str = Field(..., min_length=10)
    is_active: bool = True


class AdvisoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    category: AdvisoryCategory | None = None
    county_id: UUID | None = None
    message: str | None = Field(default=None, min_length=10)
    is_active: bool | None = None


class AdvisoryResponse(BaseModel):
    id: UUID
    title: str
    category: AdvisoryCategory
    county_id: UUID | None
    message: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
