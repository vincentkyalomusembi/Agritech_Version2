from uuid import UUID

from sqlalchemy.orm import Session

import app.models  # noqa: F401 — register all SQLAlchemy mappers
from app.subscriptions.model import Subscription


class SubscriptionRepository:
    """Handles all database operations for subscriptions."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_farmer_id(self, farmer_id: UUID) -> Subscription | None:
        """Return a farmer's subscription record."""

        return (
            self.db.query(Subscription)
            .filter(Subscription.farmer_id == farmer_id)
            .first()
        )

    def create(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription."""

        self.db.add(subscription)
        self.db.flush()
        self.db.refresh(subscription)

        return subscription

    def update(self, subscription: Subscription) -> Subscription:
        """Flush pending changes to a subscription."""

        self.db.flush()
        self.db.refresh(subscription)

        return subscription
