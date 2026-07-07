from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer

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
    "/me",
    response_model=FarmerResponse,
)
def get_farmer(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Retrieve one farmer.
    """

    service = ProfileService(db)

    return service.get_profile(current_farmer.id)


@router.put(
    "/me",
    response_model=FarmerResponse,
)
def update_farmer(
    farmer: FarmerUpdate,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Update farmer profile.
    """

    service = ProfileService(db)

    return service.update_profile(
        current_farmer.id,
        farmer,
    )


@router.put(
    "/change-pin",
)
def change_pin(
    request: ChangePinRequest,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Change farmer PIN.
    """

    service = ResetPinService(db)

    service.change_pin(
        current_farmer.id,
        request.current_pin,
        request.new_pin,
    )

    return {
        "message": "PIN updated successfully."
    }


@router.delete(
    "/me",
)
def delete_farmer(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    Deactivate a farmer account.
    """

    service = ProfileService(db)

    service.delete_profile(current_farmer.id)

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

    return service.list_farmers()