from uuid import UUID

from pydantic import BaseModel, Field


class FarmerLivestockCreate(BaseModel):
    """
    Data required to register livestock for a farmer.
    """

    livestock_id: UUID

    herd_size: int = Field(
        ...,
        gt=0,
        description="Number of animals owned.",
    )


class FarmerLivestockResponse(BaseModel):
    """
    Livestock returned to clients.
    """

    id: UUID
    farmer_id: UUID
    livestock_id: UUID
    herd_size: int

    model_config = {
        "from_attributes": True,
    }