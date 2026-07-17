from uuid import UUID

from sqlalchemy.orm import Session

from app.farmer_livestock.model import FarmerLivestock


class FarmerLivestockRepository:
    """
    Handles FarmerLivestock database operations.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def create(
        self,
        farmer_livestock: FarmerLivestock,
    ) -> FarmerLivestock:
        """
        Save farmer livestock.
        """

        self.db.add(farmer_livestock)
        self.db.commit()
        self.db.refresh(farmer_livestock)

        return farmer_livestock

    def livestock_exists(
        self,
        farmer_id: UUID,
        livestock_id: UUID,
    ) -> bool:
        """
        Check whether the farmer already registered this livestock.
        """

        return (
            self.db.query(FarmerLivestock)
            .filter(
                FarmerLivestock.farmer_id == farmer_id,
                FarmerLivestock.livestock_id == livestock_id,
            )
            .first()
            is not None
        )

    def get_farmer_livestock(
        self,
        farmer_id: UUID,
    ) -> list[FarmerLivestock]:
        """
        Return all livestock belonging to a farmer.
        """

        return (
            self.db.query(FarmerLivestock)
            .filter(
                FarmerLivestock.farmer_id == farmer_id,
            )
            .all()
        )

    def get_by_id(
        self,
        farmer_livestock_id: UUID,
        farmer_id: UUID,
    ) -> FarmerLivestock | None:
        """
        Return one livestock record belonging to a farmer.
        """

        return (
            self.db.query(FarmerLivestock)
            .filter(
                FarmerLivestock.id == farmer_livestock_id,
                FarmerLivestock.farmer_id == farmer_id,
            )
            .first()
        )

    def delete(
        self,
        farmer_livestock: FarmerLivestock,
    ) -> None:
        """
        Delete farmer livestock.
        """

        self.db.delete(farmer_livestock)
        self.db.commit()