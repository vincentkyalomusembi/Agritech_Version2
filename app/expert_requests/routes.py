from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.auth.dependencies import get_current_farmer, require_admin
from app.staff.dependencies import require_admin_or_staff
from app.farmers.model import Farmer
from app.expert_requests.exceptions import (
    ExpertRequestError,
    ExpertRequestNotFoundError,
    FarmerNotFoundError,
    InvalidStatusTransitionError,
)
from app.expert_requests.schema import (
    ExpertRequestCreate,
    ExpertRequestResponse,
    ExpertRequestStatusUpdate,
)
from app.expert_requests.services.expert_request_service import (
    ExpertRequestService,
)
from app.expert_requests.model import ExpertRequest, RequestStatus
from app.experts.exceptions import ExpertNotFoundError, ExpertUnavailableError

router = APIRouter(
    tags=["Expert Requests"],
)


@router.get("/expert-requests", response_model=list[ExpertRequestResponse])
def list_managed_expert_requests(
    status_filter: RequestStatus | None = None,
    _: Farmer | object = Depends(require_admin_or_staff),
    db: Session = Depends(get_db),
):
    query = db.query(ExpertRequest)
    if status_filter is not None:
        query = query.filter(ExpertRequest.status == status_filter)
    return [ExpertRequestResponse.model_validate(item) for item in query.order_by(ExpertRequest.created_at.desc()).limit(200).all()]


def _handle_expert_request_error(exc: ExpertRequestError) -> HTTPException:
    """Map domain exceptions to HTTP responses."""

    if isinstance(exc, (ExpertRequestNotFoundError, ExpertNotFoundError)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, FarmerNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(
        exc,
        (InvalidStatusTransitionError, ExpertUnavailableError),
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


@router.post(
    "/expert-request",
    response_model=ExpertRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expert_request(
    payload: ExpertRequestCreate,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Submit a new expert assistance request."""

    payload.farmer_id = current_farmer.id

    service = ExpertRequestService(db)

    try:
        return service.create_request(payload)

    except ExpertRequestError as exc:
        raise _handle_expert_request_error(exc)

    except ExpertNotFoundError as exc:
        raise _handle_expert_request_error(exc)

    except ExpertUnavailableError as exc:
        raise _handle_expert_request_error(exc)


@router.patch(
    "/expert-request/status",
    response_model=ExpertRequestResponse,
)
def update_expert_request_status(
    payload: ExpertRequestStatusUpdate,
    _: Farmer | object = Depends(require_admin_or_staff),
    db: Session = Depends(get_db),
):
    """Update request status; expert/admin identity is required."""

    service = ExpertRequestService(db)

    try:
        return service.update_status(payload)

    except ExpertRequestError as exc:
        raise _handle_expert_request_error(exc)

    except ExpertUnavailableError as exc:
        raise _handle_expert_request_error(exc)
