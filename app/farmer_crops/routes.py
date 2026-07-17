from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.farmer_crops.schema import (
    FarmerCropCreate,
    FarmerCropResponse,
)
from app.farmer_crops.services.farmer_crop_service import (
    FarmerCropService,
)

router = APIRouter(
    prefix="/farmer-crops",
    tags=["Farmer Crops"],
)


@router.post(
    "/",
    response_model=FarmerCropResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_crop(
    crop: FarmerCropCreate,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Register a crop for the logged-in farmer.
    """

    service = FarmerCropService(db)

    return service.add_crop(
        farmer_id=current_farmer.id,
        crop_data=crop,
    )


@router.get(
    "/",
    response_model=list[FarmerCropResponse],
)
def get_my_crops(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Return all crops for the logged-in farmer.
    """

    service = FarmerCropService(db)

    return service.list_crops(
        farmer_id=current_farmer.id,
    )


@router.delete(
    "/{farmer_crop_id}",
)
def delete_crop(
    farmer_crop_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Delete a farmer crop.
    """

    service = FarmerCropService(db)

    service.remove_crop(
        farmer_crop_id=farmer_crop_id,
        farmer_id=current_farmer.id,
    )

    return {
        "message": "Crop deleted successfully.",
    }