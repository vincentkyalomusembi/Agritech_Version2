from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LocalizedMessage(BaseModel):
    en: str = Field(min_length=5, max_length=480)
    sw: str = Field(min_length=5, max_length=480)


class SignalCell(BaseModel):
    cell_id: str
    center_lat: float
    center_lng: float
    count: int
    by_symptom: dict[str, int]
    issue_type: str
    week_start: str
    flagged: bool


class Thresholds(BaseModel):
    minimum_count: int = Field(ge=2, le=1000)
    cell_size_deg: float = Field(ge=0.02, le=2.0)


class AlertDraft(BaseModel):
    symptom_code: str = Field(min_length=1, max_length=60)
    issue_type: Literal["crop", "livestock"]
    subject_key: str | None = Field(default=None, max_length=60)
    center_lat: float = Field(ge=-4.7, le=5.1)
    center_lng: float = Field(ge=33.9, le=41.9)
    radius_km: float = Field(gt=0, le=200)
    message: LocalizedMessage


class AlertResponse(BaseModel):
    id: UUID
    symptom_code: str
    issue_type: str
    subject_key: str | None
    center_lat: float
    center_lng: float
    radius_km: float
    message: LocalizedMessage
    status: str
    recipient_count: int
    created_by: UUID | None
    created_at: datetime
    expires_at: datetime


class RecipientPreview(BaseModel):
    recipient_count: int
