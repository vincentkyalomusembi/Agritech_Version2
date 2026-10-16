from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.counties.model import County, Constituency, Ward
from app.counties.schema import CountyResponse, ConstituencyResponse, WardResponse
from app.database.sessions import get_db

router = APIRouter(prefix="/counties", tags=["County Locations"])


@router.get("", response_model=list[CountyResponse])
def list_counties(db: Session = Depends(get_db)):
    """Return the 47 counties for registration and profile location selectors."""
    return db.query(County).order_by(County.name).all()


@router.get("/{county_id}/constituencies", response_model=list[ConstituencyResponse])
def list_county_constituencies(county_id: UUID, db: Session = Depends(get_db)):
    if db.query(County.id).filter(County.id == county_id).first() is None:
        raise HTTPException(status_code=404, detail="County not found")
    return db.query(Constituency).filter_by(county_id=county_id).order_by(Constituency.name).all()


@router.get("/constituencies/{constituency_id}/wards", response_model=list[WardResponse])
def list_constituency_wards(constituency_id: UUID, db: Session = Depends(get_db)):
    if db.query(Constituency.id).filter(Constituency.id == constituency_id).first() is None:
        raise HTTPException(status_code=404, detail="Constituency not found")
    return db.query(Ward).filter_by(constituency_id=constituency_id).order_by(Ward.name).all()
