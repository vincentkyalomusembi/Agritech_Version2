from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.experts.exceptions import ExpertError, ExpertNotFoundError
from app.experts.model import ExpertType
from app.experts.schema import ExpertListResponse
from app.experts.services.expert_service import ExpertService

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
