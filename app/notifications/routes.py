from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.notifications.exceptions import FarmerIdRequiredError, NotificationError
from app.notifications.model import NotificationType
from app.notifications.schema import NotificationListResponse
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
    db: Session = Depends(get_db),
):
    """
    List notifications with optional filters.

    Supports farmer_id, notification_type, and is_sent.
    """

    service = NotificationService(db)

    try:
        return service.list_notifications(
            farmer_id=farmer_id,
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
