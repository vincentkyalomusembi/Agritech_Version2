from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.notifications.exceptions import FarmerIdRequiredError
from app.notifications.model import Notification, NotificationType
from app.notifications.repository import (
    DEFAULT_LIST_LIMIT,
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_SENT,
    NotificationRepository,
)
from app.notifications.schema import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
)


class NotificationService:
    """
    Business logic for creating and listing notifications.

    Reusable by expert requests, subscriptions, and other modules.
    """

    def __init__(self, db: Session):
        self.repository = NotificationRepository(db)
        self.db = db

    def create_notification(
        self,
        data: NotificationCreate,
        *,
        commit: bool = True,
    ) -> Notification:
        """
        Create a notification record.

        Set commit=False when called inside a larger transaction.
        """

        notification = Notification(
            farmer_id=data.farmer_id,
            notification_type=data.notification_type,
            title=data.title,
            message=data.message,
            is_sent=False,
            delivery_status=DELIVERY_STATUS_PENDING,
        )

        created = self.repository.create(notification)

        if commit:
            self.db.commit()

        return created

    def mark_as_sent(
        self,
        notification_id: UUID,
        *,
        commit: bool = True,
    ) -> Notification:
        """
        Mark a notification as sent.

        Intended for Member 4's Africa's Talking SMS dispatch flow.
        """

        notification = self.repository.get_by_id(notification_id)
        if notification is None:
            from app.notifications.exceptions import NotificationNotFoundError

            raise NotificationNotFoundError()

        notification.is_sent = True
        notification.sent_at = datetime.now(timezone.utc)
        notification.delivery_status = DELIVERY_STATUS_SENT

        if commit:
            self.db.commit()
            self.db.refresh(notification)

        return notification

    def create_expert_update_notification(
        self,
        farmer_id: UUID,
        title: str,
        message: str,
        *,
        commit: bool = True,
    ) -> Notification:
        """Create an expert-request status notification for a farmer."""

        return self.create_notification(
            NotificationCreate(
                farmer_id=farmer_id,
                notification_type=NotificationType.EXPERT_UPDATE,
                title=title,
                message=message,
            ),
            commit=commit,
        )

    def list_notifications(
        self,
        farmer_id: UUID | None = None,
        notification_type: NotificationType | None = None,
        is_sent: bool | None = None,
        limit: int | None = DEFAULT_LIST_LIMIT,
        offset: int = 0,
    ) -> NotificationListResponse:
        """List notifications with optional filters."""

        if farmer_id is None:
            raise FarmerIdRequiredError()

        effective_limit = limit if limit is not None else DEFAULT_LIST_LIMIT
        if effective_limit > DEFAULT_LIST_LIMIT:
            effective_limit = DEFAULT_LIST_LIMIT

        notifications = self.repository.list_filtered(
            farmer_id=farmer_id,
            notification_type=notification_type,
            is_sent=is_sent,
            limit=effective_limit,
            offset=offset,
        )

        total = self.repository.count_filtered(
            farmer_id=farmer_id,
            notification_type=notification_type,
            is_sent=is_sent,
        )

        return NotificationListResponse(
            items=[
                NotificationResponse.model_validate(notification)
                for notification in notifications
            ],
            total=total,
            limit=effective_limit,
            offset=offset,
        )
