from uuid import UUID

from sqlalchemy.orm import Session

from app.farmer_crops.model import FarmerCrop


class FarmerCropRepository:
    """
    Handles FarmerCrop database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        farmer_crop: FarmerCrop,
    ) -> FarmerCrop:
        """
        Save a farmer crop.
        """

        self.db.add(farmer_crop)
        self.db.commit()
        self.db.refresh(farmer_crop)

        return farmer_crop

    def crop_exists(
        self,
        farmer_id: UUID,
        crop_id: UUID,
    ) -> bool:
        """
        Check if the farmer already registered the crop.
        """

        return (
            self.db.query(FarmerCrop)
            .filter(
                FarmerCrop.farmer_id == farmer_id,
                FarmerCrop.crop_id == crop_id,
            )
            .first()
            is not None
        )

    def get_farmer_crops(
        self,
        farmer_id: UUID,
    ) -> list[FarmerCrop]:
        """
        Return all crops belonging to a farmer.
        """

        return (
            self.db.query(FarmerCrop)
            .filter(
                FarmerCrop.farmer_id == farmer_id,
            )
            .all()
        )

    def get_by_id(
        self,
        farmer_crop_id: UUID,
        farmer_id: UUID,
    ) -> FarmerCrop | None:
        """
        Return one farmer crop.
        """

        return (
            self.db.query(FarmerCrop)
            .filter(
                FarmerCrop.id == farmer_crop_id,
                FarmerCrop.farmer_id == farmer_id,
            )
            .first()
        )

    def delete(
        self,
        farmer_crop: FarmerCrop,
    ) -> None:
        """
        Delete a farmer crop.
        """

        self.db.delete(farmer_crop)
        self.db.commit()