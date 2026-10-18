from datetime import date

from sqlalchemy.orm import Session

from app.core.cache import get_json, set_json
from app.integrations.google_earth_engine.cache_model import EnvironmentalCache
from app.integrations.google_earth_engine.chirps import CHIRPSService
from app.integrations.google_earth_engine.service import EarthEngineService


class EnvironmentalCacheService:
    """Read precomputed environmental data and refresh a region when needed."""

    def __init__(self, db: Session, earth_engine: EarthEngineService | None = None):
        self.db = db
        self._earth_engine = earth_engine

    @property
    def earth_engine(self) -> EarthEngineService:
        # Created on first use so cache hits never pay the GEE start-up cost.
        if self._earth_engine is None:
            self._earth_engine = EarthEngineService()
        return self._earth_engine

    @staticmethod
    def region_for_farmer(farmer) -> tuple[str, str]:
        if farmer.ward:
            return "ward", f"{farmer.county.name}:{farmer.sub_county or ''}:{farmer.ward}"
        if farmer.sub_county:
            return "sub_county", f"{farmer.county.name}:{farmer.sub_county}"
        return "county", farmer.county.name

    LIVE_TTL_SECONDS = 6 * 3600

    def get_live(self, farmer, latitude: float, longitude: float) -> dict:
        """Live GEE lookup for a cache miss, shared by the farmer's region for a few hours."""
        region_type, region_name = self.region_for_farmer(farmer)
        key = f"gee:live:{region_type}:{region_name}:{date.today().isoformat()}"
        cached = get_json(key)
        if cached is not None:
            return cached
        environment = self.earth_engine.get_environment(latitude, longitude)
        set_json(key, environment, self.LIVE_TTL_SECONDS)
        return environment

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
                "normal_mm": row.rainfall_normal_mm,
                "rainfall_trend": CHIRPSService.classify_trend(row.rainfall_mm, row.rainfall_normal_mm)
                if row.rainfall_mm is not None else None,
            },
            "ndvi_trend": row.ndvi_trend,
            "cache": {
                "region_type": row.region_type,
                "region_name": row.region_name,
                "observed_on": row.observed_on.isoformat(),
            },
        }