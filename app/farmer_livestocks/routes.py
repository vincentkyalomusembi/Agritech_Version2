from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.farmer_livestocks.schema import (
    FarmerLivestockCreate,
    FarmerLivestockResponse,
)
from app.farmer_livestocks.services.farmer_livestock_service import (
    FarmerLivestockService,
)

router = APIRouter(
    prefix="/farmer-livestock",
    tags=["Farmer Livestock"],
)


@router.post(
    "/",
    response_model=FarmerLivestockResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_livestock(
    livestock: FarmerLivestockCreate,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Register livestock for the logged-in farmer.
    """

    service = FarmerLivestockService(db)

    return service.add_livestock(
        farmer_id=current_farmer.id,
        livestock_data=livestock,
    )


@router.get(
    "/",
    response_model=list[FarmerLivestockResponse],
)
def get_my_livestock(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Return all livestock for the logged-in farmer.
    """

    service = FarmerLivestockService(db)

    return service.list_livestock(
        farmer_id=current_farmer.id,
    )


@router.delete(
    "/{farmer_livestock_id}",
)
def delete_livestock(
    farmer_livestock_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Delete one livestock record.
    """

    service = FarmerLivestockService(db)

    service.remove_livestock(
        farmer_livestock_id=farmer_livestock_id,
        farmer_id=current_farmer.id,
    )

    return {
        "message": "Livestock deleted successfully.",
    }