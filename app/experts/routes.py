from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.auth.dependencies import get_current_farmer, get_current_web_user, get_current_expert
from app.farmers.model import Farmer
from app.experts.exceptions import ExpertError, ExpertNotFoundError
from app.experts.model import ExpertType
from app.experts.schema import ExpertContactVerificationUpdate, ExpertListResponse, ExpertResponse
from app.experts.services.expert_service import ExpertService
from app.staff.dependencies import require_admin_or_staff
from app.experts.model import Expert
from app.expert_requests.model import ExpertRequest, RequestStatus
from app.expert_requests.schema import ExpertRequestResponse, ExpertRequestStatusUpdate
from app.expert_requests.services.expert_request_service import ExpertRequestService


class AvailabilityUpdate(BaseModel):
    is_available: bool

router = APIRouter(
    prefix="/experts",
    tags=["Experts"],
)


def _handle_expert_error(exc: ExpertError) -> HTTPException:
    """Map domain exceptions to HTTP responses."""

    if isinstance(exc, ExpertNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


@router.get(
    "/",
    response_model=ExpertListResponse,
)
def list_experts(
    county_id: UUID | None = Query(default=None),
    expert_type: ExpertType | None = Query(default=None),
    is_available: bool | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: object = Depends(get_current_web_user),
    db: Session = Depends(get_db),
):
    """
    List agricultural and veterinary experts.

    Supports filtering by county_id, expert_type, and is_available.
    """

    service = ExpertService(db)

    try:
        return service.list_experts(
            county_id=county_id,
            expert_type=expert_type,
            is_available=is_available,
            limit=limit,
            offset=offset,
        )

    except ExpertError as exc:
        raise _handle_expert_error(exc)


@router.patch("/{expert_id}/contact-verification")
def set_expert_contact_verification(
    expert_id: UUID,
    payload: ExpertContactVerificationUpdate,
    _: Farmer | object = Depends(require_admin_or_staff),
    db: Session = Depends(get_db),
):
    expert = ExpertService(db).get_expert(expert_id)
    expert.contact_verified = payload.contact_verified
    db.commit()
    db.refresh(expert)
    return ExpertResponse.model_validate(expert)


@router.get("/me", response_model=ExpertResponse)
def get_my_expert_profile(current_expert: Expert = Depends(get_current_expert)):
    return current_expert


@router.get("/me/requests", response_model=list[ExpertRequestResponse])
def list_my_expert_requests(
    request_status: RequestStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_expert: Expert = Depends(get_current_expert),
    db: Session = Depends(get_db),
):
    query = db.query(ExpertRequest).filter(ExpertRequest.expert_id == current_expert.id)
    if request_status is not None:
        query = query.filter(ExpertRequest.status == request_status)
    return query.order_by(ExpertRequest.created_at.desc()).offset(offset).limit(limit).all()


@router.patch("/me/requests/{request_id}", response_model=ExpertRequestResponse)
def update_my_expert_request(
    request_id: UUID,
    payload: ExpertRequestStatusUpdate,
    current_expert: Expert = Depends(get_current_expert),
    db: Session = Depends(get_db),
):
    if payload.request_id != request_id:
        raise HTTPException(status_code=422, detail="Request ID does not match the path.")
    request = db.query(ExpertRequest).filter(
        ExpertRequest.id == request_id,
        ExpertRequest.expert_id == current_expert.id,
    ).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Expert request not found.")
    try:
        return ExpertRequestService(db).update_status(payload)
    except ExpertError as exc:
        raise _handle_expert_error(exc)


@router.patch("/me/availability", response_model=ExpertResponse)
def update_my_availability(
    payload: AvailabilityUpdate,
    current_expert: Expert = Depends(get_current_expert),
    db: Session = Depends(get_db),
):
    current_expert.is_available = payload.is_available
    db.commit()
    db.refresh(current_expert)
    return current_expert
