from uuid import UUID

from sqlalchemy.orm import Session

import app.models  # noqa: F401 - register all SQLAlchemy mappers
from app.recommendations.model import Recommendation


class RecommendationRepository:
    """
    Handles database operations for recommendations.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        recommendation: Recommendation,
    ) -> Recommendation:
        """
        Save a recommendation.
        """

        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)

        return recommendation

    def get_by_id(
        self,
        recommendation_id: UUID,
    ) -> Recommendation | None:
        """
        Return one recommendation by ID.
        """

        return (
            self.db.query(Recommendation)
            .filter(
                Recommendation.id == recommendation_id
            )
            .first()
        )

    def get_by_farmer(
        self,
        farmer_id: UUID,
        limit: int = 20,
    ) -> list[Recommendation]:
        """
        Return recent recommendations for a farmer.
        """

        return (
            self.db.query(Recommendation)
            .filter(
                Recommendation.farmer_id == farmer_id
            )
            .order_by(
                Recommendation.created_at.desc()
            )
            .limit(limit)
            .all()
        )

    def delete(self, recommendation_id: UUID) -> bool:
        """
        Delete a recommendation by ID. Returns True if a row was deleted.
        """
        row = self.get_by_id(recommendation_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True