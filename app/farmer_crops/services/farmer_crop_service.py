from uuid import UUID

from sqlalchemy.orm import Session

from app.farmer_crops.exceptions import (
    CropAlreadyExistsError,
    FarmerCropNotFoundError,
)
from app.farmer_crops.model import FarmerCrop
from app.farmer_crops.repository import FarmerCropRepository
from app.farmer_crops.schema import FarmerCropCreate


class FarmerCropService:
    """
    Handles farmer crop business logic.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.repository = FarmerCropRepository(db)

    def add_crop(
        self,
        farmer_id: UUID,
        crop_data: FarmerCropCreate,
    ) -> FarmerCrop:
        """
        Register a crop for a farmer.
        """

        # Prevent duplicate crop registration.
        if self.repository.crop_exists(
            farmer_id,
            crop_data.crop_id,
        ):
            raise CropAlreadyExistsError()

        # Create farmer crop.
        farmer_crop = FarmerCrop(
            farmer_id=farmer_id,
            crop_id=crop_data.crop_id,
            farm_size=crop_data.farm_size,
            soil_type=crop_data.soil_type,
            experience_level=crop_data.experience_level,
        )

        return self.repository.create(farmer_crop)

    def list_crops(
        self,
        farmer_id: UUID,
    ) -> list[FarmerCrop]:
        """
        Return all crops for a farmer.
        """

        return self.repository.get_farmer_crops(
            farmer_id,
        )

    def remove_crop(
        self,
        farmer_crop_id: UUID,
    ) -> None:
        """
        Delete a farmer crop.
        """

        farmer_crop = self.repository.get_by_id(
            farmer_crop_id,
        )

        if farmer_crop is None:
            raise FarmerCropNotFoundError()

        self.repository.delete(farmer_crop)