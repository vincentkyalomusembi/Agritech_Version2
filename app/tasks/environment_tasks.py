from collections import defaultdict
from datetime import date

from app.core.celery_app import celery_app
from app.database.sessions import SessionLocal
from app.farmers.model import Farmer
from app.farmers.location import farmer_coordinates
from app.integrations.google_earth_engine.cache_model import EnvironmentalCache
from app.integrations.google_earth_engine.cache_service import EnvironmentalCacheService
from app.integrations.google_earth_engine.service import EarthEngineService


@celery_app.task
def refresh_environmental_cache() -> dict:
    """Precompute daily GEE values for each known ward/sub-county/county."""
    db = SessionLocal()
    try:
        groups = defaultdict(list)
        farmers = db.query(Farmer).filter(Farmer.is_active.is_(True)).all()
        for farmer in farmers:
            if farmer.county is None:
                continue
            region_type, region_name = EnvironmentalCacheService.region_for_farmer(farmer)
            latitude, longitude, _ = farmer_coordinates(farmer)
            groups[(region_type, region_name, farmer.county.id)].append((latitude, longitude))

        engine = EarthEngineService()
        refreshed = 0
        failed = 0
        for (region_type, region_name, county_id), points in groups.items():
            latitude = sum(point[0] for point in points) / len(points)
            longitude = sum(point[1] for point in points) / len(points)
            try:
                environment = engine.get_environment(latitude, longitude)
                rainfall = environment.get("rainfall") or {}
                values = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "rainfall_mm": rainfall.get("rainfall_mm"),
                    "rainfall_status": rainfall.get("rainfall_status"),
                    "rainfall_normal_mm": rainfall.get("normal_mm"),
                    "ndvi": environment.get("ndvi"),
                    "ndvi_trend": environment.get("ndvi_trend"),
                }
                cache_key = f"{region_type}:{region_name}"
                row = db.query(EnvironmentalCache).filter_by(cache_key=cache_key).first()
                if row is None:
                    row = EnvironmentalCache(
                        cache_key=cache_key,
                        region_type=region_type,
                        region_name=region_name,
                        county_id=county_id,
                        **values,
                        observed_on=date.today(),
                    )
                    db.add(row)
                else:
                    for key, value in values.items():
                        setattr(row, key, value)
                    row.observed_on = date.today()
                db.commit()
                refreshed += 1
            except Exception:
                db.rollback()
                failed += 1
        return {"refreshed": refreshed, "failed": failed}
    finally:
        db.close()
