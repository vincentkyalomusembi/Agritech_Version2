from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.counties.model import County, Constituency, Ward
from app.counties.schema import CountyResponse, ConstituencyResponse, LocationMatchResponse, WardResponse
from app.recommendations.vendor_matching import distance_km
from app.database.sessions import get_db

router = APIRouter(prefix="/counties", tags=["County Locations"])


@router.get("", response_model=list[CountyResponse])
def list_counties(db: Session = Depends(get_db)):
    """Return the 47 counties for registration and profile location selectors."""
    return db.query(County).order_by(County.name).all()


@router.get("/locate", response_model=LocationMatchResponse)
def locate(
    latitude: float = Query(..., ge=-4.7, le=5.1),
    longitude: float = Query(..., ge=33.9, le=41.9),
    db: Session = Depends(get_db),
):
    """
    Approximate county and sub-county for a map pin or device location.

    Uses the nearest sub-county centroid (boundary polygons are not stored),
    and returns that sub-county's wards so the farmer can pick theirs.
    """
    constituencies = db.query(Constituency).all()
    if not constituencies:
        raise HTTPException(status_code=404, detail="Location data is not available")
    nearest = min(constituencies, key=lambda row: distance_km(latitude, longitude, row.latitude, row.longitude))
    return LocationMatchResponse(
        county=CountyResponse.model_validate(db.query(County).filter_by(id=nearest.county_id).one()),
        constituency=ConstituencyResponse.model_validate(nearest),
        wards=[WardResponse.model_validate(row) for row in db.query(Ward).filter_by(constituency_id=nearest.id).order_by(Ward.name)],
        distance_km=round(distance_km(latitude, longitude, nearest.latitude, nearest.longitude), 1),
    )


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
