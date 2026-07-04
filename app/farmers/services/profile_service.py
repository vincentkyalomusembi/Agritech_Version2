from uuid import UUID

from sqlalchemy.orm import Session

from app.farmers.exceptions import (
    FarmerNotFoundError,
    PhoneNumberAlreadyExistsError,
)
from app.farmers.model import Farmer
from app.farmers.repository import FarmerRepository
from app.farmers.schema import FarmerUpdate


class ProfileService:
    """
    Handles farmer profile operations.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.repository = FarmerRepository(db)

    def get_profile(
        self,
        farmer_id: UUID,
    ) -> Farmer:
        """
        Return a farmer profile.
        """

        farmer = self.repository.get_by_id(farmer_id)

        if farmer is None:
            raise FarmerNotFoundError()

        return farmer

    def update_profile(
        self,
        farmer_id: UUID,
        update_data: FarmerUpdate,
    ) -> Farmer:
        """
        Update a farmer profile.
        """

        farmer = self.repository.get_by_id(farmer_id)

        if farmer is None:
            raise FarmerNotFoundError()

        # Check if the new phone number already exists.
        if (
            update_data.phone_number
            and update_data.phone_number != farmer.phone_number
        ):
            existing = self.repository.get_by_phone(
                update_data.phone_number
            )

            if existing:
                raise PhoneNumberAlreadyExistsError()

            farmer.phone_number = update_data.phone_number

        # Update full name.
        if update_data.full_name is not None:
            farmer.full_name = update_data.full_name

        # Update county.
        if update_data.county_id is not None:
            farmer.county_id = update_data.county_id

        return self.repository.update(farmer)

    def delete_profile(
        self,
        farmer_id: UUID,
    ) -> None:
        """
        Delete a farmer account.
        """

        farmer = self.repository.get_by_id(farmer_id)

        if farmer is None:
            raise FarmerNotFoundError()

        self.repository.delete(farmer)

    def list_farmers(
        self,
    ) -> list[Farmer]:
        """
        Return all farmers.
        """

        return self.repository.list_all()