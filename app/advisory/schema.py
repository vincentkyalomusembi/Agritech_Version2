"""
Advisory — Pydantic Schemas
============================
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.advisory.model import AdvisoryCategory


# ------------------------------------------------------------------ #
#  Request schemas                                                     #
# ------------------------------------------------------------------ #

class AdvisoryCreate(BaseModel):
    """
    Payload for creating a new advisory.
    county_id is optional — if omitted the advisory applies to all counties.
    """
    title: str = Field(..., min_length=3, max_length=200)
    category: AdvisoryCategory
    county_id: UUID | None = None
    message: str = Field(..., min_length=10)
    is_active: bool = True


class AdvisoryUpdate(BaseModel):
    """
    Partial update — all fields optional.
    """
    title: str | None = Field(default=None, min_length=3, max_length=200)
    category: AdvisoryCategory | None = None
    county_id: UUID | None = None
    message: str | None = Field(default=None, min_length=10)
    is_active: bool | None = None


# ------------------------------------------------------------------ #
#  Response schema                                                     #
# ------------------------------------------------------------------ #

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
