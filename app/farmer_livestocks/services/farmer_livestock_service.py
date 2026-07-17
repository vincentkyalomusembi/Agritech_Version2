from uuid import UUID

from sqlalchemy.orm import Session

from app.farmer_livestocks.exceptions import (
    FarmerLivestockNotFoundError,
    LivestockAlreadyExistsError,
)
from app.farmer_livestocks.model import FarmerLivestock
from app.farmer_livestocks.repository import (
    FarmerLivestockRepository,
)
from app.farmer_livestocks.schema import (
    FarmerLivestockCreate,
)


class FarmerLivestockService:
    """
    Handles farmer livestock business logic.
    """

    def __init__(
        self,
        db: Session,
    ):
        self.repository = FarmerLivestockRepository(db)

    def add_livestock(
        self,
        farmer_id: UUID,
        livestock_data: FarmerLivestockCreate,
    ) -> FarmerLivestock:
        """
        Register livestock for a farmer.
        """

        # Prevent duplicate livestock registration.
        if self.repository.livestock_exists(
            farmer_id,
            livestock_data.livestock_id,
        ):
            raise LivestockAlreadyExistsError()

        # Create livestock record.
        farmer_livestock = FarmerLivestock(
            farmer_id=farmer_id,
            livestock_id=livestock_data.livestock_id,
            herd_size=livestock_data.herd_size,
        )

        return self.repository.create(
            farmer_livestock,
        )

    def list_livestock(
        self,
        farmer_id: UUID,
    ) -> list[FarmerLivestock]:
        """
        Return all livestock owned by a farmer.
        """

        return self.repository.get_farmer_livestock(
            farmer_id,
        )

    def remove_livestock(
        self,
        farmer_livestock_id: UUID,
        farmer_id: UUID,
    ) -> None:
        """
        Delete farmer livestock.
        """

        farmer_livestock = self.repository.get_by_id(
            farmer_livestock_id,
            farmer_id,
        )

        if farmer_livestock is None:
            raise FarmerLivestockNotFoundError()

        self.repository.delete(
            farmer_livestock,
        )