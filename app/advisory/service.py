"""
Advisory — Service Layer
=========================
Business logic for creating, reading, and managing advisory messages.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.advisory.model import Advisory, AdvisoryCategory
from app.advisory.repository import AdvisoryRepository
from app.advisory.schema import AdvisoryCreate, AdvisoryUpdate


class AdvisoryService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvisoryRepository(db)

    # ------------------------------------------------------------------ #
    #  Create                                                              #
    # ------------------------------------------------------------------ #

    def create(self, data: AdvisoryCreate) -> Advisory:
        advisory = Advisory(
            title=data.title,
            category=data.category,
            county_id=data.county_id,
            message=data.message,
            is_active=data.is_active,
        )
        return self.repo.create(advisory)

    # ------------------------------------------------------------------ #
    #  Read                                                                #
    # ------------------------------------------------------------------ #

    def get_all(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Advisory]:
        return self.repo.get_all(active_only=active_only, limit=limit, offset=offset)

    def get_by_id(self, advisory_id: UUID) -> Advisory:
        advisory = self.repo.get_by_id(advisory_id)
        if not advisory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisory {advisory_id} not found.",
            )
        return advisory

    def get_by_county(self, county_id: UUID) -> list[Advisory]:
        """
        Returns advisories for the specific county PLUS national advisories
        (those with county_id = NULL).
        """
        return self.repo.get_by_county(county_id)

    def get_by_category(self, category: AdvisoryCategory) -> list[Advisory]:
        return self.repo.get_by_category(category)

    # ------------------------------------------------------------------ #
    #  Update                                                              #
    # ------------------------------------------------------------------ #

    def update(self, advisory_id: UUID, data: AdvisoryUpdate) -> Advisory:
        advisory = self.get_by_id(advisory_id)  # raises 404 if not found

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(advisory, field, value)

        return self.repo.update(advisory)

    # ------------------------------------------------------------------ #
    #  Delete                                                              #
    # ------------------------------------------------------------------ #

    def delete(self, advisory_id: UUID) -> None:
        advisory = self.get_by_id(advisory_id)
        self.repo.delete(advisory)
