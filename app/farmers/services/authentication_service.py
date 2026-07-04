from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    verify_pin,
)
from app.farmers.exceptions import (
    FarmerNotFoundError,
    InactiveFarmerError,
    InvalidPinError,
)
from app.farmers.repository import FarmerRepository


class AuthenticationService:
    """
    Handles farmer authentication.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.repository = FarmerRepository(db)

    def login(
        self,
        phone_number: str,
        pin: str,
    ) -> str:
        """
        Authenticate a farmer and return a JWT.
        """

        # Find farmer by phone number.
        farmer = self.repository.get_by_phone(
            phone_number
        )

        if farmer is None:
            raise FarmerNotFoundError()

        # Ensure the account is active.
        if not farmer.is_active:
            raise InactiveFarmerError()

        # Verify the PIN.
        if not verify_pin(
            pin,
            farmer.pin_hash,
        ):
            raise InvalidPinError()

        # Create a JWT containing the farmer ID.
        token = create_access_token(
            {
                "sub": str(farmer.id),
            }
        )

        return token