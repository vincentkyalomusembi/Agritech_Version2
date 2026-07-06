from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

import app.models  # noqa: F401 — register all SQLAlchemy mappers
from app.experts.model import Expert, ExpertType

DEFAULT_LIST_LIMIT = 100


class ExpertRepository:
    """Handles all database operations for experts."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, expert_id: UUID) -> Expert | None:
        """Return an expert by primary key."""

        return (
            self.db.query(Expert)
            .filter(Expert.id == expert_id)
            .first()
        )

    def list_filtered(
        self,
        county_id: UUID | None = None,
        expert_type: ExpertType | None = None,
        is_available: bool | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Expert]:
        """
        Return experts matching optional filters.

        Uses indexed columns: county_id, expert_type, is_available.
        """

        query = self.db.query(Expert)

        if county_id is not None:
            query = query.filter(Expert.county_id == county_id)

        if expert_type is not None:
            query = query.filter(Expert.expert_type == expert_type)

        if is_available is not None:
            query = query.filter(Expert.is_available == is_available)

        query = query.order_by(Expert.full_name.asc())

        if offset:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count_filtered(
        self,
        county_id: UUID | None = None,
        expert_type: ExpertType | None = None,
        is_available: bool | None = None,
    ) -> int:
        """Return total count for the same filter set (pagination support)."""

        query = self.db.query(func.count(Expert.id))

        if county_id is not None:
            query = query.filter(Expert.county_id == county_id)

        if expert_type is not None:
            query = query.filter(Expert.expert_type == expert_type)

        if is_available is not None:
            query = query.filter(Expert.is_available == is_available)

        return query.scalar() or 0
