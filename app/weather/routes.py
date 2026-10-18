import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_farmer
from app.database.sessions import get_db
from app.farmers.model import Farmer
from app.recommendations.context_service import RecommendationContextService
from app.weather.schema import FarmWeatherResponse

router = APIRouter(prefix="/weather", tags=["Weather"])
logger = logging.getLogger(__name__)


@router.get("", response_model=FarmWeatherResponse)
def get_farm_weather(
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Weather, 5-day forecast, rainfall and NDVI for the signed-in farmer's farm."""
    context_service = RecommendationContextService(db)
    context = context_service.environmental_context(current_farmer)
    latitude, longitude = context["latitude"], context["longitude"]

    daily = []
    if latitude is not None and longitude is not None:
        try:
            daily = context_service.weather.get_daily_forecast(latitude, longitude)
        except Exception as exc:
            logger.warning("Daily forecast unavailable: %s", exc)

    observations = context.get("observations") or {}
    ndvi = observations.get("ndvi")
    # NDVI is normally the full GEE reading; tolerate a bare value as well.
    ndvi_value = ndvi.get("ndvi") if isinstance(ndvi, dict) else ndvi
    rainfall = observations.get("rainfall") or {}
    trend = observations.get("ndvi_trend") or {}

    return FarmWeatherResponse(
        latitude=latitude,
        longitude=longitude,
        location_source=context.get("location_source"),
        current=(context.get("weather_forecast") or {}).get("current"),
        daily_forecast=daily,
        rainfall_mm_30d=rainfall.get("rainfall_mm"),
        rainfall_status=rainfall.get("rainfall_status"),
        rainfall_normal_mm=rainfall.get("normal_mm"),
        rainfall_trend=rainfall.get("rainfall_trend"),
        ndvi_trend_level={"improving": "above", "declining": "below", "stable": "normal"}.get(
            trend.get("direction") if isinstance(trend, dict) else None),
        ndvi=ndvi_value,
        vegetation_health=ndvi.get("vegetation_health") if isinstance(ndvi, dict) else None,
        ndvi_trend=trend.get("direction") if isinstance(trend, dict) else None,
        ndvi_change=trend.get("change") if isinstance(trend, dict) else None,
        observations=observations or None,
    )
