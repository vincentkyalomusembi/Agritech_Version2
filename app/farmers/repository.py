from uuid import UUID

from sqlalchemy.orm import Session

from app.farmers.model import Farmer


class FarmerRepository:
    """
    Handles all database operations for farmers.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        farmer_id: UUID,
    ) -> Farmer | None:
        """
        Return a farmer using the ID.
        """

        return (
            self.db.query(Farmer)
            .filter(Farmer.id == farmer_id)
            .first()
        )

    def get_by_phone(
        self,
        phone_number: str,
    ) -> Farmer | None:
        """
        Return a farmer using the phone number.
        """

        return (
            self.db.query(Farmer)
            .filter(Farmer.phone_number == phone_number)
            .first()
        )

    def get_by_national_id(
        self,
        national_id: str,
    ) -> Farmer | None:
        """
        Return a farmer using the national ID.
        """

        return (
            self.db.query(Farmer)
            .filter(Farmer.national_id == national_id)
            .first()
        )

    def list_all(self) -> list[Farmer]:
        """
        Return all farmers.
        """

        return (
            self.db.query(Farmer)
            .all()
        )

    def create(
        self,
        farmer: Farmer,
    ) -> Farmer:
        """
        Save a new farmer.
        """

        self.db.add(farmer)
        self.db.commit()
        self.db.refresh(farmer)

        return farmer

    def update(
        self,
        farmer: Farmer,
    ) -> Farmer:
        """
        Save changes to a farmer.
        """

        self.db.commit()
        self.db.refresh(farmer)

        return farmer

    def delete(
        self,
        farmer: Farmer,
    ) -> None:
        """
        Delete a farmer.
        """

        self.db.delete(farmer)
        self.db.commit()