from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.market_prices.schema import MarketPriceResponse, MarketPriceCreate
from app.market_prices.service import MarketPriceService

router = APIRouter(
    prefix="/market-prices",
    tags=["Market Prices"],
)


@router.get("/", response_model=list[MarketPriceResponse])
def get_all_prices(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    """Return market prices sorted newest first. Supports pagination."""
    return MarketPriceService(db).get_all(limit=limit, offset=offset)


@router.get("/county/{county_id}", response_model=list[MarketPriceResponse])
def get_prices_by_county(county_id: UUID, db: Session = Depends(get_db)):
    """Return all price records for a given county."""
    return MarketPriceService(db).get_by_county(county_id)


@router.get("/crop/{crop_id}", response_model=list[MarketPriceResponse])
def get_prices_by_crop(crop_id: UUID, db: Session = Depends(get_db)):
    """Return all price records for a given crop."""
    return MarketPriceService(db).get_by_crop(crop_id)


@router.post("/scrape", status_code=status.HTTP_200_OK)
def trigger_scrape(db: Session = Depends(get_db)):
    """Manually trigger a KAMIS price scrape and store new records."""
    result = MarketPriceService(db).scrape_and_store()
    return {"message": "KAMIS scrape completed.", **result}


@router.post("/", response_model=MarketPriceResponse, status_code=status.HTTP_201_CREATED)
def create_price(data: MarketPriceCreate, db: Session = Depends(get_db)):
    """Manually add a single market price record (admin use)."""
    return MarketPriceService(db).create_manual(data)
