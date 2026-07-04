from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db

from app.farmers.schema import (
    FarmerCreate,
    FarmerLogin,
    FarmerUpdate,
    ChangePinRequest,
    FarmerResponse,
    TokenResponse,
)

from app.farmers.services.registration_service import (
    RegistrationService,
)
from app.farmers.services.authentication_service import (
    AuthenticationService,
)
from app.farmers.services.profile_service import (
    ProfileService,
)
from app.farmers.services.reset_pin_service import (
    ResetPinService,
)

router = APIRouter(
    prefix="/farmers",
    tags=["Farmers"],
)


@router.post(
    "/register",
    response_model=FarmerResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_farmer(
    farmer: FarmerCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new farmer.
    """

    service = RegistrationService(db)

    return service.register(farmer)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_farmer(
    login_data: FarmerLogin,
    phone_number: str,
    db: Session = Depends(get_db),
):
    """
    Authenticate a farmer.
    """

    service = AuthenticationService(db)

    token = service.login(
        phone_number=phone_number,
        pin=login_data.pin,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get(
    "/{farmer_id}",
    response_model=FarmerResponse,
)
def get_farmer(
    farmer_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Retrieve one farmer.
    """

    service = ProfileService(db)

    return service.get_profile(farmer_id)


@router.put(
    "/{farmer_id}",
    response_model=FarmerResponse,
)
def update_farmer(
    farmer_id: UUID,
    farmer: FarmerUpdate,
    db: Session = Depends(get_db),
):
    """
    Update farmer profile.
    """

    service = ProfileService(db)

    return service.update_profile(
        farmer_id,
        farmer,
    )


@router.put(
    "/{farmer_id}/change-pin",
)
def change_pin(
    farmer_id: UUID,
    request: ChangePinRequest,
    db: Session = Depends(get_db),
):
    """
    Change farmer PIN.
    """

    service = ResetPinService(db)

    service.change_pin(
        farmer_id,
        request.current_pin,
        request.new_pin,
    )

    return {
        "message": "PIN updated successfully."
    }


@router.delete(
    "/{farmer_id}",
)
def delete_farmer(
    farmer_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Deactivate a farmer account.
    """

    service = ProfileService(db)

    service.delete_profile(farmer_id)

    return {
        "message": "Farmer deleted successfully."
    }


@router.get(
    "/",
    response_model=list[FarmerResponse],
)
def get_all_farmers(
    db: Session = Depends(get_db),
):
    """
    Retrieve all farmers.
    """

    service = ProfileService(db)

    return service.get_all_profiles()