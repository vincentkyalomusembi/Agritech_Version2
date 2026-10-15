from datetime import date

from sqlalchemy.orm import Session

from app.integrations.google_earth_engine.cache_model import EnvironmentalCache
from app.integrations.google_earth_engine.service import EarthEngineService


class EnvironmentalCacheService:
    """Read precomputed environmental data and refresh a region when needed."""

    def __init__(self, db: Session, earth_engine: EarthEngineService | None = None):
        self.db = db
        self.earth_engine = earth_engine or EarthEngineService()

    @staticmethod
    def region_for_farmer(farmer) -> tuple[str, str]:
        if farmer.ward:
            return "ward", f"{farmer.county.name}:{farmer.sub_county or ''}:{farmer.ward}"
        if farmer.sub_county:
            return "sub_county", f"{farmer.county.name}:{farmer.sub_county}"
        return "county", farmer.county.name

    def get_for_farmer(self, farmer) -> dict | None:
        region_type, region_name = self.region_for_farmer(farmer)
        row = (
            self.db.query(EnvironmentalCache)
            .filter(EnvironmentalCache.cache_key == f"{region_type}:{region_name}")
            .filter(EnvironmentalCache.observed_on == date.today())
            .first()
        )
        if row is None:
            return None
        return {
            "ndvi": row.ndvi,
            "rainfall": {
                "dataset": "CHIRPS Daily",
                "period_days": 30,
                "rainfall_mm": row.rainfall_mm,
                "rainfall_status": row.rainfall_status,
            },
            "ndvi_trend": row.ndvi_trend,
            "cache": {
                "region_type": row.region_type,
                "region_name": row.region_name,
                "observed_on": row.observed_on.isoformat(),
            },
        }