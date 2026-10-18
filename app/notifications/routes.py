from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.auth.dependencies import get_current_farmer
from app.farmers.model import Farmer
from app.notifications.exceptions import FarmerIdRequiredError, NotificationError
from app.notifications.model import NotificationType
from app.notifications.schema import MarkAllReadResponse, NotificationListResponse, NotificationResponse, UnreadCountResponse
from app.notifications.services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "/",
    response_model=NotificationListResponse,
)
def list_notifications(
    farmer_id: UUID | None = Query(default=None),
    notification_type: NotificationType | None = Query(default=None),
    is_sent: bool | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """
    List notifications with optional filters.

    Supports farmer_id, notification_type, and is_sent.
    """

    if farmer_id is not None and farmer_id != current_farmer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own notifications.",
        )

    service = NotificationService(db)

    try:
        return service.list_notifications(
            farmer_id=current_farmer.id,
            notification_type=notification_type,
            is_sent=is_sent,
            limit=limit,
            offset=offset,
        )

    except FarmerIdRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except NotificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_notification_count(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Badge count for the signed-in farmer's unread notifications."""
    return UnreadCountResponse(unread_count=NotificationService(db).unread_count(current_farmer.id))


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
def mark_all_notifications_read(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    return MarkAllReadResponse(updated=NotificationService(db).mark_all_read(current_farmer.id))


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    notification = NotificationService(db).mark_read(notification_id, current_farmer.id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return NotificationResponse.model_validate(notification)
