from uuid import UUID

from pydantic import BaseModel, Field


class FarmerCropCreate(BaseModel):
    """
    Data required to register a crop for a farmer.
    """

    crop_id: UUID

    farm_size: float = Field(
        ...,
        gt=0,
    )

    soil_type: str = Field(
        ...,
        min_length=3,
        max_length=100,
    )

    experience_level: str = Field(
        ...,
        min_length=3,
        max_length=50,
    )


class FarmerCropResponse(BaseModel):
    """
    Farmer crop returned to clients.
    """

    id: UUID
    farmer_id: UUID
    crop_id: UUID
    farm_size: float
    soil_type: str
    experience_level: str

    model_config = {
        "from_attributes": True,
    }