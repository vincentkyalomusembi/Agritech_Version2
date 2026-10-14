from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from app.recommendations.model import RecommendationType


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
    created_at: datetime

    model_config = {"from_attributes": True}
