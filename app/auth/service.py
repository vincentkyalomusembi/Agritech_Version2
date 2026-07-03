from sqlalchemy.orm import Session

from app.auth.schema import LoginRequest, TokenResponse
from app.auth.security import (
    verify_pin,
    create_access_token,
)
from app.farmers.model import Farmer


def authenticate_farmer(
    db: Session,
    phone_number: str,
    pin: str,
) -> Farmer | None:
    """
    Return the farmer if the credentials are valid.
    """

    # Find farmer using phone number.
    farmer = (
        db.query(Farmer)
        .filter(Farmer.phone_number == phone_number)
        .first()
    )

    if farmer is None:
        return None

    # Verify the entered PIN.
    if not verify_pin(pin, farmer.pin_hash):
        return None

    return farmer


def login_farmer(
    db: Session,
    login_data: LoginRequest,
) -> TokenResponse:
    """
    Authenticate farmer and return a JWT.
    """

    farmer = authenticate_farmer(
        db=db,
        phone_number=login_data.phone_number,
        pin=login_data.pin,
    )

    if farmer is None:
        raise ValueError("Invalid phone number or PIN.")

    access_token = create_access_token(
        {
            "farmer_id": str(farmer.id)
        }
    )

    return TokenResponse(
        access_token=access_token
    )