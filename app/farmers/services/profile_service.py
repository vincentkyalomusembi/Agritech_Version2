from uuid import UUID

from sqlalchemy.orm import Session

from app.farmers.exceptions import (
    FarmerNotFoundError,
    PhoneNumberAlreadyExistsError,
)
from app.farmers.model import Farmer
from app.farmers.repository import FarmerRepository
from app.farmers.schema import FarmerUpdate
from app.counties.model import Constituency, Ward
from sqlalchemy import func


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

        county_id = update_data.county_id or farmer.county_id
        county_changed = update_data.county_id is not None and update_data.county_id != farmer.county_id

        # Update county and clear stale locality selections if it changed.
        if update_data.county_id is not None:
            farmer.county_id = update_data.county_id
            if county_changed:
                for field in ("latitude", "longitude", "sub_county", "ward", "constituency_id", "ward_id"):
                    if field not in update_data.model_fields_set:
                        setattr(farmer, field, None)

        old_constituency_id = farmer.constituency_id
        constituency_id = update_data.constituency_id if "constituency_id" in update_data.model_fields_set else farmer.constituency_id
        if "sub_county" in update_data.model_fields_set and update_data.sub_county:
            if "constituency_id" not in update_data.model_fields_set:
                constituency = self.repository.db.query(Constituency).filter(
                    Constituency.county_id == county_id,
                    func.lower(Constituency.name) == update_data.sub_county.strip().lower(),
                ).first()
                if constituency is None:
                    raise ValueError("Selected constituency/sub-county is not in the selected county.")
                constituency_id = constituency.id
            farmer.sub_county = update_data.sub_county.strip()
        elif "sub_county" in update_data.model_fields_set:
            farmer.sub_county = None

        # A ward selection identifies its parent constituency. This lets clients
        # submit just ward_id without having to duplicate the hierarchy lookup.
        if "ward_id" in update_data.model_fields_set and update_data.ward_id is not None and "constituency_id" not in update_data.model_fields_set:
            selected_ward = self.repository.db.query(Ward).filter_by(id=update_data.ward_id).first()
            if selected_ward is None:
                raise ValueError("Selected ward was not found.")
            constituency_id = selected_ward.constituency_id

        constituency = None
        if constituency_id is not None:
            constituency = self.repository.db.query(Constituency).filter_by(id=constituency_id).first()
            if constituency is None or constituency.county_id != county_id:
                raise ValueError("Selected constituency/sub-county is not in the selected county.")
        farmer.constituency_id = constituency.id if constituency else None
        if constituency is not None:
            farmer.sub_county = constituency.name
        if constituency_id != old_constituency_id and "ward_id" not in update_data.model_fields_set and "ward" not in update_data.model_fields_set:
            farmer.ward_id = None
            farmer.ward = None

        ward_id = update_data.ward_id if "ward_id" in update_data.model_fields_set else farmer.ward_id
        if "ward" in update_data.model_fields_set and update_data.ward:
            if "ward_id" not in update_data.model_fields_set:
                if constituency is None:
                    raise ValueError("Select a constituency/sub-county before selecting a ward.")
                ward = self.repository.db.query(Ward).filter(
                    Ward.constituency_id == constituency.id,
                    func.lower(Ward.name) == update_data.ward.strip().lower(),
                ).first()
                if ward is None:
                    raise ValueError("Selected ward is not in the selected constituency/sub-county.")
                ward_id = ward.id
            farmer.ward = update_data.ward.strip()
        elif "ward" in update_data.model_fields_set:
            farmer.ward = None

        if ward_id is not None:
            ward = self.repository.db.query(Ward).filter_by(id=ward_id).first()
            if ward is None or ward.constituency_id != farmer.constituency_id:
                raise ValueError("Selected ward is not in the selected constituency/sub-county.")
            farmer.ward = ward.name
        elif "ward_id" in update_data.model_fields_set:
            farmer.ward = None
        farmer.ward_id = ward_id

        for field in ("latitude", "longitude"):
            if field in update_data.model_fields_set:
                setattr(farmer, field, getattr(update_data, field))

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
