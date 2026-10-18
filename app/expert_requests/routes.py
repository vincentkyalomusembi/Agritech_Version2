from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    ExpertRequestFeedback,
    ExpertRequestResponse,
    ExpertRequestStatusUpdate,
    FarmerExpertRequestPage,
    FarmerExpertRequestResponse,
    FarmerRequestExpert,
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


# ── Farmer-owned request history ─────────────────────────────────────

def _farmer_view(request: ExpertRequest) -> FarmerExpertRequestResponse:
    """Farmers see the expert's phone only after the expert accepts."""
    expert = None
    if request.expert is not None:
        show_phone = request.status in {RequestStatus.ACCEPTED, RequestStatus.COMPLETED}
        expert = FarmerRequestExpert(
            id=request.expert.id,
            full_name=request.expert.full_name,
            expert_type=getattr(request.expert.expert_type, "value", request.expert.expert_type),
            organization=request.expert.organization,
            phone_number=request.expert.phone_number if show_phone else None,
        )
    return FarmerExpertRequestResponse(**ExpertRequestResponse.model_validate(request).model_dump(), expert=expert)


@router.get("/farmers/me/expert-requests", response_model=FarmerExpertRequestPage)
def list_my_expert_requests(
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    open_only: bool = Query(default=False, alias="open"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """The signed-in farmer's requests, newest first. `open=true` counts unfinished ones."""
    rows, total = ExpertRequestService(db).list_for_farmer(current_farmer.id, status_filter, open_only, limit, offset)
    return FarmerExpertRequestPage(items=[_farmer_view(row) for row in rows], total=total, limit=limit, offset=offset)


@router.get("/farmers/me/expert-requests/{request_id}", response_model=FarmerExpertRequestResponse)
def get_my_expert_request(
    request_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    try:
        return _farmer_view(ExpertRequestService(db).get_for_farmer(request_id, current_farmer.id))
    except ExpertRequestError as exc:
        raise _handle_expert_request_error(exc)


@router.post("/farmers/me/expert-requests/{request_id}/cancel", response_model=FarmerExpertRequestResponse)
def cancel_my_expert_request(
    request_id: UUID,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Cancel an unfinished request; any offered or assigned expert is told by SMS."""
    try:
        return _farmer_view(ExpertRequestService(db).cancel_for_farmer(request_id, current_farmer))
    except ExpertRequestError as exc:
        raise _handle_expert_request_error(exc)


@router.post("/farmers/me/expert-requests/{request_id}/feedback", response_model=FarmerExpertRequestResponse)
def give_expert_request_feedback(
    request_id: UUID,
    payload: ExpertRequestFeedback,
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Same outcome as replying SOLVED/UNSOLVED by SMS; unsolved escalates to support."""
    try:
        return _farmer_view(ExpertRequestService(db).feedback_for_farmer(request_id, current_farmer, payload.solved))
    except ExpertRequestError as exc:
        raise _handle_expert_request_error(exc)
