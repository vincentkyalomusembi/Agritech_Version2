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


@router.post("/", response_model=AdvisoryResponse, status_code=status.HTTP_201_CREATED)
def create_advisory(data: AdvisoryCreate, db: Session = Depends(get_db)):
    """Create a new agricultural advisory. Leave county_id blank for national-level."""
    return AdvisoryService(db).create(data)


@router.get("/", response_model=list[AdvisoryResponse])
def list_advisories(
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return advisories, newest first. Use active_only=false to include deactivated ones."""
    return AdvisoryService(db).get_all(active_only=active_only, limit=limit, offset=offset)


@router.get("/county/{county_id}", response_model=list[AdvisoryResponse])
def get_advisories_by_county(county_id: UUID, db: Session = Depends(get_db)):
    """Return advisories for a county plus national advisories (county_id = null)."""
    return AdvisoryService(db).get_by_county(county_id)


@router.get("/category/{category}", response_model=list[AdvisoryResponse])
def get_advisories_by_category(category: AdvisoryCategory, db: Session = Depends(get_db)):
    """Filter advisories by category: Crop, Livestock, or General."""
    return AdvisoryService(db).get_by_category(category)


@router.get("/{advisory_id}", response_model=AdvisoryResponse)
def get_advisory(advisory_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single advisory by its UUID."""
    return AdvisoryService(db).get_by_id(advisory_id)


@router.patch("/{advisory_id}", response_model=AdvisoryResponse)
def update_advisory(advisory_id: UUID, data: AdvisoryUpdate, db: Session = Depends(get_db)):
    """Partial update — only send the fields you want to change."""
    return AdvisoryService(db).update(advisory_id, data)


@router.delete("/{advisory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_advisory(advisory_id: UUID, db: Session = Depends(get_db)):
    """Remove an advisory permanently."""
    AdvisoryService(db).delete(advisory_id)
