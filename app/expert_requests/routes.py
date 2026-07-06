from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
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
from app.experts.exceptions import ExpertNotFoundError, ExpertUnavailableError

router = APIRouter(
    tags=["Expert Requests"],
)


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
    db: Session = Depends(get_db),
):
    """Submit a new expert assistance request."""

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
    db: Session = Depends(get_db),
):
    """Update the status of an existing expert request."""

    service = ExpertRequestService(db)

    try:
        return service.update_status(payload)

    except ExpertRequestError as exc:
        raise _handle_expert_request_error(exc)

    except ExpertUnavailableError as exc:
        raise _handle_expert_request_error(exc)
