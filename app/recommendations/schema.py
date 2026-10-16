from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from app.recommendations.model import RecommendationType


class RecommendationSMSDeliveryResponse(BaseModel):
    id: UUID
    recipient_phone: str
    provider_message_id: str | None
    status: str
    failure_reason: str | None
    submitted_at: datetime
    delivered_at: datetime | None

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    id: UUID
    recommendation_type: RecommendationType
    title: str
    recommendation_text: str
    recommendation_data: dict | None
    crop_variety_id: UUID | None = None
    livestock_breed_id: UUID | None = None
    vendor_product_id: UUID | None = None
    ai_provider: str
    is_sent: bool
    sms_deliveries: list[RecommendationSMSDeliveryResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationGenerateRequest(BaseModel):
    """Answers collected by the frontend for a new farmer recommendation."""

    kind: str = Field(pattern=r"^(crop|livestock)$")
    answers: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
