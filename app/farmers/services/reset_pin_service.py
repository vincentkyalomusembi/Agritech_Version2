from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.security import (
    hash_pin,
    verify_pin,
)
from app.farmers.exceptions import (
    FarmerNotFoundError,
    InvalidPinError,
)
from app.farmers.repository import FarmerRepository


class ResetPinService:
    """
    Handles PIN changes.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.repository = FarmerRepository(db)

    def change_pin(
        self,
        farmer_id: UUID,
        current_pin: str,
        new_pin: str,
    ) -> None:
        """
        Change a farmer PIN.
        """

        # Find the farmer.
        farmer = self.repository.get_by_id(farmer_id)

        if farmer is None:
            raise FarmerNotFoundError()

        # Verify the current PIN.
        if not verify_pin(
            current_pin,
            farmer.pin_hash,
        ):
            raise InvalidPinError()

        # Hash and save the new PIN.
        farmer.pin_hash = hash_pin(new_pin)

        self.repository.update(farmer)