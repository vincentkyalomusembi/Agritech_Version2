from uuid import UUID

from sqlalchemy.orm import Session
from loguru import logger

from app.market_prices.model import MarketPrice
from app.market_prices.repository import MarketPriceRepository
from app.market_prices.schema import MarketPriceCreate
from app.market_prices.scraper import (
    fetch_kamis_html,
    parse_kamis_html,
    normalise_crop_name,
    normalise_county_name,
)
from app.crops.model import Crop
from app.counties.model import County


class MarketPriceService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = MarketPriceRepository(db)

    def get_all(self, limit: int = 200, offset: int = 0):
        return self.repo.get_all(limit=limit, offset=offset)

    def get_by_county(self, county_id: UUID):
        return self.repo.get_by_county(county_id)

    def get_by_crop(self, crop_id: UUID):
        return self.repo.get_by_crop(crop_id)

    def create_manual(self, data: MarketPriceCreate) -> MarketPrice:
        price = MarketPrice(
            county_id=data.county_id,
            crop_id=data.crop_id,
            market_name=data.market_name,
            minimum_price=data.minimum_price,
            maximum_price=data.maximum_price,
            average_price=data.average_price,
            unit=data.unit,
            price_date=data.price_date,
            source=data.source,
        )
        return self.repo.create(price)

    def scrape_and_store(self) -> dict:
        """
        Full KAMIS pipeline:
        1. Fetch the daily price page HTML
        2. Parse price rows from the table
        3. Match each row to a DB Crop and County
        4. Skip duplicates for the same market/crop/date
        5. Bulk insert new rows
        """
        html = fetch_kamis_html()
        if not html:
            logger.warning("KAMIS scrape aborted — no HTML received.")
            return {"scraped": 0, "inserted": 0, "skipped": 0}

        raw_records = parse_kamis_html(html)
        if not raw_records:
            logger.warning("KAMIS parse returned zero records.")
            return {"scraped": 0, "inserted": 0, "skipped": 0}

        to_insert = []
        skipped = 0

        for record in raw_records:
            try:
                price_obj = self._resolve_record(record)
                if price_obj is None:
                    skipped += 1
                    continue

                already_exists = self.repo.exists_for_date(
                    county_id=price_obj.county_id,
                    crop_id=price_obj.crop_id,
                    market_name=price_obj.market_name,
                    price_date=price_obj.price_date,
                )
                if already_exists:
                    skipped += 1
                    continue

                to_insert.append(price_obj)

            except Exception as exc:
                logger.warning(f"KAMIS: Could not process record {record}: {exc}")
                skipped += 1

        inserted = self.repo.bulk_create(to_insert) if to_insert else 0

        logger.info(
            f"KAMIS done — scraped={len(raw_records)}, inserted={inserted}, skipped={skipped}"
        )
        return {"scraped": len(raw_records), "inserted": inserted, "skipped": skipped}

    def _resolve_record(self, record: dict) -> MarketPrice | None:
        """Match a raw KAMIS row to a DB Crop and County. Returns None if either lookup fails."""
        canonical_crop = normalise_crop_name(record["commodity"])
        canonical_county = normalise_county_name(record["county"]) or normalise_county_name(record["market"])

        if not canonical_crop or not canonical_county:
            return None

        crop = self.db.query(Crop).filter(Crop.name == canonical_crop).first()
        if not crop:
            logger.debug(f"KAMIS: Crop '{canonical_crop}' not in DB — skipping.")
            return None

        county = self.db.query(County).filter(County.name == canonical_county).first()
        if not county:
            logger.debug(f"KAMIS: County '{canonical_county}' not in DB — skipping.")
            return None

        return MarketPrice(
            county_id=county.id,
            crop_id=crop.id,
            market_name=record["market"],
            minimum_price=record["minimum_price"],
            maximum_price=record["maximum_price"],
            average_price=record["average_price"],
            unit=record["unit"],
            price_date=record["price_date"],
            source="KAMIS",
        )
