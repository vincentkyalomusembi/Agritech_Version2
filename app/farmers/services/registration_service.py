from sqlalchemy.orm import Session

from app.auth.security import hash_pin
from app.farmers.exceptions import (
    NationalIDAlreadyExistsError,
    PhoneNumberAlreadyExistsError,
)
from app.farmers.model import Farmer
from app.farmers.repository import FarmerRepository
from app.farmers.schema import FarmerCreate


class RegistrationService:
    """
    Handles farmer registration.
    """

    def __init__(self, db: Session):
        self.repository = FarmerRepository(db)

    def register(
        self,
        farmer_data: FarmerCreate,
    ) -> Farmer:
        """
        Register a new farmer.
        """

        # Check phone number.
        if self.repository.get_by_phone(
            farmer_data.phone_number
        ):
            raise PhoneNumberAlreadyExistsError()

        # Check national ID.
        if self.repository.get_by_national_id(
            farmer_data.national_id
        ):
            raise NationalIDAlreadyExistsError()

        # Create farmer object.
        farmer = Farmer(
            full_name=farmer_data.full_name,
            national_id=farmer_data.national_id,
            phone_number=farmer_data.phone_number,
            pin_hash=hash_pin(farmer_data.pin),
            county_id=farmer_data.county_id,
        )

        # Save farmer.
        return self.repository.create(farmer)