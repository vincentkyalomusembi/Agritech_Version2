"""
Advisory — API Routes
======================
Endpoints:
  POST   /advisories                         → create advisory (admin)
  GET    /advisories                         → list all active advisories
  GET    /advisories/{advisory_id}           → get one advisory
  GET    /advisories/county/{county_id}      → advisories for a county
  GET    /advisories/category/{category}     → advisories by category
  PATCH  /advisories/{advisory_id}           → update advisory (admin)
  DELETE /advisories/{advisory_id}           → delete advisory (admin)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.advisory.model import AdvisoryCategory
from app.advisory.schema import AdvisoryCreate, AdvisoryUpdate, AdvisoryResponse
from app.advisory.service import AdvisoryService

router = APIRouter(
    prefix="/advisories",
    tags=["Advisories"],
)


@router.post(
    "/",
    response_model=AdvisoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new advisory",
)
def create_advisory(
    data: AdvisoryCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new agricultural advisory.
    Leave county_id blank to create a national-level advisory.
    """
    service = AdvisoryService(db)
    return service.create(data)


@router.get(
    "/",
    response_model=list[AdvisoryResponse],
    summary="List all advisories",
)
def list_advisories(
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Return advisories, newest first.
    Use ?active_only=false to include deactivated advisories.
    """
    service = AdvisoryService(db)
    return service.get_all(active_only=active_only, limit=limit, offset=offset)


@router.get(
    "/county/{county_id}",
    response_model=list[AdvisoryResponse],
    summary="Get advisories for a county",
)
def get_advisories_by_county(
    county_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return advisories targeted at a county, plus national advisories (county_id = null).
    """
    service = AdvisoryService(db)
    return service.get_by_county(county_id)


@router.get(
    "/category/{category}",
    response_model=list[AdvisoryResponse],
    summary="Get advisories by category",
)
def get_advisories_by_category(
    category: AdvisoryCategory,
    db: Session = Depends(get_db),
):
    """
    Filter advisories by category: CROP, LIVESTOCK, or GENERAL.
    """
    service = AdvisoryService(db)
    return service.get_by_category(category)


@router.get(
    "/{advisory_id}",
    response_model=AdvisoryResponse,
    summary="Get a single advisory",
)
def get_advisory(
    advisory_id: UUID,
    db: Session = Depends(get_db),
):
    service = AdvisoryService(db)
    return service.get_by_id(advisory_id)


@router.patch(
    "/{advisory_id}",
    response_model=AdvisoryResponse,
    summary="Update an advisory",
)
def update_advisory(
    advisory_id: UUID,
    data: AdvisoryUpdate,
    db: Session = Depends(get_db),
):
    """
    Partial update — send only the fields you want to change.
    """
    service = AdvisoryService(db)
    return service.update(advisory_id, data)


@router.delete(
    "/{advisory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an advisory",
)
def delete_advisory(
    advisory_id: UUID,
    db: Session = Depends(get_db),
):
    service = AdvisoryService(db)
    service.delete(advisory_id)
