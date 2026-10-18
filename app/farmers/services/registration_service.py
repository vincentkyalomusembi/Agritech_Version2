from sqlalchemy.orm import Session

from app.auth.security import hash_pin
from app.farmers.exceptions import (
    NationalIDAlreadyExistsError,
    PhoneNumberAlreadyExistsError,
)
from app.counties.model import Constituency, Ward
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

        # Resolve the selected location hierarchy; names follow the chosen IDs.
        sub_county, ward_name = farmer_data.sub_county, farmer_data.ward
        constituency = ward = None
        if farmer_data.constituency_id is not None:
            constituency = self.repository.db.query(Constituency).filter_by(id=farmer_data.constituency_id).first()
            if constituency is None or constituency.county_id != farmer_data.county_id:
                raise ValueError("Sub-county does not belong to the selected county.")
            sub_county = constituency.name
        if farmer_data.ward_id is not None:
            ward = self.repository.db.query(Ward).filter_by(id=farmer_data.ward_id).first()
            if ward is None or constituency is None or ward.constituency_id != constituency.id:
                raise ValueError("Ward does not belong to the selected sub-county.")
            ward_name = ward.name

        # Create farmer object. Web sign-up collects name and county directly,
        # so no SMS profile completion step is needed (unlike USSD sign-up).
        farmer = Farmer(
            full_name=farmer_data.full_name,
            national_id=farmer_data.national_id,
            phone_number=farmer_data.phone_number,
            pin_hash=hash_pin(farmer_data.pin),
            county_id=farmer_data.county_id,
            latitude=farmer_data.latitude,
            longitude=farmer_data.longitude,
            sub_county=sub_county,
            ward=ward_name,
            constituency_id=constituency.id if constituency else None,
            ward_id=ward.id if ward else None,
            profile_complete=True,
        )

        # Save farmer.
        return self.repository.create(farmer)
