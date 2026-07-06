from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

import app.models  # noqa: F401 — register all SQLAlchemy mappers
from app.notifications.model import Notification, NotificationType

DEFAULT_LIST_LIMIT = 100
DELIVERY_STATUS_PENDING = "Pending"
DELIVERY_STATUS_SENT = "Sent"


class NotificationRepository:
    """Handles all database operations for notifications."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, notification_id: UUID) -> Notification | None:
        """Return a notification by primary key."""

        return (
            self.db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )

    def create(self, notification: Notification) -> Notification:
        """Persist a new notification."""

        self.db.add(notification)
        self.db.flush()
        self.db.refresh(notification)

        return notification

    def list_filtered(
        self,
        farmer_id: UUID | None = None,
        notification_type: NotificationType | None = None,
        is_sent: bool | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Notification]:
        """
        Return notifications matching optional filters.

        Uses indexed columns: farmer_id, notification_type.
        """

        query = self.db.query(Notification)

        if farmer_id is not None:
            query = query.filter(Notification.farmer_id == farmer_id)

        if notification_type is not None:
            query = query.filter(
                Notification.notification_type == notification_type
            )

        if is_sent is not None:
            query = query.filter(Notification.is_sent == is_sent)

        query = query.order_by(Notification.created_at.desc())

        if offset:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count_filtered(
        self,
        farmer_id: UUID | None = None,
        notification_type: NotificationType | None = None,
        is_sent: bool | None = None,
    ) -> int:
        """Return total count for the same filter set."""

        query = self.db.query(func.count(Notification.id))

        if farmer_id is not None:
            query = query.filter(Notification.farmer_id == farmer_id)

        if notification_type is not None:
            query = query.filter(
                Notification.notification_type == notification_type
            )

        if is_sent is not None:
            query = query.filter(Notification.is_sent == is_sent)

        return query.scalar() or 0
