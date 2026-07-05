"""
Market Prices — API Routes
===========================
Endpoints:
  GET  /market-prices                    → all prices (paginated)
  GET  /market-prices/county/{county_id} → prices filtered by county
  GET  /market-prices/crop/{crop_id}     → prices filtered by crop
  POST /market-prices/scrape             → trigger KAMIS scrape manually
  POST /market-prices                    → manually add a price record
"""

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


@router.get(
    "/",
    response_model=list[MarketPriceResponse],
    summary="Get all market prices",
)
def get_all_prices(
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of market prices across all counties and crops.
    Sorted by price_date descending (newest first).
    """
    service = MarketPriceService(db)
    return service.get_all(limit=limit, offset=offset)


@router.get(
    "/county/{county_id}",
    response_model=list[MarketPriceResponse],
    summary="Get market prices for a specific county",
)
def get_prices_by_county(
    county_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return all price records for a given county UUID.
    """
    service = MarketPriceService(db)
    return service.get_by_county(county_id)


@router.get(
    "/crop/{crop_id}",
    response_model=list[MarketPriceResponse],
    summary="Get market prices for a specific crop",
)
def get_prices_by_crop(
    crop_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return all price records for a given crop UUID.
    """
    service = MarketPriceService(db)
    return service.get_by_crop(crop_id)


@router.post(
    "/scrape",
    summary="Trigger KAMIS scrape and store results",
    status_code=status.HTTP_200_OK,
)
def trigger_scrape(
    db: Session = Depends(get_db),
):
    """
    Manually trigger a KAMIS price scrape.
    Returns a summary of how many records were scraped, inserted, and skipped.
    """
    service = MarketPriceService(db)
    result = service.scrape_and_store()
    return {
        "message": "KAMIS scrape completed.",
        **result,
    }


@router.post(
    "/",
    response_model=MarketPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a market price",
)
def create_price(
    data: MarketPriceCreate,
    db: Session = Depends(get_db),
):
    """
    Manually insert a single market price record (admin use).
    """
    service = MarketPriceService(db)
    return service.create_manual(data)
