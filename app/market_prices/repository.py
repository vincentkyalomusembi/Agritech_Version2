from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.market_prices.model import MarketPrice


class MarketPriceRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, price: MarketPrice) -> MarketPrice:
        self.db.add(price)
        self.db.commit()
        self.db.refresh(price)
        return price

    def bulk_create(self, prices: list[MarketPrice]) -> int:
        """Insert multiple price rows at once. Returns the number of rows inserted."""
        self.db.add_all(prices)
        self.db.commit()
        return len(prices)

    def get_all(self, limit: int = 200, offset: int = 0):
        return (
            self.db.query(MarketPrice)
            .order_by(MarketPrice.price_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_county(self, county_id: UUID, limit: int = 100):
        return (
            self.db.query(MarketPrice)
            .filter(MarketPrice.county_id == county_id)
            .order_by(MarketPrice.price_date.desc())
            .limit(limit)
            .all()
        )

    def get_by_crop(self, crop_id: UUID, limit: int = 100):
        return (
            self.db.query(MarketPrice)
            .filter(MarketPrice.crop_id == crop_id)
            .order_by(MarketPrice.price_date.desc())
            .limit(limit)
            .all()
        )

    def get_by_county_and_crop(self, county_id: UUID, crop_id: UUID, limit: int = 50):
        return (
            self.db.query(MarketPrice)
            .filter(
                MarketPrice.county_id == county_id,
                MarketPrice.crop_id == crop_id,
            )
            .order_by(MarketPrice.price_date.desc())
            .limit(limit)
            .all()
        )

    def exists_for_date(
        self,
        county_id: UUID,
        crop_id: UUID,
        market_name: str,
        price_date: date,
    ) -> bool:
        """Check if a price record already exists for this market/crop/date combo."""
        return (
            self.db.query(MarketPrice)
            .filter(
                MarketPrice.county_id == county_id,
                MarketPrice.crop_id == crop_id,
                MarketPrice.market_name == market_name,
                MarketPrice.price_date == price_date,
            )
            .first()
        ) is not None

    def get_latest_by_crop(self, crop_id: UUID) -> MarketPrice | None:
        return (
            self.db.query(MarketPrice)
            .filter(MarketPrice.crop_id == crop_id)
            .order_by(MarketPrice.price_date.desc())
            .first()
        )
