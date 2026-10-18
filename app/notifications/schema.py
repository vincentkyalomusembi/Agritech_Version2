from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.notifications.model import NotificationType


class NotificationCreate(BaseModel):
    """Data required to create a notification record."""

    farmer_id: UUID
    notification_type: NotificationType
    title: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1)


class NotificationResponse(BaseModel):
    """Notification data returned to clients."""

    id: UUID
    farmer_id: UUID
    notification_type: NotificationType
    title: str
    message: str
    is_sent: bool
    sent_at: datetime | None
    delivery_status: str
    created_at: datetime
    read_at: datetime | None = None

    @computed_field
    @property
    def read(self) -> bool:
        return self.read_at is not None

    model_config = {
        "from_attributes": True,
    }


class NotificationListResponse(BaseModel):
    """Paginated-ready list wrapper for notifications."""

    items: list[NotificationResponse]
    total: int
    limit: int | None = None
    offset: int = 0
    unread_count: int = 0


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkAllReadResponse(BaseModel):
    updated: int
