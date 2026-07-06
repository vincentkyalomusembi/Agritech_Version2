from uuid import UUID

from sqlalchemy.orm import Session

import app.models  # noqa: F401 — register all SQLAlchemy mappers
from app.expert_requests.model import ExpertRequest


class ExpertRequestRepository:
    """Handles all database operations for expert requests."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, request_id: UUID) -> ExpertRequest | None:
        """Return an expert request by primary key."""

        return (
            self.db.query(ExpertRequest)
            .filter(ExpertRequest.id == request_id)
            .first()
        )

    def get_by_id_for_update(self, request_id: UUID) -> ExpertRequest | None:
        """Return a row-locked expert request for safe concurrent updates."""

        return (
            self.db.query(ExpertRequest)
            .filter(ExpertRequest.id == request_id)
            .with_for_update()
            .first()
        )

    def create(self, request: ExpertRequest) -> ExpertRequest:
        """Persist a new expert request."""

        self.db.add(request)
        self.db.flush()
        self.db.refresh(request)

        return request

    def update(self, request: ExpertRequest) -> ExpertRequest:
        """Flush pending changes to an expert request."""

        self.db.flush()
        self.db.refresh(request)

        return request
