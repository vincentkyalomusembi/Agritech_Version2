from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.staff.model import StaffRole


class StaffLoginRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class StaffTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: StaffRole
    staff_id: UUID


class StaffRefreshRequest(BaseModel):
    refresh_token: str | None = None


class StaffResponse(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    email: str | None
    role: StaffRole
    county_id: UUID | None
    expert_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    phone_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = None
    role: StaffRole = StaffRole.OFFICER
    county_id: UUID | None = None
    expert_id: UUID | None = None


class StaffUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=150)
    email: str | None = None
    role: StaffRole | None = None
    county_id: UUID | None = None
    expert_id: UUID | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
